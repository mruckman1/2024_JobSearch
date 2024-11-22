# /Users/mruckman1/Desktop/JobSearchResumeOptimizer1/resume-customizer/markdown_docx_converter.py
from docx import Document
from docx.shared import Pt, Inches
import markdown
import html
import re

def convert_to_docx(markdown_text):
    # Create a new Document
    doc = Document()
    
    # Set margins
    sections = doc.sections
    for section in sections:
        section.top_margin = Inches(1)
        section.bottom_margin = Inches(1)
        section.left_margin = Inches(1)
        section.right_margin = Inches(1)

    # Clean up ampersands and other special characters before conversion
    cleaned_text = html.unescape(markdown_text)
    
    # Convert Markdown to HTML
    html_text = markdown.markdown(cleaned_text)
    
    # Clean up any remaining HTML entities
    html_text = html.unescape(html_text)
    
    # Split content by sections (headers)
    sections = re.split(r'(<h[1-3]>.*?</h[1-3]>)', html_text)
    
    current_level = 0
    for section in sections:
        if section.strip():
            # Handle headers
            if section.startswith('<h1>'):
                text = re.sub('<[^<]+?>', '', section)
                doc.add_heading(text, level=1)
            elif section.startswith('<h2>'):
                text = re.sub('<[^<]+?>', '', section)
                doc.add_heading(text, level=2)
            elif section.startswith('<h3>'):
                text = re.sub('<[^<]+?>', '', section)
                heading_text = html.unescape(text)  # Additional unescape for headers
                
                # Split and handle job entry headers specially
                if '|' in heading_text:
                    parts = [part.strip() for part in heading_text.split('|')]
                    heading_text = ' | '.join(parts)
                
                doc.add_heading(heading_text, level=3)
            else:
                # Handle regular paragraphs and lists
                para = doc.add_paragraph()
                
                # Convert HTML lists to plain text bullets
                text = re.sub(r'<ul>|</ul>|<li>|</li>', '', section)
                text = re.sub(r'<p>|</p>', '', text)
                text = re.sub(r'<[^<]+?>', '', text)  # Remove any other HTML tags
                
                # Final cleanup of any remaining HTML entities
                text = html.unescape(text)
                
                # Handle bullet points
                if text.strip().startswith('•'):
                    para.style = 'List Bullet'
                    text = text.replace('•', '').strip()
                elif text.strip().startswith('-'):
                    para.style = 'List Bullet'
                    text = text.replace('-', '').strip()
                
                para.text = text.strip()
                
                # Set font
                for run in para.runs:
                    run.font.size = Pt(11)
                    run.font.name = 'Calibri'

    return doc