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
import docx
import PyPDF2
import tempfile

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
if 'user_name' not in st.session_state:
    st.session_state.user_name = ""

def extract_text_from_pdf(file_path):
    """Extract text from a PDF file."""
    pdf_reader = PyPDF2.PdfReader(file_path)
    text = ""
    for page in pdf_reader.pages:
        text += page.extract_text() + "\n"
    return text

def extract_text_from_docx(file_path):
    """Extract text from a DOCX file."""
    doc = docx.Document(file_path)
    text = ""
    for paragraph in doc.paragraphs:
        text += paragraph.text + "\n"
    return text

def extract_text_from_txt(file):
    """Extract text from a TXT file."""
    return file.getvalue().decode('utf-8')

def process_uploaded_files(files):
    """Process all uploaded files and extract their content."""
    extracted_texts = []
    for file in files:
        # Create a temporary file to handle the uploaded file
        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
            tmp_file.write(file.getvalue())
            tmp_file_path = tmp_file.name

        try:
            if file.type == "application/pdf":
                text = extract_text_from_pdf(tmp_file_path)
            elif file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
                text = extract_text_from_docx(tmp_file_path)
            elif file.type == "text/plain":
                text = extract_text_from_txt(file)
            else:
                text = f"Unsupported file type: {file.type}"
            
            extracted_texts.append({
                "filename": file.name,
                "content": text
            })
        finally:
            # Clean up the temporary file
            os.unlink(tmp_file_path)
    
    return extracted_texts

# Try loading from Streamlit secrets first
if "OPENAI_API_KEY" in st.secrets:
    api_key = st.secrets["OPENAI_API_KEY"]
else:
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")

# Load allowed keys from environment
if "ALLOWED_KEYS" in st.secrets:
    allowed_keys = st.secrets["ALLOWED_KEYS"].split(",")
else:
    load_dotenv()
    allowed_keys_str = os.getenv("ALLOWED_KEYS", "")
    allowed_keys = [key.strip() for key in allowed_keys_str.split(",") if key.strip()]

# Set page config must be the first Streamlit command
st.set_page_config(page_title="Personal Brand Discovery", layout="centered")

if not api_key:
    st.error("OPENAI_API_KEY not found in environment variables")
    st.stop()

if not allowed_keys:
    st.error("ALLOWED_KEYS not found in environment variables")
    st.stop()

client = OpenAI(api_key=api_key)

# Access control
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
            # Add name field
            user_name = st.text_input(
                "What's your name?",
                value=st.session_state.user_name,
                placeholder="Enter your name"
            )
            
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
            if not user_name:
                st.error("Please provide your name.")
                st.stop()
            if not initial_context:
                st.error("Please provide some information about yourself and your goals.")
                st.stop()
            
            # Store the initial context, name, and uploaded files in session state
            st.session_state.user_name = user_name
            st.session_state.initial_context = initial_context
            st.session_state.uploaded_files = uploaded_files
            
            with st.spinner("Analyzing your context to determine relevant questions..."):
                try:
                    # Process uploaded files and extract their content
                    if uploaded_files:
                        extracted_docs = process_uploaded_files(uploaded_files)
                        # Add document content to the context
                        full_context = initial_context + "\n\nAdditional information from uploaded documents:\n"
                        for doc in extracted_docs:
                            full_context += f"\nContent from {doc['filename']}:\n{doc['content']}\n"
                    else:
                        full_context = initial_context
                    
                    # Generate questions based on context
                    system_prompt = """You are a personal brand development expert. Based on the user's context and any uploaded documents, generate a set of relevant questions that will help them develop their personal brand. 
                    The questions should be specific to their situation and goals. Format the response as a JSON array of objects, where each object has 'question' and 'description' fields.
                    The questions should be thought-provoking and help uncover their unique value proposition, strengths, and professional identity.
                    DO NOT ask questions about information that is already provided in the uploaded documents."""
                    
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
                            user_name=st.session_state.user_name,
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
                                spaceAfter=30,
                                textColor=colors.HexColor('#2E4053')
                            )
                            
                            section_title_style = ParagraphStyle(
                                'SectionTitle',
                                parent=styles['Heading2'],
                                fontSize=14,
                                spaceAfter=15,
                                textColor=colors.HexColor('#2E4053')
                            )
                            
                            body_style = ParagraphStyle(
                                'CustomBody',
                                parent=styles['Normal'],
                                fontSize=12,
                                spaceAfter=12,
                                leading=14
                            )
                            
                            bold_style = ParagraphStyle(
                                'BoldStyle',
                                parent=styles['Normal'],
                                fontSize=12,
                                spaceAfter=12,
                                fontName='Helvetica-Bold',
                                textColor=colors.HexColor('#2E4053')
                            )
                            
                            # Build PDF content
                            content = []
                            
                            # Add title
                            content.append(Paragraph("Personal Brand Analysis", title_style))
                            content.append(Spacer(1, 20))
                            
                            # Add initial context section
                            content.append(Paragraph("Initial Context", section_title_style))
                            content.append(Paragraph(st.session_state.initial_context, body_style))
                            content.append(Spacer(1, 20))
                            
                            # Add analysis section
                            content.append(Paragraph("Analysis", section_title_style))
                            
                            # Split the result into sections based on numbered points
                            sections = result.split('\n\n')
                            for section in sections:
                                if section.strip():
                                    # Check if it's a numbered section
                                    if section.strip()[0].isdigit():
                                        # Extract the section title and content
                                        parts = section.split('.', 1)
                                        if len(parts) > 1:
                                            section_title = parts[0].strip() + '.'
                                            section_content = parts[1].strip()
                                            # First line: section number and title
                                            content.append(Paragraph(section_title, bold_style))
                                            # Second line: content
                                            content.append(Paragraph(section_content, body_style))
                                        else:
                                            content.append(Paragraph(section, body_style))
                                    else:
                                        content.append(Paragraph(section, body_style))
                                    content.append(Spacer(1, 12))
                            
                            content.append(PageBreak())
                            
                            # Add questions and responses section
                            content.append(Paragraph("Your Responses", section_title_style))
                            content.append(Spacer(1, 15))
                            
                            for i, (q, r) in enumerate(zip(questions_data, responses), 1):
                                if r.strip():  # Only include answered questions
                                    content.append(Paragraph(f"Question {i}: {q['question']}", bold_style))
                                    if q.get('description'):
                                        content.append(Paragraph(q['description'], body_style))
                                    content.append(Paragraph(r, body_style))
                                    content.append(Spacer(1, 20))
                            
                            # Build PDF
                            doc.build(content)
                            return buffer.getvalue()

                        # Create PDF
                        pdf_data = create_pdf(st.session_state.analysis_result, st.session_state.responses, st.session_state.questions_data)
                        
                        # Create download button with personalized filename
                        b64 = base64.b64encode(pdf_data).decode()
                        href = f'<a href="data:application/pdf;base64,{b64}" download="{st.session_state.user_name}-personal-brand-analysis.pdf">📥 Download PDF Report</a>'
                        st.markdown(href, unsafe_allow_html=True)

                    except Exception as e:
                        st.error("An error occurred while generating the analysis. Please try again.")
                        st.exception(e)
