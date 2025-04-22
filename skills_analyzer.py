import streamlit as st
from openai import OpenAI
import os
from dotenv import load_dotenv


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

        # Load questions
        questions = load_questions()

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
                prompt = (
                    "I’ve answered a set of personal branding questions to reflect on my identity, strengths, values, "
                    "passions, communication style, and the impact I want to create.\n\n"
                    "Based on the responses below, do the following three things:\n\n"
                    "1. Craft a concise one-line personal brand statement that captures the essence of who I am and what I uniquely offer.\n"
                    "2. Provide a paragraph explaining the reasoning behind the statement, connecting it to my strengths, values, and aspirations.\n"
                    "3. Write a 150-word engaging personal brand script that I can use to introduce myself to a potential employer or my manager—"
                    "something that feels confident, human, and makes me memorable.\n\n"
                    "Here are my answers to the personal branding questions:\n"
                )
                
                for i, ((question, _), response) in enumerate(zip(questions, responses), 1):
                    prompt += f"{i}. {question}\n{response}\n\n"

#                prompt += "Provide your analysis in a friendly, clear, and insightful tone."

                try:
                    response = client.responses.create(
                        model="gpt-4.1",
                        input=prompt,
                        temperature=0.7
                    )

                    result = response.output_text
                    st.success("Here is your personal brand insight:")
                    st.write(result)

                except Exception as e:
                    st.error("An error occurred while trying to generate insights. Please check your API key and try again.")
                    st.exception(e)
