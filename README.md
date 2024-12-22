# 2024 Job Search - Resume Customizer

This project helps you customize your resume to better match job descriptions using AI. It extracts key information from job postings, analyzes your base resume and additional context, and suggests improvements to tailor your resume for specific applications. It also tracks your job applications and provides some basic statistics.

## Overview

The Resume Customizer application allows you to:

1. **Input a job description** either by providing a URL or pasting the text directly.
2. **Extract key information** like company name, position title, and important ATS (Applicant Tracking System) keywords.
3. **Customize your resume** based on the job description and extracted keywords, leveraging AI to suggest improvements.
4. **Analyze the changes** made to your resume, with explanations of the impact of each change.
5. **Save the customized resume** as both a Markdown (.md) and a Word document (.docx).
6. **Track your job applications** in a local database, including the date, company, position, input method, generated resume, and analysis of changes.
7. **View application statistics**, such as the total number of applications, daily/weekly/monthly counts, and top companies applied to.
8. **Manage your base resume and context files**, allowing you to easily switch between different versions or upload new ones.

## Prerequisites

*   Python 3.11+
*   `uv` package manager
*   Git

## Installation and Setup

1. **Download the Repository:**

    First, clone the repository to your local machine using Git:

    ```bash
    git clone https://github.com/mruckman1/2024_JobSearch.git
    ```

    This will create a new directory named `2024_JobSearch` containing the project files.

2. **Install `uv`:**

    ```bash
    # On macOS and Linux.
    curl -LsSf https://astral.sh/uv/install.sh | sh
    # On Windows.
    powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
    ```

    Alternatively, you can install `uv` from PyPI using `pip` or `pipx`:

    ```bash
    pip install uv
    # Or
    pipx install uv
    ```

    If you installed `uv` using the standalone installer, you can update it to the latest version using:

    ```bash
    uv self update
    ```

3. **Create and activate a virtual environment:**

    Navigate to the `resume-customizer` directory within the cloned repository:

    ```bash
    cd 2024_JobSearch/resume-customizer
    ```

    Create a virtual environment using `uv`:

    ```bash
    uv venv
    ```

    Activate the environment:

    ```bash
    # On macOS/Linux
    source .venv/bin/activate

    # On Windows
    .venv\Scripts\activate
    ```

4. **Install dependencies:**

    ```bash
    uv pip install -r requirements.txt
    ```

    (Assuming you have a `requirements.txt` file in the `resume-customizer` directory. If not, you'll need to create one with the necessary packages: `streamlit`, `openai`, `python-docx`, `beautifulsoup4`, `requests`, `markdown`, etc.)

## Getting an OpenAI API Key

1. Go to the [OpenAI website](https://openai.com/).
2. Sign up or log in to your account.
3. Navigate to the API section.
4. Create a new project.
5. Go to the "API Keys" page within your project.
6. Click "Create new secret key".
7. Give your key a name (e.g., "ResumeCustomizer").
8. **Important:** Copy the generated API key and store it securely. You won't be able to see it again.

## Adding API Keys

### .env file

1. Create a `.env` file in the root of your project directory (`2024_JobSearch`).
2. Add your OpenAI API key to the `.env` file:

    ```
    OPENAI_API_KEY=your_openai_api_key_here
    ```

### config.toml

1. Create a `config.toml` file inside the `.streamlit` directory within `resume-customizer`.
2. Add the following content to `config.toml`, replacing `your_openai_api_key_here` with your actual API key:

    ```toml
    [openai]
    api_key = "your_openai_api_key_here"
    ```

### secrets.toml

1. Create a `secrets.toml` file inside the `.streamlit` directory within `resume-customizer`.
2. Add the following content to `secrets.toml`, replacing `your_openai_api_key_here` with your actual API key:

    ```toml
    [openai]
    api_key = "your_openai_api_key_here"
    ```

## Running the Application

1. Make sure you are in the `resume-customizer` directory and your virtual environment is activated.
2. Run the Streamlit application:

    ```bash
    streamlit run main.py
    ```

    This will open the application in your default web browser.

## Application Walkthrough

1. **File Selection (Sidebar):**

    *   Choose your base resume and context files from the dropdown menus. These files should be located in the `Resume_Context/Resume` and `Resume_Context/Context` folders, respectively.
    *   Upload new resume or context files using the "Upload New Files" section.

2. **Application Tracking (Sidebar):**

    *   View your job application statistics: total applications, daily, weekly, and monthly counts.
    *   See a list of your recent applications. You can load a previous application to review the generated resume and changes.

3. **Job Description Input:**

    *   Select your input method: "URL" or "Text".
    *   If you choose "URL", paste the job posting URL into the text box and press Enter.
    *   If you choose "Text", paste the job description into the text area.
    *   Click the "Process Job Description" button.

4. **Processing and Results:**

    *   The application will extract the company name, position title, and ATS keywords.
    *   It will then customize your resume based on the job description and keywords.
    *   The "Changes Made" section will display a detailed analysis of the modifications made to your resume.
    *   The "Customized Resume" section will show the updated resume. You can edit it directly in the text area.

5. **Saving and Downloading:**

    *   Click the "Save Resume" button to save the customized resume as both a Markdown file (.md) and a Word document (.docx) in the `outputs` folder.
    *   Click the "Download Resume (DOCX)" or "Download Resume (MD)" buttons to download the respective file types.

6. **Starting a New Application:**

    *   Click the "Clear and Start New" button to clear the current job description and generated resume, allowing you to start fresh with a new application.

## Notes

*   The application uses the `gpt-4o-2024-11-20` model for most tasks and `gpt-4o-mini` for analyzing changes. You can adjust these in the `main.py` file if needed.
*   Error handling and fallback mechanisms are in place to ensure the application continues to function even if certain API calls or parsing operations fail.
*   The application log (`resume_customizer.log`) provides detailed information about the processing steps and any errors encountered.
*   The database (`job_applications.db`) is stored in the `data` directory.

This README provides a thorough guide to setting up and using the Resume Customizer application. Remember to replace placeholder API keys with your actual key and adjust paths as necessary based on your specific setup.
