# /Users/mruckman1/Desktop/JobSearchResumeOptimizer1/resume-customizer/main.py
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
from io import BytesIO
from markdown_docx_converter import convert_to_docx  # Assuming you saved the above code as markdown_docx_converter.py
import html
import re
from datetime import datetime, timedelta  # Add timedelta here
import shutil
from typing import Optional
from database import JobApplicationsDB, JobApplication

class ResumeCustomizer:
    def __init__(self):
        self.db = JobApplicationsDB()
        
        # Define all folder paths
        self.resume_folder = Path('Resume_Context/Resume')
        self.context_folder = Path('Resume_Context/Context')
        self.legacy_data_folder = Path('data')  # Add this line
        
        self.setup_folders()
        self.setup_logging()
        
        # Initialize with first available files or None
        self.current_resume_file = None
        self.current_context_file = None
        self.base_resume = ""
        self.context_info = ""
        
        # Load available files
        self.load_available_files()
        
        # Initialize OpenAI client
        try:
            self.client = OpenAI(api_key=st.secrets.openai.api_key)
        except (FileNotFoundError, AttributeError):
            st.error("OpenAI API key not found. Please ensure you have created .streamlit/secrets.toml with your API key.")
            st.stop()
    
    def save_application_to_db(self, job_description: str, input_type: str, 
                            company: str, position: str, keywords: str, 
                            customized_resume: str, changes: str) -> int:
        """Save the job application details to the database."""
        application = JobApplication(
            id=None,  # Will be set by the database
            timestamp=datetime.now(),
            company=company,
            position=position,
            input_type=input_type,
            input_content=job_description,
            generated_resume=customized_resume,
            base_resume_file=self.current_resume_file,
            context_file=self.current_context_file,
            keywords=keywords,
            changes=changes
        )
        
        return self.db.save_application(application)    
    
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
    
    def setup_folders(self):
        """Create necessary folder structure while maintaining legacy folders."""
        folders = [
            'Resume_Context/Resume', 
            'Resume_Context/Context', 
            'outputs',
            'data',  # Keep legacy folder
            'data/resumes',  # Keep legacy folder
            'data/context'   # Keep legacy folder
        ]
        for folder in folders:
            Path(folder).mkdir(parents=True, exist_ok=True)

    def get_available_files(self, folder_path: Path, legacy_path: Optional[Path] = None) -> list:
        """Get list of available files with legacy path fallback."""
        files = []
        
        # Check primary folder
        if folder_path.exists():
            files.extend([f.name for f in folder_path.glob('*') if f.suffix.lower() in ['.txt', '.md']])
        
        # Check legacy folder if provided
        if legacy_path and legacy_path.exists():
            legacy_files = [f.name for f in legacy_path.glob('*') if f.suffix.lower() in ['.txt', '.md']]
            # Only add legacy files that aren't already in the new location
            files.extend([f for f in legacy_files if f not in files])
            
        return sorted(files)

    def load_available_files(self):
        """Load files with fallback to legacy locations."""
        # Check new locations first, then legacy
        resume_files = self.get_available_files(
            self.resume_folder, 
            self.legacy_data_folder / 'resumes'
        )
        context_files = self.get_available_files(
            self.context_folder, 
            self.legacy_data_folder / 'context'
        )
        
        # Set current files if available
        if resume_files:
            self.current_resume_file = resume_files[0]
        if context_files:
            self.current_context_file = context_files[0]
            
        # Load the files
        self.load_base_files()    
    
    def load_base_files(self):
        """Load base files with fallback to legacy locations."""
        try:
            if self.current_resume_file:
                # Try new location first
                resume_path = self.resume_folder / self.current_resume_file
                if not resume_path.exists():
                    # Try legacy locations
                    legacy_paths = [
                        self.legacy_data_folder / 'resumes' / self.current_resume_file,
                        self.legacy_data_folder / self.current_resume_file
                    ]
                    for path in legacy_paths:
                        if path.exists():
                            resume_path = path
                            break
                
                with open(resume_path, 'r', encoding='utf-8') as f:
                    self.base_resume = f.read()
            
            if self.current_context_file:
                # Try new location first
                context_path = self.context_folder / self.current_context_file
                if not context_path.exists():
                    # Try legacy locations
                    legacy_paths = [
                        self.legacy_data_folder / 'context' / self.current_context_file,
                        self.legacy_data_folder / self.current_context_file
                    ]
                    for path in legacy_paths:
                        if path.exists():
                            context_path = path
                            break
                
                with open(context_path, 'r', encoding='utf-8') as f:
                    self.context_info = f.read()
                    
            logging.info("Base files loaded successfully")
            
        except Exception as e:
            logging.error(f"Error loading base files: {str(e)}")
            raise

    def update_base_file(self, file_type: str, uploaded_file) -> bool:
        """Update base file with proper migration handling."""
        try:
            if not uploaded_file:
                return False

            if file_type == 'resume':
                target_dir = self.resume_folder
                current_file_attr = 'current_resume_file'
            else:  # context
                target_dir = self.context_folder
                current_file_attr = 'current_context_file'

            # Save the uploaded file to new location
            file_path = target_dir / uploaded_file.name
            with open(file_path, 'wb') as f:
                f.write(uploaded_file.getbuffer())

            # Also save to legacy location for backward compatibility
            legacy_dir = self.legacy_data_folder / ('resumes' if file_type == 'resume' else 'context')
            legacy_path = legacy_dir / uploaded_file.name
            shutil.copy2(file_path, legacy_path)

            # Update the current file attribute
            setattr(self, current_file_attr, uploaded_file.name)
            
            # Reload the base files
            self.load_base_files()
            
            return True
            
        except Exception as e:
            logging.error(f"Error updating {file_type} file: {str(e)}")
            return False

    def get_file_options(self) -> tuple:
        """Get lists of available files from both new and legacy locations."""
        resume_files = self.get_available_files(
            self.resume_folder,
            self.legacy_data_folder / 'resumes'
        )
        context_files = self.get_available_files(
            self.context_folder,
            self.legacy_data_folder / 'context'
        )
        return resume_files, context_files

    def switch_files(self, resume_file: str = None, context_file: str = None) -> bool:
        """Switch files with validation."""
        try:
            if resume_file:
                # Validate file exists in either location
                resume_exists = (
                    (self.resume_folder / resume_file).exists() or
                    (self.legacy_data_folder / 'resumes' / resume_file).exists() or
                    (self.legacy_data_folder / resume_file).exists()
                )
                if not resume_exists:
                    raise FileNotFoundError(f"Resume file {resume_file} not found")
                self.current_resume_file = resume_file
                
            if context_file:
                # Validate file exists in either location
                context_exists = (
                    (self.context_folder / context_file).exists() or
                    (self.legacy_data_folder / 'context' / context_file).exists() or
                    (self.legacy_data_folder / context_file).exists()
                )
                if not context_exists:
                    raise FileNotFoundError(f"Context file {context_file} not found")
                self.current_context_file = context_file
                
            self.load_base_files()
            return True
            
        except Exception as e:
            logging.error(f"Error switching files: {str(e)}")
            return False

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
                model="gpt-4o-2024-11-20",
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
        try:
            completion = self.client.chat.completions.create(
                model="gpt-4o-2024-11-20",  # Update to latest model
                messages=[
                    {"role": "system", "content": """You are an expert resume optimization specialist.
                    Your task is to customize the resume to better match the job requirements while maintaining
                    complete truthfulness and authenticity. 
                    
                    CRITICAL REQUIREMENTS:
                    - The section headers must remain exactly as they are (###)
                    - Each job entry must start with '### ' followed by the exact position, company, location and dates
                    - Do not change any dates or company names
                    - Only enhance descriptions and achievements
                    - Keep all sections in the same order
                    - Maintain markdown formatting
                    - Do not add additional certifications or expand on language skills
                    
                    Format job entries exactly like this:
                    ### Position | Company | Location | Dates
                    
                    IMPORTANT:
                    - Return ONLY the updated resume content
                    - Start with profile section
                    - Maintain exact markdown formatting
                    - Do not add commentary"""},
                    {"role": "user", "content": f"""Base Resume:
                    {self.base_resume}
                    
                    Additional Context:
                    {self.context_info}
                    
                    Job Description:
                    {job_description}
                    
                    ATS Keywords to Integrate:
                    {json.dumps(keywords, indent=2)}"""}
                ],
                temperature=0.3
            )
            
            resume_content = completion.choices[0].message.content.strip()
            
            # Clean up the resume content
            resume_content = self._clean_resume_text(resume_content)
            
            # Verify critical elements are present
            if not all(x in resume_content for x in ['## Profile', '## Work Experience', '## Education']):
                logging.error("Missing required sections")
                return self._fallback_resume_update(self.base_resume, keywords)
                
            # Verify job entries format
            job_entries = re.findall(r'###\s+[^|]+\|[^|]+\|[^|]+\|[^|\n]+', resume_content)
            if not job_entries:
                logging.error("Job entries not properly formatted")
                return self._fallback_resume_update(self.base_resume, keywords)
                
            return resume_content

        except Exception as e:
            logging.error(f"Error customizing resume: {str(e)}")
            return self._fallback_resume_update(self.base_resume, keywords)

    def _clean_resume_text(self, text: str) -> str:
        """Clean up resume text by removing HTML and fixing special characters."""
        # Decode HTML entities
        text = html.unescape(text)
        
        # Remove HTML links but keep the text
        text = re.sub(r'<a href="[^"]*">(.*?)</a>', r'\1', text)
        
        # Fix spacing around headers
        text = re.sub(r'(\n#{1,3}[^\n]+)\n([^\n])', r'\1\n\n\2', text)
        
        # Ensure proper spacing between sections
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # Fix bullet points spacing
        text = re.sub(r'(\n-[^\n]+)\n([^\n-])', r'\1\n\n\2', text)
        
        return text        

    def _fallback_resume_update(self, base_resume: str, keywords: List[Dict]) -> str:
        try:
            # Clean up the base resume first
            base_resume = self._clean_resume_text(base_resume)
            sections = base_resume.split('\n\n')
            updated_sections = []
            
            for section in sections:
                if section.startswith('## Profile'):
                    # Enhance profile with top keywords
                    keyword_terms = [kw['keyword'] for kw in keywords if kw['importance'] >= 8]
                    profile_text = sections[sections.index(section) + 1]
                    enhanced_profile = (f"Results-driven professional with expertise in "
                                    f"{', '.join(keyword_terms[:3])}. {profile_text}")
                    updated_sections.extend([section, enhanced_profile])
                    
                elif section.startswith('### '):
                    # Enhance job descriptions with relevant keywords
                    relevant_keywords = [kw['keyword'] for kw in keywords if kw['importance'] >= 7]
                    bullet_points = section.split('\n- ')
                    enhanced_points = []
                    for point in bullet_points:
                        if not point.startswith('###'):
                            for keyword in relevant_keywords:
                                if keyword.lower() in point.lower():
                                    point = f"Leveraged {keyword} to " + point
                                    break
                        enhanced_points.append(point)
                    updated_sections.append('\n- '.join(enhanced_points))
                    
                else:
                    updated_sections.append(section)
                    
            return '\n\n'.join(updated_sections)
            
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
    
    # Add file selection section in sidebar
    st.sidebar.header("Current Files")
    
    # Get available files
    resume_files, context_files = customizer.get_file_options()
    
    # File selection
    with st.sidebar.expander("Select Files", expanded=True):
        # Resume selection
        if resume_files:
            selected_resume = st.selectbox(
                "Select Resume",
                options=resume_files,
                index=resume_files.index(customizer.current_resume_file) if customizer.current_resume_file in resume_files else 0
            )
            if selected_resume != customizer.current_resume_file:
                customizer.switch_files(resume_file=selected_resume)
                st.rerun()
        else:
            st.warning("No resume files found in Resume folder")
        
        # Context selection
        if context_files:
            selected_context = st.selectbox(
                "Select Context",
                options=context_files,
                index=context_files.index(customizer.current_context_file) if customizer.current_context_file in context_files else 0
            )
            if selected_context != customizer.current_context_file:
                customizer.switch_files(context_file=selected_context)
                st.rerun()
        else:
            st.warning("No context files found in Context folder")
    
    # Display current files
    st.sidebar.write(f"**Current Resume:** {customizer.current_resume_file or 'None'}")
    st.sidebar.write(f"**Current Context:** {customizer.current_context_file or 'None'}")
    
    # Add file upload widgets
    with st.sidebar.expander("Upload New Files"):
        # Resume upload
        new_resume = st.file_uploader("Upload New Resume", type=['md', 'txt'])
        if new_resume is not None:
            if st.button("Update Resume"):
                if customizer.update_base_file('resume', new_resume):
                    st.success(f"Resume updated to: {new_resume.name}")
                    st.rerun()
                else:
                    st.error("Failed to update resume")
        
        # Context upload
        new_context = st.file_uploader("Upload New Context File", type=['txt'])
        if new_context is not None:
            if st.button("Update Context"):
                if customizer.update_base_file('context', new_context):
                    st.success(f"Context file updated to: {new_context.name}")
                    st.rerun()
                else:
                    st.error("Failed to update context file")
    
    # Display application tracking in sidebar
    st.sidebar.header("Application Tracking")
    
    # Get counters from database
    total_count, weekly_count, monthly_count = customizer.db.get_counters()
    tracking_start = customizer.db.get_tracking_start_date()
    
    # Create three columns for the metrics
    col1, col2, col3 = st.sidebar.columns(3)
    with col1:
        st.metric("Total", total_count)
    with col2:
        st.metric("This Week", weekly_count)
    with col3:
        st.metric("This Month", monthly_count)
    
    # Format timestamp nicely
    timestamp_str = tracking_start.strftime("%B %d, %Y")
    st.sidebar.write(f"Tracking since: {timestamp_str}")

    # Add application history section in sidebar
    st.sidebar.header("Recent Applications")
    recent_apps = customizer.db.get_recent_applications(5)
    for app in recent_apps:
        with st.sidebar.expander(f"{app.company} - {app.position}"):
            st.write(f"Date: {app.timestamp.strftime('%Y-%m-%d %H:%M')}")
            st.write(f"Input Type: {app.input_type}")
            if st.button("Load This Application", key=f"load_{app.id}"):
                st.session_state.customized_resume = app.generated_resume
                st.session_state.company = app.company
                st.session_state.position = app.position
                st.session_state.changes = json.loads(app.changes)
                st.rerun()

    # Add statistics
    st.sidebar.header("Application Statistics")
    stats = customizer.db.get_statistics()
    st.sidebar.metric("Total Applications", stats['total_applications'])

    # Show top companies
    st.sidebar.subheader("Top Companies")
    for company, count in stats['top_companies'].items():
        st.sidebar.text(f"{company}: {count} applications")
    
    # Input section
    st.header("Job Description Input")
    input_method = st.radio("Choose input method:", ["URL", "Text"])
    
    # Wrap input in a form
    with st.form(key='job_description_form'):
        job_description = None
        if input_method == "URL":
            url = st.text_input("Enter job posting URL and press Enter:")
            if url:
                job_description = customizer.scrape_job_description(url)
                st.markdown("""
                    <style>
                    [data-testid="stFormSubmitButton"] {
                        display: none;
                    }
                    </style>
                    """, unsafe_allow_html=True)
        else:
            job_description = st.text_area("Paste job description:")
            
        submit_button = st.form_submit_button("Process Job Description")
    
    # Move processing logic outside the form but check for submission
    if submit_button and job_description:
        with st.spinner("Processing..."):
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
                
                # Save application to database
                application_id = customizer.save_application_to_db(
                    job_description=job_description,
                    input_type='url' if input_method == "URL" else 'text',
                    company=company,
                    position=position,
                    keywords=json.dumps(keywords),
                    customized_resume=customized_resume,
                    changes=json.dumps(changes)
                )
                
                # Save to session state
                st.session_state.customized_resume = customized_resume
                st.session_state.company = company
                st.session_state.position = position
                st.session_state.changes = changes
                
                # Refresh the sidebar metrics
                st.rerun()
    
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
                # Convert to DOCX
                doc = convert_to_docx(edited_resume)
                filename_base = f"{st.session_state.position}_{st.session_state.company}"
                filename_md = f"outputs/{filename_base}.md"
                filename_docx = f"outputs/{filename_base}.docx"
                
                # Save both versions
                with open(filename_md, 'w', encoding='utf-8') as f:
                    f.write(edited_resume)
                doc.save(filename_docx)
                st.success(f"Resume saved as {filename_md} and {filename_docx}")

        with col2:
            # Create DOCX in memory for download
            doc = convert_to_docx(edited_resume)
            docx_bio = BytesIO()
            doc.save(docx_bio)
            docx_bio.seek(0)
            
            st.download_button(
                "Download Resume (DOCX)",
                docx_bio,
                file_name=f"{st.session_state.position}_{st.session_state.company}.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )
            
            # Also provide markdown download option
            st.download_button(
                "Download Resume (MD)",
                edited_resume,
                file_name=f"{st.session_state.position}_{st.session_state.company}.md",
                mime="text/markdown"
            )
        
        # Add Clear button at the bottom
        st.write("")  # Add some spacing
        if st.button("Clear and Start New"):
            # Clear all relevant session state variables
            for key in ['customized_resume', 'company', 'position', 'changes']:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()

if __name__ == "__main__":
    main()