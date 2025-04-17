# Personal Brand Analyzer

A CLI tool that helps you discover and articulate your personal brand through a series of structured questions and AI-powered analysis.

## Features

- Interactive questionnaire with 8 key questions about your skills, values, and experiences
- AI-powered analysis of your answers to identify key themes
- Generation of a compelling personal brand summary
- Creation of a 60-second video script
- Option to export results to a markdown file

## Setup

1. Clone this repository
2. Create a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows, use: .venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Create a `.env` file in the project root and add your OpenAI API key:
   ```
   OPENAI_API_KEY=your_api_key_here
   ```

## Usage

Run the analyzer:
```bash
python personal_brand_analyzer.py
```

Follow the prompts to answer the questions. The tool will then:
1. Analyze your answers
2. Generate a personal brand summary
3. Create a video script
4. Offer to export the results to a markdown file

## Output

The tool generates:
- A list of key themes identified from your answers
- A 3-4 sentence personal brand summary
- A 60-second video script
- An optional markdown file containing all the above information

## Requirements

- Python 3.7+
- OpenAI API key
- Internet connection for API calls 