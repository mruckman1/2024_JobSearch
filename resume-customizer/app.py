import streamlit as st
import os
import json
import logging
import re
from datetime import datetime
from pathlib import Path
import requests
from bs4 import BeautifulSoup
from openai import OpenAI
from typing import Dict, List, Tuple
import time
import pickle
import difflib

class ResumeCustomizer:
    def __init__(self):
        self.setup_folders()
        self.setup_logging()
        self.counter_file = "data/job_counter.pkl"
        self.load_counter()
        self.load_base_files()
        
        # Initialize OpenAI client
        try:
            self.client = OpenAI(api_key=st.secrets.openai.api_key)
        except (FileNotFoundError, AttributeError):
            st.error("OpenAI API key not found. Please ensure you have created .streamlit/secrets.toml with your API key.")
            st.stop()

    def setup_folders(self):
        """Create necessary folder structure."""
        folders = ['data', 'outputs']
        for folder in folders:
            Path(folder).mkdir(exist_ok=True)

    def setup_logging(self):
        """Configure logging."""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('resume_customizer.log'),
                logging.StreamHandler()
            ]
        )

    def load_base_files(self):
        """Load base resume and context files."""
        try:
            with open('data/MattRuckmanResume.md', 'r') as f:
                self.base_resume = f.read()
            with open('data/CombinedJobSearchContext.txt', 'r') as f:
                self.context_info = f.read()
            logging.info("Base files loaded successfully")
        except Exception as e:
            logging.error(f"Error loading base files: {str(e)}")
            raise

    def load_counter(self):
        """Load job description counter from pickle file."""
        try:
            with open(self.counter_file, 'rb') as f:
                self.job_counter = pickle.load(f)
        except FileNotFoundError:
            self.job_counter = 0

    def save_counter(self):
        """Save job description counter to pickle file."""
        with open(self.counter_file, 'wb') as f:
            pickle.dump(self.job_counter, f)

    def scrape_job_description(self, url: str) -> str:
        """Scrape job description from URL with improved error handling."""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Remove unwanted elements
            for tag in ['script', 'style', 'nav', 'header', 'footer']:
                for element in soup.find_all(tag):
                    element.decompose()
            
            possible_containers = [
                soup.find(class_=class_name) for class_name in [
                    'job-description', 'description', 'posting-description',
                    'content', 'main-content', 'job-details'
                ]
            ]
            
            job_container = next((c for c in possible_containers if c), soup.find('body'))
            
            if not job_container:
                raise ValueError("Could not find job description content")
                
            return job_container.get_text(separator='\n', strip=True)
            
        except Exception as e:
            st.error(f"Error scraping job description: {str(e)}")
            return None

    def extract_job_info(self, job_description: str) -> Tuple[str, str, List[Dict]]:
        """Extract job title, company name, and key keywords with relevance."""
        try:
            # Extract company and position using GPT-4-turbo with larger context
            completion = self.client.chat.completions.create(
                model="gpt-4-1106-preview",
                messages=[
                    {"role": "system", "content": """You are an experienced recruiter and ATS specialist. 
                    Extract the company name and exact position title from this job description.
                    
                    You must respond in exactly this format (including the exact labels):
                    Company: [company name]
                    Position: [position title]"""},
                    {"role": "user", "content": job_description}
                ]
            )
            job_info = completion.choices[0].message.content
            
            # More robust regex pattern matching with error handling
            company_match = re.search(r'^Company:\s*(.+)$', job_info, re.MULTILINE)
            position_match = re.search(r'^Position:\s*(.+)$', job_info, re.MULTILINE)
            
            if not company_match or not position_match:
                st.error("Failed to extract company or position from LLM response. Response format was incorrect.")
                logging.error(f"Unexpected LLM response format: {job_info}")
                return None, None, []
                
            company_name = company_match.group(1).strip()
            position_title = position_match.group(1).strip()

            # Extract ATS-focused keywords with context analysis
            completion = self.client.chat.completions.create(
                model="gpt-4o-2024-11-20",
                messages=[
                    {"role": "system", "content": """You are an experienced ATS system analyst and recruiter.
                    Analyze this job description and identify the 10 most important keywords/phrases that are 
                    likely to be used in ATS filtering systems. Focus on:
                    1. Technical skills and tools mentioned
                    2. Required certifications or qualifications
                    3. Industry-specific terminology
                    4. Common ATS filter terms for this role level
                    
                    For each keyword:
                    1. Rate its ATS importance (1-10)
                    2. Explain why it's likely to be an ATS filter
                    3. List exact variations that ATS systems commonly look for
                    
                    Return the analysis in this JSON format:
                    [
                        {
                            "keyword": "exact term from job description",
                            "importance": 1-10 score,
                            "ats_reason": "why this is likely an ATS filter",
                            "variations": ["exact variation 1", "exact variation 2"]
                        },
                        ...
                    ]
                    
                    Ensure response is valid JSON."""},
                    {"role": "user", "content": job_description}
                ]
            )
            
            try:
                keywords = json.loads(completion.choices[0].message.content)
            except json.JSONDecodeError:
                st.error("Failed to parse keywords response as JSON")
                logging.error(f"Invalid JSON in keywords response: {completion.choices[0].message.content}")
                keywords = []

            return company_name, position_title, keywords

        except Exception as e:
            st.error(f"Error extracting job information: {str(e)}")
            logging.error(f"Job info extraction error: {str(e)}", exc_info=True)
            return None, None, []

    def customize_resume(self, job_description: str, keywords: List[Dict]) -> str:
        """Customize resume based on job description and keywords, using context information."""
        try:
            completion = self.client.chat.completions.create(
                model="gpt-4-1106-preview",
                messages=[
                    {"role": "system", "content": """You are an expert resume optimization specialist.
                    Your task is to customize the resume to better match the job requirements while maintaining
                    complete truthfulness and authenticity. 
                    
                    Focus on:
                    1. Incorporating ATS keywords naturally
                    2. Using exact phrases from the job description
                    3. Matching the seniority level and tone
                    4. Highlighting relevant experience that matches requirements
                    
                    IMPORTANT OUTPUT INSTRUCTIONS:
                    - Return ONLY the updated resume content in markdown format
                    - Do NOT include any explanatory text before or after the resume
                    - Do NOT include any commentary about changes made
                    - Do NOT include any summary or analysis
                    - Start directly with the resume header
                    - Maintain exact markdown formatting with proper spacing"""},
                    {"role": "user", "content": f"""Base Resume:
                    {self.base_resume}
                    
                    Additional Context Information:
                    {self.context_info}
                    
                    Job Description:
                    {job_description}
                    
                    ATS Keywords to Integrate:
                    {json.dumps(keywords, indent=2)}"""}
                ]
            )
            
            # Clean up any potential commentary before or after the resume
            resume_content = completion.choices[0].message.content
            # Remove any lines starting with common commentary phrases
            resume_lines = [line for line in resume_content.split('\n') 
                        if not line.strip().lower().startswith(('here', 'this resume', 'based on', 'i have', 'note:', 'summary:'))]
            cleaned_resume = '\n'.join(resume_lines).strip()
            
            return cleaned_resume

        except Exception as e:
            st.error(f"Error customizing resume: {str(e)}")
            return self.base_resume

    def analyze_changes(self, original_resume: str, updated_resume: str) -> List[Dict]:
        """Analyze and summarize the changes made to the resume."""
        try:
            completion = self.client.chat.completions.create(
                model="gpt-4o-2024-11-20",
                messages=[
                    {"role": "system", "content": """You are an expert resume analyst.
                    Compare the original and updated resumes and identify all meaningful changes.
                    Focus on:
                    1. Added keywords and phrases
                    2. Modified sections
                    3. Restructured content
                    4. Enhanced descriptions
                    
                    Return the analysis in this format:
                    [
                        {
                            "type": "addition|modification|restructure",
                            "section": "section name",
                            "original": "original text if applicable",
                            "updated": "new text if applicable",
                            "impact": "explanation of why this change helps"
                        },
                        ...
                    ]"""},
                    {"role": "user", "content": f"""Original Resume:
                    {original_resume}
                    
                    Updated Resume:
                    {updated_resume}"""}
                ]
            )
            
            return json.loads(completion.choices[0].message.content)

        except Exception as e:
            st.error(f"Error analyzing changes: {str(e)}")
            return []

def main():
    st.title("Resume Customizer")
    
    # Initialize ResumeCustomizer
    customizer = ResumeCustomizer()
    
    # Display job counter
    st.sidebar.metric("Total Jobs Processed", customizer.job_counter)
    
    # Input section
    st.header("Job Description Input")
    input_method = st.radio("Choose input method:", ["URL", "Text"])
    
    job_description = None
    if input_method == "URL":
        url = st.text_input("Enter job posting URL:")
        if url:
            job_description = customizer.scrape_job_description(url)
    else:
        job_description = st.text_area("Paste job description:")
    
    # Process job description
    if job_description and st.button("Process Job Description"):
        with st.spinner("Processing..."):
            # Extract information
            company, position, keywords = customizer.extract_job_info(job_description)
            
            if company and position:
                st.success("Job information extracted successfully!")
                
                # Display extracted information
                st.subheader("Extracted Information")
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**Company:** {company}")
                with col2:
                    st.write(f"**Position:** {position}")
                
                # Display ATS keywords with importance and suggestions
                st.subheader("ATS Keywords Analysis")
                for kw in keywords:
                    with st.expander(f"{kw['keyword']} (ATS Importance: {kw['importance']}/10)"):
                        st.write(f"**Why important for ATS:** {kw['ats_reason']}")
                        st.write("**Common ATS variations:** " + ", ".join(kw['variations']))
                
                # Store original resume
                original_resume = customizer.base_resume
                
                # Customize resume
                customized_resume = customizer.customize_resume(job_description, keywords)
                
                # Analyze changes
                changes = customizer.analyze_changes(original_resume, customized_resume)
                
                # Save to session state
                st.session_state.customized_resume = customized_resume
                st.session_state.company = company
                st.session_state.position = position
                st.session_state.changes = changes
                
                # Increment and save counter
                customizer.job_counter += 1
                customizer.save_counter()
                
                # Refresh counter display
                st.sidebar.metric("Total Jobs Processed", customizer.job_counter)
    
    # Display customized resume and changes
    if 'customized_resume' in st.session_state:
        # Display changes first
        st.header("Changes Made")
        for change in st.session_state.changes:
            with st.expander(f"Change in {change['section']}"):
                st.write(f"**Type of Change:** {change['type']}")
                if change.get('original'):
                    st.write("**Original:**")
                    st.text(change['original'])
                if change.get('updated'):
                    st.write("**Updated:**")
                    st.text(change['updated'])
                st.write(f"**Impact:** {change['impact']}")
        
        # Display and edit resume
        st.header("Customized Resume")
        edited_resume = st.text_area(
            "Edit resume if needed:",
            st.session_state.customized_resume,
            height=400
        )
        
        # Save buttons
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Save Resume"):
                filename = customizer.save_resume(
                    edited_resume,
                    st.session_state.company,
                    st.session_state.position
                )
                st.success(f"Resume saved as {filename}")
        
        with col2:
            st.download_button(
                "Download Resume",
                edited_resume,
                file_name=f"{st.session_state.position}_{st.session_state.company}.md",
                mime="text/markdown"
            )

if __name__ == "__main__":
    main()