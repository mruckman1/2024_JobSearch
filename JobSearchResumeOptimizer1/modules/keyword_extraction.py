# modules/keyword_extraction.py

import openai
import logging
from typing import List
import os

def extract_keywords(job_description: str) -> List[str]:
    """Use LLM to extract the 10 most important keywords from the job description."""
    # Use OpenAI API
    openai.api_key = os.getenv("OPENAI_API_KEY")
    prompt = f"""As a hiring manager and recruiter, identify the 10 most important keywords from the following job description:

{job_description}

Provide the keywords as a numbered list."""
    try:
        response = openai.Completion.create(
            engine="text-davinci-003",
            prompt=prompt,
            max_tokens=200,
            temperature=0.5,
        )
        keywords_text = response.choices[0].text.strip()
        # Parse the keywords into a list
        keywords = [line.split('. ', 1)[1] for line in keywords_text.split('\n') if '. ' in line]
        return keywords
    except Exception as e:
        logging.error(f"Error extracting keywords: {e}")
        return []
