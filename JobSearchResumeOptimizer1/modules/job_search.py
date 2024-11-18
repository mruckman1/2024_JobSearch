# modules/job_search.py

import requests
import logging
from typing import List, Dict
from bs4 import BeautifulSoup

class JobSearchAPI:
    def search_jobs(self, query: str) -> List[Dict]:
        """Abstract method to search for jobs based on a query."""
        raise NotImplementedError

class BingJobSearchAPI(JobSearchAPI):
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.endpoint = "https://api.bing.microsoft.com/v7.0/search"
    
    def search_jobs(self, query: str) -> List[Dict]:
        """Search for jobs using Bing Search API."""
        headers = {"Ocp-Apim-Subscription-Key": self.api_key}
        params = {
            "q": query,
            "responseFilter": "Webpages",
            "count": 5
        }
        response = requests.get(self.endpoint, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()
        results = []
        if "webPages" in data:
            for idx, item in enumerate(data["webPages"]["value"]):
                job = self.parse_job_posting(item["url"], idx)
                if job:
                    results.append(job)
        return results

    def parse_job_posting(self, url: str, job_id: int) -> Dict:
        """Parse the job posting at the given URL to extract job details."""
        try:
            response = requests.get(url)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            job = {
                'id': job_id,
                'url': url,
                'title': self.extract_title(soup),
                'company': self.extract_company(soup),
                'location': self.extract_location(soup),
                'description': self.extract_description(soup),
                'base_compensation': self.extract_compensation(soup)
            }
            return job
        except Exception as e:
            logging.error(f"Error parsing job posting at {url}: {e}")
            return None

    def extract_title(self, soup) -> str:
        title = soup.find('h1')
        return title.get_text(strip=True) if title else "N/A"

    def extract_company(self, soup) -> str:
        # Implement logic to extract company name
        return "Company Name"

    def extract_location(self, soup) -> str:
        # Implement logic to extract location
        return "Location"

    def extract_description(self, soup) -> str:
        description = soup.find('div', {'class': 'job-description'})
        if description:
            return description.get_text(separator='\n', strip=True)
        else:
            # Fallback to extracting all text
            return soup.get_text(separator='\n', strip=True)

    def extract_compensation(self, soup) -> str:
        # Implement logic to extract base compensation
        return "Base Compensation"

def search_and_store_jobs(search_api: JobSearchAPI, query: str) -> List[Dict]:
    """Search for jobs and store the results."""
    jobs = search_api.search_jobs(query)
    return jobs
