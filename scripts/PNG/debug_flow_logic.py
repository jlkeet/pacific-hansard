#!/usr/bin/env python3
"""
Debug the exact flow logic around question titles
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

def is_heading(element):
    """Check if element is a heading (PNG-specific patterns)"""
    if element.name not in ['p', 'h2', 'h3']:
        return False

    style = element.get('style', '')
    text = get_inner_text(element).strip()

    # PNG-specific heading patterns
    png_heading_patterns = [
        r'^QUESTIONS\s*$',
        r'^PERSONAL EXPLANATION\s*$', 
        r'^MOTION BY LEAVE\s*$',
        r'^SUSPENSION OF STANDING ORDERS\s*$',
        r'^ADJOURNMENT\s*$',
        r'^CONSTITUTIONAL.*BILL\s+\d{4}\s*$',
        r'^ORGANIC LAW.*BILL\s+\d{4}\s*$',
        r'^MINISTERIAL STATEMENT\s*$',
        r'^TREATY DOCUMENT\s*$',
        r'^First Reading\s*$',
        r'^Second Reading\s*$',
        r'^Third Reading\s*$',
    ]
    
    # Check PNG-specific patterns
    for pattern in png_heading_patterns:
        if re.match(pattern, text, re.IGNORECASE):
            return True

    # Check for center alignment
    if 'text-align: center' in style:
        return True

    # Check for all-caps headings (PNG style)
    if text.isupper() and len(text) > 3 and not text.startswith('Page'):
        return True

    # Exclude speaker names
    speaker_pattern = r'^(?:The Acting Speaker|Speaker|Mr|Mrs|Ms|Dr|Hon\.?)\\s+'
    if re.match(speaker_pattern, text):
        return False

    return False

def is_uppercase_heading(element):
    """Check if element is uppercase heading"""
    text = get_inner_text(element)
    # Remove non-alphabetic characters
    letters_only = re.sub(r'[^A-Za-z]+', '', text)
    is_upper = letters_only.isupper() and len(letters_only) > 0
    return is_upper

def is_question_heading(element):
    """Check if element is a question heading (PNG-specific patterns)"""
    if element.name not in ['p', 'h2', 'h3']:
        return False

    text = get_inner_text(element).strip()
    style = element.get('style', '')

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
            return True

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

# Simulate the exact logic around QUESTIONS section
in_questions_section = False
questions_index = -1

for i, element in enumerate(all_elements):
    text = get_inner_text(element).strip()
    
    if text.upper() == "QUESTIONS":
        in_questions_section = True
        questions_index = i
        print(f"Found QUESTIONS at index {i}, entered questions section")
        continue
    
    if in_questions_section and i < questions_index + 20:  # Check next 20 elements
        print(f"\n[{i}] Processing in questions section: '{text[:50]}...'")
        
        is_heading_result = is_heading(element)
        print(f"    is_heading: {is_heading_result}")
        
        if is_heading_result:
            is_uppercase_result = is_uppercase_heading(element)
            print(f"    is_uppercase_heading: {is_uppercase_result}")
            
            if is_uppercase_result:
                print(f"    → Would exit questions section (uppercase heading)")
            else:
                is_question_result = is_question_heading(element)
                print(f"    is_question_heading: {is_question_result}")
                if is_question_result:
                    print(f"    → Would start new question: '{text}'")
                else:
                    print(f"    → Would add to current question (non-question heading)")
        else:
            print(f"    → Would add to current question (non-heading)")