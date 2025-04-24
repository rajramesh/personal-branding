import streamlit as st
from openai import OpenAI
import os
from dotenv import load_dotenv
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
import io
import base64
import json

# Initialize session state variables
if 'initial_context' not in st.session_state:
    st.session_state.initial_context = ""
if 'resume_file' not in st.session_state:
    st.session_state.resume_file = None
if 'questions_data' not in st.session_state:
    st.session_state.questions_data = None
if 'responses' not in st.session_state:
    st.session_state.responses = []
if 'analysis_result' not in st.session_state:
    st.session_state.analysis_result = None

# Try loading from Streamlit secrets first
if "OPENAI_API_KEY" in st.secrets:
    api_key = st.secrets["OPENAI_API_KEY"]
else:
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")

# Set page config must be the first Streamlit command
st.set_page_config(page_title="Personal Brand Discovery", layout="centered")

if not api_key:
    st.error("OPENAI_API_KEY not found in environment variables")
    st.stop()

client = OpenAI(api_key=api_key)

# Access control
allowed_keys = ["peterrocks", "rajrocks"]
key = st.text_input("Enter access key:", type="password")

# Only check the key if it's not empty
if key:
    if key not in allowed_keys:
        st.error("Invalid access key. Please try again.")
        st.stop()
    else:
        # Main app content
        st.title("🔍 Discover Your Personal Brand")
        
        # Load initial context gathering instructions
        try:
            with open("initial_context_gathering.txt", "r") as file:
                context_instructions = file.read()
        except FileNotFoundError:
            st.error("Initial context gathering instructions file not found. Please contact support.")
            st.stop()
        
        # Initial context gathering
        st.write(context_instructions)
        
        with st.form("initial_context_form"):
            initial_context = st.text_area(
                "Share your information here:",
                height=500,
                value=st.session_state.initial_context
            )
            
            # Add file uploader for multiple documents
            st.write("Please upload any relevant documents (PDF, DOCX, or TXT format) such as your resume, personal statements, career goals, or other materials that can help us understand your professional journey.")
            uploaded_files = st.file_uploader(
                "Upload Files", 
                type=['pdf', 'docx', 'txt'], 
                key="file_uploader",
                accept_multiple_files=True
            )
            
            initial_submitted = st.form_submit_button("Submit Initial Information")
        
        if initial_submitted:
            if not initial_context:
                st.error("Please provide some information about yourself and your goals.")
                st.stop()
            
            # Store the initial context and uploaded files in session state
            st.session_state.initial_context = initial_context
            st.session_state.uploaded_files = uploaded_files
            
            with st.spinner("Analyzing your context to determine relevant questions..."):
                try:
                    # Prepare the context with uploaded files information if available
                    full_context = initial_context
                    if uploaded_files:
                        full_context += "\n\nAdditional documents have been uploaded for context:"
                        for i, file in enumerate(uploaded_files, 1):
                            full_context += f"\n- Document {i}: {file.name}"
                    
                    # Generate questions based on context
                    system_prompt = """You are a personal brand development expert. Based on the user's context, generate a set of relevant questions that will help them develop their personal brand. 
                    The questions should be specific to their situation and goals. Format the response as a JSON array of objects, where each object has 'question' and 'description' fields.
                    The questions should be thought-provoking and help uncover their unique value proposition, strengths, and professional identity."""
                    
                    chat_response = client.chat.completions.create(
                        model="gpt-4",
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": full_context}
                        ],
                        temperature=0.7
                    )
                    
                    # Parse the generated questions and store in session state
                    st.session_state.questions_data = json.loads(chat_response.choices[0].message.content)
                    st.session_state.responses = [""] * len(st.session_state.questions_data)
                except Exception as e:
                    st.error("An error occurred while generating questions. Please try again.")
                    st.exception(e)
                    st.stop()
        
        # Show questions form if we have questions data
        if st.session_state.questions_data:
            st.write("Based on what you have shared, here are the questions we'll explore:")
            
            with st.form("personal_brand_form"):
                for i, q in enumerate(st.session_state.questions_data, 1):
                    st.subheader(f"{i}. {q['question']}")
                    if q.get('description'):
                        st.markdown(q['description'])
                    response = st.text_area(
                        "Your response (optional):", 
                        height=100, 
                        key=f"response_{i}",
                        value=st.session_state.responses[i-1] if i-1 < len(st.session_state.responses) else ""
                    )
                    st.session_state.responses[i-1] = response
                
                submitted = st.form_submit_button("Generate Personal Brand Analysis")

            if submitted:
                with st.spinner("Analyzing your responses..."):
                    try:
                        # Load analysis prompt template
                        try:
                            with open("analysis_prompt.txt", "r") as file:
                                analysis_prompt_template = file.read()
                        except FileNotFoundError:
                            st.error("Analysis prompt template file not found. Please contact support.")
                            st.stop()

                        # Build the responses section
                        responses_section = ""
                        for i, (q, r) in enumerate(zip(st.session_state.questions_data, st.session_state.responses), 1):
                            if r.strip():  # Only include non-empty responses
                                responses_section += f"\nQuestion {i}: {q['question']}\nResponse: {r}\n"

                        # Format the analysis prompt
                        analysis_prompt = analysis_prompt_template.format(
                            initial_context=st.session_state.initial_context,
                            responses=responses_section
                        )
                        
                        analysis_response = client.chat.completions.create(
                            model="gpt-4",
                            messages=[
                                {"role": "system", "content": "You are a personal brand development expert. Provide detailed, actionable insights based on the available information. If some questions were not answered, focus on the information provided in the initial context and answered questions."},
                                {"role": "user", "content": analysis_prompt}
                            ],
                            temperature=0.7
                        )
                        
                        st.session_state.analysis_result = analysis_response.choices[0].message.content
                        st.success("Here is your personal brand insight:")
                        st.write(st.session_state.analysis_result)

                        # PDF Download functionality
                        st.markdown("---")
                        st.subheader("Download Your Results")
                        
                        def create_pdf(result, responses, questions_data):
                            buffer = io.BytesIO()
                            doc = SimpleDocTemplate(buffer, pagesize=letter)
                            styles = getSampleStyleSheet()
                            
                            # Custom styles
                            title_style = ParagraphStyle(
                                'CustomTitle',
                                parent=styles['Heading1'],
                                fontSize=16,
                                spaceAfter=30
                            )
                            
                            body_style = ParagraphStyle(
                                'CustomBody',
                                parent=styles['Normal'],
                                fontSize=12,
                                spaceAfter=12
                            )
                            
                            bold_style = ParagraphStyle(
                                'BoldStyle',
                                parent=styles['Normal'],
                                fontSize=12,
                                spaceAfter=12,
                                fontName='Helvetica-Bold'
                            )
                            
                            # Build PDF content
                            content = []
                            
                            # Add title
                            content.append(Paragraph("Your Personal Brand Analysis", title_style))
                            content.append(Spacer(1, 20))
                            
                            # Add initial context
                            content.append(Paragraph("<b>Initial Context</b>", bold_style))
                            content.append(Paragraph(st.session_state.initial_context, body_style))
                            content.append(Spacer(1, 20))
                            
                            # Add analysis
                            content.append(Paragraph("<b>Analysis</b>", bold_style))
                            content.append(Paragraph(result, body_style))
                            content.append(PageBreak())
                            
                            # Add questions and responses
                            content.append(Paragraph("<b>Your Responses</b>", bold_style))
                            for i, (q, r) in enumerate(zip(questions_data, responses), 1):
                                if r.strip():  # Only include answered questions
                                    content.append(Paragraph(f"<b>Question {i}: {q['question']}</b>", bold_style))
                                    content.append(Paragraph(r, body_style))
                                    content.append(Spacer(1, 20))
                            
                            # Build PDF
                            doc.build(content)
                            return buffer.getvalue()

                        # Create PDF
                        pdf_data = create_pdf(st.session_state.analysis_result, st.session_state.responses, st.session_state.questions_data)
                        
                        # Create download button
                        b64 = base64.b64encode(pdf_data).decode()
                        href = f'<a href="data:application/pdf;base64,{b64}" download="personal-brand-analysis.pdf">📥 Download PDF Report</a>'
                        st.markdown(href, unsafe_allow_html=True)

                    except Exception as e:
                        st.error("An error occurred while generating the analysis. Please try again.")
                        st.exception(e)
