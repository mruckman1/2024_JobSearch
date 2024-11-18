# main.py

import logging
import os
import json
from modules.job_search import BingJobSearchAPI, search_and_store_jobs
from modules.keyword_extraction import extract_keywords
from modules.resume_customizer import customize_resume
from modules.datastore import DataStore

def main():
    # Setup logging
    logging.basicConfig(level=logging.INFO)

    # Load configuration
    with open('config/config.json', 'r') as f:
        config = json.load(f)

    # Initialize datastore
    datastore = DataStore(db_path=config['datastore']['path'])

    # Initialize job search API
    search_api = BingJobSearchAPI(api_key=config['bing_api_key'])

    # Get user input for search query
    query = input("Enter your job search query: ")

    # Search for jobs
    jobs = search_and_store_jobs(search_api, query)

    # For each job, extract keywords and customize resume
    for job in jobs:
        # Extract job description
        job_description = job['description']
        # Extract keywords
        keywords = extract_keywords(job_description)
        # Customize resume
        resume_path = os.path.join('data', 'resumes', 'resume.docx')
        context_docs_path = os.path.join('data', 'context_docs')
        customized_resume = customize_resume(resume_path, keywords, context_docs_path)
        if customized_resume:
            # Store customized resume
            output_filename = f"customized_resume_{job['id']}.docx"
            output_path = os.path.join('data', 'outputs', output_filename)
            customized_resume.save(output_path)
            # Store in datastore
            datastore.save_job_application(job, output_path)
            logging.info(f"Customized resume saved to {output_path}")
        else:
            logging.error("Failed to customize resume")

if __name__ == '__main__':
    main()
