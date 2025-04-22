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
        st.write("Answer the following questions to help identify your core competencies and shape your personal brand.")

        # Read questions from file
        def load_questions(file_path="questions.txt"):
            questions = []
            current_question = None
            current_description = []
            
            with open(file_path, 'r') as file:
                for line in file:
                    line = line.strip()
                    if line.startswith('Q:'):
                        if current_question is not None:
                            questions.append((current_question, '\n'.join(current_description)))
                        current_question = line[2:].strip()
                        current_description = []
                    elif line.startswith('D:'):
                        current_description.append(line[2:].strip())
                    elif line and current_description:  # If it's a continuation of the description
                        current_description.append(line)
            
            if current_question is not None:
                questions.append((current_question, '\n'.join(current_description)))
            
            return questions

        # Load prompt from file
        def load_prompt(file_path="prompt.txt"):
            with open(file_path, 'r') as file:
                return file.read()

        # Load questions and prompt
        questions = load_questions()
        prompt_template = load_prompt()

        # Form to collect user responses
        with st.form("personal_brand_form"):
            responses = []
            for i, (question, description) in enumerate(questions, 1):
                st.subheader(f"{i}. {question}")
                if description:
                    st.markdown(description)
                response = st.text_area("Your response:", height=100, key=f"response_{i}")
                responses.append(response)
            submitted = st.form_submit_button("Submit")

        if submitted:
            with st.spinner("Analyzing your responses..."):
                # Build the prompt
                prompt = prompt_template + "\n\n"
                
                for i, ((question, _), response) in enumerate(zip(questions, responses), 1):
                    prompt += f"{i}. {question}\n{response}\n\n"

                try:
                    response = client.responses.create(
                        model="gpt-4.1",
                        input=prompt,
                        temperature=0.7
                    )

                    result = response.output_text
                    st.success("Here is your personal brand insight:")
                    st.write(result)

                    # PDF Download functionality
                    st.markdown("---")
                    st.subheader("Download Your Results")
                    
                    def create_pdf(result, responses, questions):
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
                        
                        # Process the result to handle any line starting with **
                        lines = result.split('\n')
                        for line in lines:
                            if line.strip().startswith('**'):
                                # Remove the ** and make it bold
                                clean_line = line.strip().replace('**', '')
                                content.append(Paragraph(f"<b>{clean_line}</b>", bold_style))
                            else:
                                content.append(Paragraph(line, body_style))
                        
                        # Add page break before responses
                        content.append(PageBreak())
                        content.append(Spacer(1, 20))
                        
                        # Add questions and responses
                        content.append(Paragraph("<b>Your Responses</b>", bold_style))
                        for i, ((question, _), response) in enumerate(zip(questions, responses), 1):
                            content.append(Paragraph(f"<b>Question {i}: {question}</b>", bold_style))
                            content.append(Paragraph(response, body_style))
                            content.append(Spacer(1, 20))
                        
                        # Build PDF
                        doc.build(content)
                        return buffer.getvalue()

                    # Create PDF
                    pdf_data = create_pdf(result, responses, questions)
                    
                    # Create download button
                    b64 = base64.b64encode(pdf_data).decode()
                    href = f'<a href="data:application/pdf;base64,{b64}" download="personal-brand-analysis.pdf">📥 Download PDF Report</a>'
                    st.markdown(href, unsafe_allow_html=True)

                except Exception as e:
                    st.error("An error occurred while trying to generate insights. Please check your API key and try again.")
                    st.exception(e)
