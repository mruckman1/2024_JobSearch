### Project Description:

The Job Search Resume Optimizer is an automated tool designed to streamline the job application process. It uses advanced AI technologies and APIs to search for relevant job postings, extract critical keywords from job descriptions, and customize resumes to align with specific job requirements. The project ensures resumes are optimized for Applicant Tracking Systems (ATS) while maintaining accuracy and authenticity. It also organizes all job postings, extracted data, and customized resumes in an easily queryable datastore, making the job search process efficient and highly personalized. The project is modular, extensible, and designed to integrate with various AI and search APIs.

---

### **Requirements**

#### **Functional Requirements**
1. **Job Search**:
   - Search for job postings using APIs (e.g., Bing, Google, or Serper).
   - Extract job details: title, company, location, base compensation, and full job description.
   - Match postings to the candidate's resume and compensation expectations.
   - Store results in a structured datastore.

2. **Keyword Extraction**:
   - Analyze job descriptions using an AI model (LLM).
   - Identify the top 10 most important keywords or phrases relevant to the position.
   - Focus on keywords for ATS optimization.

3. **Resume Customization**:
   - Take a base resume (in `.docx` or `.pdf`) and optional context documents.
   - Update the resume with extracted keywords while ensuring it remains truthful to the candidate's experience.
   - Rewrite content to better align with job requirements without fabricating information.

4. **Datastore Management**:
   - Store all processed data (job details, keywords, and customized resumes) in a queryable database.
   - Allow retrieval and organization of stored job applications.

5. **Output Files**:
   - Save customized resumes in `.docx` and `.pdf` formats.
   - Log changes made to the resume and output a change report in JSON format.

---

#### **Non-Functional Requirements**
1. **Modularity**:
   - Each functionality (search, keyword extraction, resume customization, datastore) is implemented as a separate module for ease of maintenance and scalability.

2. **Flexibility**:
   - Support multiple AI models (e.g., OpenAI, Ollama, Perplexity).
   - Support various search APIs (e.g., Bing, Google, Serper).

3. **User-Friendly**:
   - Maintain clean and readable code with proper error handling and logging.
   - Create outputs in standardized formats for easy use.

4. **Storage**:
   - Use an SQLite database for storing job and resume data.
   - Ensure the datastore is easily queryable.

5. **Extensibility**:
   - Allow the integration of new AI models or APIs with minimal changes.

6. **Security**:
   - Ensure API keys are handled securely and comply with terms of service.

7. **Portability**:
   - Run seamlessly on any system with Python installed (focused on macOS for development).

This project combines automation, AI-driven analysis, and clean data organization to create a powerful tool for job seekers.