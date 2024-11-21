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
        """Simple scraper to get all text content from any job posting URL."""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
            }
            
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            # Parse the HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Remove script and style elements
            for element in soup(['script', 'style']):
                element.decompose()
                
            # Get all text
            text = soup.get_text(separator='\n')
            
            # Clean up the text
            lines = (line.strip() for line in text.splitlines())
            # Break multi-line paragraphs into a single line
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            # Drop empty lines
            text = '\n'.join(chunk for chunk in chunks if chunk)
            
            if not text:
                st.error("No content found on the page")
                return None
                
            return text
            
        except Exception as e:
            st.error(f"Error accessing URL: {str(e)}")
            return None

    def extract_job_info(self, job_description: str) -> Tuple[str, str, List[Dict]]:
        """Extract job title, company name, and key keywords with relevance."""
        try:
            # Extract company and position
            completion = self.client.chat.completions.create(
                model="gpt-4o-2024-11-20",
                messages=[
                    {"role": "system", "content": """You are an experienced recruiter and ATS specialist. 
                    Extract the company name and exact position title from this job description.
                    
                    Respond in exactly this format:
                    Company: [company name]
                    Position: [position title]"""},
                    {"role": "user", "content": job_description}
                ]
            )
            job_info = completion.choices[0].message.content
            company_name = re.search(r'Company:\s*(.*)', job_info).group(1)
            position_title = re.search(r'Position:\s*(.*)', job_info).group(1)

            # Extract ATS-focused keywords with context analysis
            completion = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": """You are an experienced ATS system analyst and recruiter.
                    Analyze this job description and identify the 10 most important keywords/phrases that are 
                    likely to be used in ATS filtering systems.

                    YOU MUST RETURN A VALID JSON ARRAY IN EXACTLY THIS FORMAT:
                    [
                        {
                            "keyword": "exact term from job description",
                            "importance": 9,
                            "ats_reason": "why this is likely an ATS filter",
                            "variations": ["variation 1", "variation 2"]
                        }
                    ]

                    REQUIREMENTS:
                    - Must be valid JSON
                    - Must be an array of exactly 10 items
                    - Each item must have all four fields
                    - 'importance' must be a number between 1 and 10
                    - 'variations' must be an array of strings
                    - No trailing commas
                    - No comments
                    - No additional text before or after the JSON"""},
                    {"role": "user", "content": job_description}
                ]
            )
            
            try:
                response_text = completion.choices[0].message.content.strip()
                # Remove any potential text before or after the JSON array
                json_start = response_text.find('[')
                json_end = response_text.rfind(']') + 1
                if json_start >= 0 and json_end > json_start:
                    json_text = response_text[json_start:json_end]
                    keywords = json.loads(json_text)
                else:
                    raise ValueError("No JSON array found in response")

            except (json.JSONDecodeError, ValueError) as e:
                logging.error(f"JSON parsing error: {str(e)}\nResponse: {response_text}")
                # Provide a fallback structure if JSON parsing fails
                keywords = [
                    {
                        "keyword": "fallback_keyword",
                        "importance": 5,
                        "ats_reason": "Parsing error occurred",
                        "variations": ["alternative"]
                    }
                ]
                
            return company_name, position_title, keywords

        except Exception as e:
            st.error(f"Error extracting job information: {str(e)}")
            logging.error(f"Job info extraction error: {str(e)}", exc_info=True)
            return None, None, []

    # Add the missing save_resume method:
    def save_resume(self, content: str, company: str, position: str) -> str:
        """Save resume as markdown file with proper error handling."""
        try:
            # Clean the company and position names for filename
            def clean_filename(s: str) -> str:
                # Replace any characters that aren't alphanumeric or spaces with underscore
                s = re.sub(r'[^\w\s-]', '_', s)
                # Replace multiple spaces or underscores with single underscore
                s = re.sub(r'[\s_]+', '_', s)
                return s.strip('_')

            company_clean = clean_filename(company)
            position_clean = clean_filename(position)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            filename = f"outputs/{position_clean}_{company_clean}_{timestamp}.md"
            
            # Ensure outputs directory exists
            Path('outputs').mkdir(exist_ok=True)
            
            # Write content to file
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(content)
                
            logging.info(f"Resume saved successfully to {filename}")
            return filename

        except Exception as e:
            error_msg = f"Error saving resume: {str(e)}"
            logging.error(error_msg, exc_info=True)
            st.error(error_msg)
            return ""

    def customize_resume(self, job_description: str, keywords: List[Dict]) -> str:
        """Customize resume based on job description and keywords, using context information."""
        try:
            completion = self.client.chat.completions.create(
                model="gpt-4o-2024-11-20",
                messages=[
                    {"role": "system", "content": """You are an expert resume optimization specialist.
                    Your task is to customize the resume to better match the job requirements while maintaining
                    complete truthfulness and authenticity. 
                    
                    Focus on:
                    1. Incorporating ATS keywords naturally
                    2. Using exact phrases from the job description
                    3. Matching the seniority level and tone
                    4. Highlighting relevant experience that matches requirements
                    
                    CRITICAL REQUIREMENTS:
                    - Must maintain ALL experience entries from the original resume
                    - Do not remove any positions or experience
                    - Only enhance and modify existing content
                    - Maintain the exact same sections and structure
                    - Keep all dates and company information intact
                    
                    IMPORTANT OUTPUT INSTRUCTIONS:
                    - Return ONLY the updated resume content in markdown format
                    - Start directly with the resume header
                    - Maintain exact markdown formatting with proper spacing
                    - Include ALL original positions and experiences
                    - Do not truncate or remove any sections
                    - Do not add commentary or explanations"""},
                    {"role": "user", "content": f"""Base Resume:
                    {self.base_resume}
                    
                    Additional Context Information:
                    {self.context_info}
                    
                    Job Description:
                    {job_description}
                    
                    ATS Keywords to Integrate:
                    {json.dumps(keywords, indent=2)}"""}
                ],
                temperature=0.5  # Lower temperature for more consistent output
            )
            
            # Clean up any potential commentary before or after the resume
            resume_content = completion.choices[0].message.content
            resume_lines = [line for line in resume_content.split('\n') 
                        if not line.strip().lower().startswith(('here', 'this resume', 'based on', 'i have', 'note:', 'summary:'))]
            cleaned_resume = '\n'.join(resume_lines).strip()
            
            # Verify all original positions are present
            original_positions = re.findall(r'###\s+[^#\n]+', self.base_resume)
            updated_positions = re.findall(r'###\s+[^#\n]+', cleaned_resume)
            
            if len(original_positions) != len(updated_positions):
                logging.error("Position count mismatch. Falling back to base resume with keyword integration")
                return self._fallback_resume_update(self.base_resume, keywords)
                
            return cleaned_resume

        except Exception as e:
            st.error(f"Error customizing resume: {str(e)}")
            return self._fallback_resume_update(self.base_resume, keywords)

    def _fallback_resume_update(self, base_resume: str, keywords: List[Dict]) -> str:
        """Simple fallback method to integrate keywords into base resume while maintaining structure."""
        try:
            # Modify profile section to include key terms
            sections = base_resume.split('\n\n')
            for i, section in enumerate(sections):
                if section.startswith('## Profile'):
                    profile_text = sections[i+1]
                    keyword_terms = [kw['keyword'] for kw in keywords if kw['importance'] >= 8]
                    enhanced_profile = f"Results-driven professional with expertise in {', '.join(keyword_terms[:3])}. " + profile_text
                    sections[i+1] = enhanced_profile
                    break
            
            return '\n\n'.join(sections)
            
        except Exception as e:
            logging.error(f"Error in fallback resume update: {str(e)}")
            return base_resume

    def analyze_changes(self, original_resume: str, updated_resume: str) -> List[Dict]:
        """Analyze and summarize the changes made to the resume."""
        try:
            completion = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": """You are an expert resume analyst.
                    Compare the original and updated resumes and identify all meaningful changes.
                    You must respond with a valid JSON array containing objects with the following structure:
                    [
                        {
                            "type": "addition|modification|restructure",
                            "section": "section name",
                            "original": "original text if applicable",
                            "updated": "new text if applicable",
                            "impact": "explanation of why this change helps"
                        }
                    ]

                    REQUIREMENTS:
                    - Response must be a valid JSON array
                    - Each object must have all five fields
                    - 'type' must be one of: "addition", "modification", or "restructure"
                    - Do not include any text before or after the JSON array
                    - Ensure proper JSON formatting with no trailing commas"""},
                    {"role": "user", "content": f"""Original Resume:
                    {original_resume}
                    
                    Updated Resume:
                    {updated_resume}"""}
                ],
                temperature=0.3  # Lower temperature for more consistent JSON formatting
            )
            
            try:
                response_text = completion.choices[0].message.content.strip()
                # Remove any potential text before or after the JSON array
                json_start = response_text.find('[')
                json_end = response_text.rfind(']') + 1
                
                if json_start >= 0 and json_end > json_start:
                    json_text = response_text[json_start:json_end]
                    changes = json.loads(json_text)
                    
                    # Validate the structure of each change
                    for change in changes:
                        required_fields = ['type', 'section', 'original', 'updated', 'impact']
                        if not all(field in change for field in required_fields):
                            raise ValueError("Missing required fields in change object")
                        if change['type'] not in ['addition', 'modification', 'restructure']:
                            change['type'] = 'modification'  # Default to modification if invalid type
                    
                    return changes
                else:
                    logging.error(f"Invalid response format. Response: {response_text}")
                    return self._generate_fallback_changes(original_resume, updated_resume)

            except (json.JSONDecodeError, ValueError) as e:
                logging.error(f"Error parsing changes response: {str(e)}\nResponse: {response_text}")
                return self._generate_fallback_changes(original_resume, updated_resume)

        except Exception as e:
            st.error(f"Error analyzing changes: {str(e)}")
            logging.error(f"Changes analysis error: {str(e)}", exc_info=True)
            return self._generate_fallback_changes(original_resume, updated_resume)

    def _generate_fallback_changes(self, original_resume: str, updated_resume: str) -> List[Dict]:
        """Generate basic changes analysis when the main analysis fails."""
        try:
            # Use difflib to find differences
            differ = difflib.Differ()
            diff = list(differ.compare(original_resume.splitlines(), updated_resume.splitlines()))
            
            changes = []
            current_section = "General"
            current_change = {"type": "modification", "section": current_section, 
                            "original": [], "updated": [], "impact": "Updated content to better match job requirements"}
            
            for line in diff:
                if line.startswith('- '):
                    current_change["original"].append(line[2:])
                elif line.startswith('+ '):
                    current_change["updated"].append(line[2:])
                
                # Check for section headers to organize changes better
                if line.startswith(('# ', '## ', '### ')):
                    current_section = line.strip('#').strip()
                    if current_change["original"] or current_change["updated"]:
                        current_change["original"] = "\n".join(current_change["original"])
                        current_change["updated"] = "\n".join(current_change["updated"])
                        changes.append(current_change)
                    current_change = {"type": "modification", "section": current_section, 
                                    "original": [], "updated": [], 
                                    "impact": "Updated content to better match job requirements"}
            
            # Add the last change if it exists
            if current_change["original"] or current_change["updated"]:
                current_change["original"] = "\n".join(current_change["original"])
                current_change["updated"] = "\n".join(current_change["updated"])
                changes.append(current_change)
            
            return changes or [{"type": "modification", 
                            "section": "General",
                            "original": "Original resume content",
                            "updated": "Updated resume content",
                            "impact": "Resume updated to better match job requirements"}]

        except Exception as e:
            logging.error(f"Error in fallback changes analysis: {str(e)}", exc_info=True)
            return [{"type": "modification", 
                    "section": "General",
                    "original": "Original resume content",
                    "updated": "Updated resume content",
                    "impact": "Resume updated to better match job requirements"}]

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