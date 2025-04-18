import streamlit as st
from openai import OpenAI
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Set page config must be the first Streamlit command
st.set_page_config(page_title="Personal Brand Discovery", layout="centered")

# Initialize the OpenAI client with minimal configuration
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Access control
allowed_keys = ["peterrocks", "rajrocks", "teamaccess"]
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
            with open(file_path, 'r') as file:
                return [line.strip() for line in file if line.strip()]

        # Load questions
        questions = load_questions()

        # Form to collect user responses
        with st.form("personal_brand_form"):
            responses = []
            for i, question in enumerate(questions, 1):
                response = st.text_area(f"{i}. {question}", height=100)
                responses.append(response)
            submitted = st.form_submit_button("Submit")

        if submitted:
            with st.spinner("Analyzing your responses..."):
                # Build the prompt
                prompt = "Based on the following responses, identify the person's core competencies and suggest a possible personal brand statement. Also recommend one or two areas they can focus on to enhance their personal brand.\n\n"
                
                for i, (question, response) in enumerate(zip(questions, responses), 1):
                    prompt += f"{i}. {question}\n{response}\n\n"

                prompt += "Provide your analysis in a friendly, clear, and insightful tone."

                try:
                    response = client.responses.create(
                        model="gpt-4",
                        input=prompt,
                        temperature=0.7
                    )

                    result = response.output_text
                    st.success("Here is your personal brand insight:")
                    st.write(result)

                except Exception as e:
                    st.error("An error occurred while trying to generate insights. Please check your API key and try again.")
                    st.exception(e)
