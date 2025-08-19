#!/usr/bin/env python3
"""
Debug script to test question heading detection
"""

import re
from bs4 import BeautifulSoup

def get_inner_text(element):
    """Get inner text from element"""
    a_tag = element.find('a')
    if a_tag:
        text = a_tag.get_text(separator=' ', strip=True)
        return text
    else:
        text = element.get_text(separator=' ', strip=True)
        return text

def is_question_heading(element):
    """Check if element is a question heading (PNG-specific patterns)"""
    if element.name not in ['p', 'h2', 'h3']:
        return False

    text = get_inner_text(element).strip()
    style = element.get('style', '')

    print(f"is_question_heading: Checking element '{text}' with tag '{element.name}' and style '{style}'")

    # PNG-specific question patterns based on content analysis
    png_question_patterns = [
        r"Contracting SME's to Deliver School Supplies",
        r"Supplementary Question",
        r"Closure of companies in PNG",
        r"Power project in.*Province",
        r"Provide Financial Report",
        r"Length of Repayment Term",
        r"Promote Police Officers", 
        r"National Development Bank",
        r"Status of the Economy",
        # Generic patterns
        r".+\?\s*$",  # Ends with question mark
        r"Question\s+\d+",  # Question numbered
        r"^[A-Z][a-z].*[a-z]\s*$",  # Title case questions
    ]

    # Check PNG question patterns
    for pattern in png_question_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            print(f"is_question_heading: Text '{text}' matches PNG question pattern {pattern}, returning True")
            return True

    # Exclude purely numeric elements
    def is_purely_numeric(text):
        cleaned_text = re.sub(r'[^0-9]', '', text)
        return cleaned_text.isdigit()
        
    if is_purely_numeric(text):
        print(f"is_question_heading: Text is purely numeric: {text}")
        return False

    # Exclude speaker names
    speaker_pattern = r'^(?:The Acting Speaker|Speaker|Mr|Mrs|Ms|Dr|Hon\.?)\\s+'
    if re.match(speaker_pattern, text):
        print(f"is_question_heading: Text matches speaker pattern: {text}")
        return False

    # Exclude the 'QUESTIONS' heading itself
    if text.upper() == 'QUESTIONS':
        print("is_question_heading: Text is 'QUESTIONS', returning False")
        return False

    print("is_question_heading: None of the conditions met, returning False")
    return False

def preprocess_png_html(soup):
    """Preprocess PNG HTML to convert <br> separated content into proper paragraphs"""
    content_div = soup.find('div', class_='content')
    if not content_div:
        return soup
    
    # Get the text content and split by <br> tags
    html_content = str(content_div)
    
    # Split content by <br> variations
    lines = re.split(r'<br[^>]*>', html_content)
    
    # Clean and filter lines
    paragraphs = []
    for line in lines:
        # Remove HTML tags and clean up
        clean_line = BeautifulSoup(line, 'html.parser').get_text().strip()
        if (clean_line and 
            not clean_line.startswith('<div') and 
            not clean_line.endswith('</div>') and
            not clean_line.startswith('class=') and
            len(clean_line) > 2):  # Skip very short lines
            paragraphs.append(clean_line)
    
    # Replace content div with proper paragraph structure
    content_div.clear()
    for para_text in paragraphs:
        if para_text:
            p_tag = soup.new_tag('p')
            p_tag.string = para_text
            content_div.append(p_tag)
    
    return soup

# Load the HTML content
with open("H-11-20230315-M06-D02.html", "r", encoding='utf-8') as file:
    soup = BeautifulSoup(file, 'html.parser')

# Preprocess 
soup = preprocess_png_html(soup)

# Find all elements
all_elements = soup.find_all(['p', 'h2', 'h3'])

# Skip table of contents
start_index = 0
for i, element in enumerate(all_elements):
    text = get_inner_text(element).strip()
    
    if (re.search(r'took the Chair at \\d+', text) or 
        re.search(r'PARLIAMENTARY DEBATES', text) or
        re.search(r'The Acting Speaker.*took the Chair', text) or
        (text.startswith('Page ') and any(digit in text for digit in '456789'))):
        start_index = i
        break

if start_index > 0:
    all_elements = all_elements[start_index:]

# Find QUESTIONS section and test question heading detection
questions_found = False
questions_index = -1

for i, element in enumerate(all_elements):
    text = get_inner_text(element).strip()
    
    if text.upper() == "QUESTIONS":
        questions_found = True
        questions_index = i
        print(f"Found QUESTIONS at index {i}")
        break

if questions_found:
    print(f"\nTesting question heading detection after QUESTIONS section:")
    
    # Test elements after QUESTIONS
    for j in range(questions_index + 1, min(len(all_elements), questions_index + 20)):
        element = all_elements[j]
        text = get_inner_text(element).strip()
        
        # Test specific question titles we expect
        if any(keyword in text for keyword in ["Contracting SME", "Supplementary Question", "Closure of companies", "Power project"]):
            print(f"\n=== Testing potential question title at index {j} ===")
            print(f"Text: '{text}'")
            result = is_question_heading(element)
            print(f"is_question_heading result: {result}")
            print("---")
else:
    print("QUESTIONS section not found!")