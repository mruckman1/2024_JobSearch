import os
import json
import logging
from datetime import datetime
from pathlib import Path
import requests
from bs4 import BeautifulSoup
import pypdf
from typing import Dict, List, Tuple
import time

class ResumeCustomizer:
    def __init__(self, config_path: str = "ollama_config.json"):
        self.config = self._load_config(config_path)
        self.setup_folders()
        self.setup_logging()
        
    def _load_config(self, config_path: str) -> Dict:
        """Load configuration from JSON file."""
        default_config = {
            "default_model": "llama3.1:8b-instruct-q8_0",
            "server_url": "http://localhost:11434",
            "max_retries": 3,
            "retry_delay": 1
        }
        
        try:
            with open(config_path, 'r') as f:
                return {**default_config, **json.load(f)}
        except FileNotFoundError:
            logging.warning(f"Config file not found at {config_path}. Using defaults.")
            return default_config

    def setup_folders(self):
        """Create necessary folder structure."""
        folders = ['Base_Resume', 'Context_Files', 'Outputs']
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

    def parse_pdf(self, pdf_path: str) -> str:
        """Extract text content from PDF while preserving structure."""
        try:
            text_content = []
            with open(pdf_path, 'rb') as file:
                pdf_reader = pypdf.PdfReader(file)
                for page in pdf_reader.pages:
                    text_content.append(page.extract_text())
            
            # Join pages with double newlines to preserve structure
            return "\n\n".join(text_content)
        except Exception as e:
            logging.error(f"Error parsing PDF: {str(e)}")
            raise

    def scrape_job_description(self, url: str) -> str:
        """Scrape job description from URL with improved error handling."""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Remove unwanted elements
            for tag in ['script', 'style', 'nav', 'header', 'footer']:
                for element in soup.find_all(tag):
                    element.decompose()
            
            # Try to find the job description container
            # Common class names for job descriptions
            possible_containers = [
                soup.find(class_=class_name) for class_name in [
                    'job-description', 'description', 'posting-description',
                    'content', 'main-content', 'job-details'
                ]
            ]
            
            # Use the first non-None container or fall back to body
            job_container = next((c for c in possible_containers if c), soup.find('body'))
            
            if not job_container:
                raise ValueError("Could not find job description content")
                
            text = job_container.get_text(separator='\n', strip=True)
            
            if not text:
                raise ValueError("Extracted text is empty")
                
            return text
            
        except requests.exceptions.RequestException as e:
            logging.error(f"Error fetching URL {url}: {str(e)}")
            manual_input = input("Failed to scrape job description. Would you like to paste it manually? (y/n): ")
            if manual_input.lower() == 'y':
                print("Please paste the job description (press Ctrl+D or Ctrl+Z when finished):")
                return "\n".join(iter(input, ""))
            raise
            
        except Exception as e:
            logging.error(f"Error parsing job description: {str(e)}")
            raise

    def _query_ollama(self, prompt: str, additional_content: str = "") -> str:
        """Query Ollama model with improved error handling."""
        retries = 0
        max_retries = self.config.get("max_retries", 3)
        
        while retries < max_retries:
            try:
                url = f"{self.config['server_url']}/api/generate"
                
                payload = {
                    "model": self.config["default_model"],
                    "prompt": f"{prompt}\n\n{additional_content}".strip(),
                    "stream": False
                }
                
                response = requests.post(url, json=payload, timeout=30)
                response.raise_for_status()
                
                result = response.json()
                return result.get('response', '')
                
            except requests.exceptions.RequestException as e:
                retries += 1
                if retries < max_retries:
                    logging.warning(f"Attempt {retries}/{max_retries} failed: {str(e)}")
                    time.sleep(self.config.get("retry_delay", 1) * retries)
                else:
                    logging.error(f"Failed to query Ollama after {max_retries} attempts")
                    raise
            except Exception as e:
                logging.error(f"Unexpected error querying Ollama: {str(e)}")
                raise

    def extract_job_requirements(self, job_description: str) -> Dict:
        """Extract key requirements from job description."""
        try:
            prompt = """
            Analyze this job description and extract the following information in JSON format:
            {
                "required_skills": [],
                "required_qualifications": [],
                "key_responsibilities": []
            }

            Job Description:
            """
            
            response = self._query_ollama(prompt, job_description)
            
            # Extract JSON from response
            import re
            json_match = re.search(r'\{[\s\S]*\}', response)
            if not json_match:
                raise ValueError("No JSON found in response")
                
            requirements = json.loads(json_match.group())
            
            # Validate the response has the expected structure
            expected_keys = ["required_skills", "required_qualifications", "key_responsibilities"]
            if not all(key in requirements for key in expected_keys):
                raise ValueError("Missing required keys in response")
                
            return requirements
            
        except Exception as e:
            logging.error(f"Error extracting requirements: {str(e)}")
            # Return empty structure rather than failing
            return {
                "required_skills": [],
                "required_qualifications": [],
                "key_responsibilities": []
            }

    def customize_resume(self, resume_text: str, job_requirements: Dict) -> Tuple[str, List[Dict]]:
        """Customize resume based on job requirements."""
        prompt = """
        Given this resume and job requirements, rewrite the resume to better match the job while maintaining truthfulness.
        
        Resume:
        {resume}
        
        Job Requirements:
        {requirements}
        
        Provide your response in the following format:
        
        UPDATED_RESUME:
        [Your updated resume text here]
        
        CHANGES:
        [A JSON array of changes, each with 'original' and 'updated' fields]
        """.format(
            resume=resume_text,
            requirements=json.dumps(job_requirements, indent=2)
        )

        response = self._query_ollama(prompt)
        
        try:
            # Split response into resume and changes sections
            if "UPDATED_RESUME:" not in response or "CHANGES:" not in response:
                raise ValueError("Response format incorrect")
                
            # Extract updated resume
            resume_parts = response.split("UPDATED_RESUME:")
            changes_parts = resume_parts[1].split("CHANGES:")
            
            updated_resume = changes_parts[0].strip()
            changes_text = changes_parts[1].strip()
            
            # Parse changes JSON
            # Find the JSON array in the text
            import re
            json_match = re.search(r'\[[\s\S]*\]', changes_text)
            if not json_match:
                raise ValueError("No changes JSON found in response")
                
            changes = json.loads(json_match.group())
            
            return updated_resume, changes
        except Exception as e:
            logging.error(f"Error parsing model response: {str(e)}")
            # Return original resume and empty changes list on error
            return resume_text, []

    def generate_output_files(self, 
                            updated_resume: str, 
                            changes: List[Dict], 
                            job_title: str) -> Tuple[str, str]:
        """Generate output files with updated resume and change log."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        model_name = self.config["default_model"]
        
        # Save updated resume
        resume_filename = f"Outputs/Updated_Resume_{job_title}_{timestamp}_{model_name}.txt"
        with open(resume_filename, 'w') as f:
            f.write(updated_resume)
        
        # Save change log
        log_filename = f"Outputs/Change_Log_{job_title}_{timestamp}_{model_name}.json"
        with open(log_filename, 'w') as f:
            json.dump(changes, f, indent=2)
            
        return resume_filename, log_filename

def main():
    # Initialize customizer
    customizer = ResumeCustomizer()
    
    try:
        # Parse resume
        resume_text = customizer.parse_pdf("Base_Resume/resume.pdf")
        logging.info("Resume parsed successfully")
        
        # Get job description
        job_url = input("Enter job posting URL: ")
        job_description = customizer.scrape_job_description(job_url)
        logging.info("Job description scraped successfully")
        
        # Extract requirements
        requirements = customizer.extract_job_requirements(job_description)
        logging.info("Job requirements extracted successfully")
        
        # Customize resume
        job_title = input("Enter job title for file naming: ")
        updated_resume, changes = customizer.customize_resume(resume_text, requirements)
        logging.info("Resume customization completed")
        
        # Generate output files
        resume_file, log_file = customizer.generate_output_files(
            updated_resume, changes, job_title)
        
        logging.info(f"Updated resume saved to: {resume_file}")
        logging.info(f"Change log saved to: {log_file}")
        
    except Exception as e:
        logging.error(f"Error in main process: {str(e)}")
        raise

if __name__ == "__main__":
    main()