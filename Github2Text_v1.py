import os
from github import Github
import base64
import mimetypes
from datetime import datetime

# Define patterns to exclude from processing
EXCLUDE_PATTERNS = {
    "ISSUE_TEMPLATE",
    "PULL_REQUEST_TEMPLATE",
    "CONTRIBUTING.md",
    "CODE_OF_CONDUCT.md",
    ".github",
    "docs",
    "LICENSE",
    "README.md",
    "CHANGELOG.md",
    "templates",
    "example",
    "examples",
    "test",
    "tests",
    "demo",
    "demos",
    "Makefile",
    "Dockerfile",
    "requirements.txt",
    "Pipfile",
    "Pipfile.lock",
    "package.json",
    "package-lock.json",
    "yarn.lock",
    ".env",
    ".gitignore",
    "dist",
    "build",
    "out",
    "node_modules",
    "ci",
    ".circleci",
    ".travis.yml",
    ".vscode",
    ".idea",
    "logs"
}

def is_excluded(name):
    """
    Check if the given file or directory name matches any of the exclude patterns.
    """
    name_lower = name.lower()
    for pattern in EXCLUDE_PATTERNS:
        pattern_lower = pattern.lower()
        if name_lower == pattern_lower or pattern_lower in name_lower:
            return True
    return False

def is_binary_string(bytes_data):
    """
    Determine if the given bytes data is binary.
    """
    # Define a set of text characters
    text_characters = bytearray({7, 8, 9, 10, 12, 13, 27} | set(range(0x20, 0x100)) - {0x7f})
    
    if not bytes_data:
        return False  # Empty files are considered text
    
    if b'\0' in bytes_data:
        return True  # Files containing null bytes are binary
    
    # Filter out all text characters
    nontext = bytes([b for b in bytes_data if b not in text_characters])
    
    return bool(nontext)  # If there are any non-text characters, it's binary

def process_file_content(repo, file_content, path):
    """
    Process the content of a single file.
    """
    decoded_content = base64.b64decode(file_content.content)
    if is_binary_string(decoded_content):
        return ""  # Skip binary files
    try:
        decoded_content = decoded_content.decode('utf-8', errors='ignore')
    except UnicodeDecodeError:
        return ""  # Skip files that can't be decoded
    file_text = f"\n## {path}\n\n```\n{decoded_content}\n```\n"
    return file_text

def process_repo_contents(repo, contents, base_path="", indent_level=0):
    """
    Recursively process repository contents to build repository structure and content.
    """
    repo_text = ""
    structure_text = ""
    indent = "│   " * indent_level
    for i, content_file in enumerate(contents):
        # Skip excluded files and directories
        if is_excluded(content_file.name):
            continue

        connector = "└── " if i == len(contents) - 1 else "├── "
        full_path = os.path.join(base_path, content_file.name)
        
        if content_file.type == "dir":
            structure_text += f"{indent}{connector}{content_file.name}/\n"
            try:
                sub_contents = repo.get_contents(content_file.path)
            except Exception as e:
                print(f"Failed to get contents of directory {content_file.path}: {e}")
                continue
            dir_text, dir_structure = process_repo_contents(repo, sub_contents, full_path, indent_level + 1)
            repo_text += dir_text
            structure_text += dir_structure
        else:
            structure_text += f"{indent}{connector}{content_file.name}\n"
            mime_type, _ = mimetypes.guess_type(content_file.path)
            if mime_type and mime_type.startswith("text"):
                repo_text += process_file_content(repo, content_file, full_path)
            else:
                try:
                    file_content = repo.get_contents(content_file.path)
                    decoded_content = base64.b64decode(file_content.content)
                    if not is_binary_string(decoded_content):
                        repo_text += process_file_content(repo, file_content, full_path)
                except Exception as e:
                    print(f"Failed to process file {content_file.path}: {e}")
                    continue
    return repo_text, structure_text

def repo_to_text(github_url, output_dir):
    """
    Convert a GitHub repository to a structured text file.
    """
    token = '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'  # Replace with your GitHub token
    repo_name = github_url.replace("https://github.com/", "").split('/tree/')[0]
    g = Github(token)
    try:
        repo = g.get_repo(repo_name)
    except Exception as e:
        print(f"Failed to access repository {repo_name}: {e}")
        return
    
    try:
        contents = repo.get_contents("")
    except Exception as e:
        print(f"Failed to get contents of repository {repo_name}: {e}")
        return

    timestamp = datetime.utcnow().strftime('%Y-%m-%d_%H-%M-%S')
    safe_repo_name = repo_name.replace('/', '_')
    output_file = os.path.join(output_dir, f"{safe_repo_name}_{timestamp}.txt")

    repo_text = f"# Repository: {repo_name}\n"
    contents_text, structure_text = process_repo_contents(repo, contents)
    repo_text += f"\n## Repository Structure\n\n```\n{structure_text}\n```\n"
    repo_text += contents_text

    try:
        with open(output_file, "w", encoding='utf-8') as f:
            f.write(repo_text)
        print(f"Repository contents have been written to {output_file}")
    except Exception as e:
        print(f"Failed to write to file {output_file}: {e}")

# Example usage
if __name__ == "__main__":
    github_url = "https://github.com/mberman84/edu-crew"  # Replace with the target GitHub repo URL
    output_dir = "/Users/mruckman1/Desktop/JobSearchResumeOptimizer1/Github"  # Directory where the output file will be saved
    repo_to_text(github_url, output_dir)
