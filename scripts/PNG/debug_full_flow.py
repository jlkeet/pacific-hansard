#!/usr/bin/env python3
"""
Debug script to trace the full processing flow around QUESTIONS section
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

# Skip table of contents and find actual parliamentary proceedings
start_index = 0

# Look for indicators that we've moved past the table of contents
for i, element in enumerate(all_elements):
    text = get_inner_text(element).strip()
    
    # Look for session start indicators
    if (re.search(r'took the Chair at \\d+', text) or 
        re.search(r'PARLIAMENTARY DEBATES', text) or
        re.search(r'The Acting Speaker.*took the Chair', text) or
        (text.startswith('Page ') and any(digit in text for digit in '456789'))):  # Skip early pages
        start_index = i
        print(f"Found start of actual proceedings at index {i}: {text[:60]}...")
        break

if start_index > 0:
    print(f"Skipping table of contents, starting from index {start_index}")
    all_elements = all_elements[start_index:]
else:
    print("Could not identify table of contents boundary, processing all content")

# Simulate the main processing loop around QUESTIONS
questions_found = False
questions_index = -1

for i, element in enumerate(all_elements):
    text = get_inner_text(element).strip()
    
    if text.upper() == "QUESTIONS":
        questions_found = True
        questions_index = i
        print(f"\n=== FOUND QUESTIONS at index {i} ===")
        print(f"Element: {element}")
        print(f"is_heading result: {is_heading(element)}")
        print(f"is_uppercase_heading result: {is_uppercase_heading(element)}")
        
        # Show context
        print(f"\nContext around QUESTIONS:")
        for j in range(max(0, i-2), min(len(all_elements), i+10)):
            context_text = get_inner_text(all_elements[j]).strip()
            marker = " >>> " if j == i else "     "
            print(f"{marker}[{j}] {context_text[:80]}")
        
        break

if not questions_found:
    print("QUESTIONS section not found in processed elements!")
else:
    print(f"\nQUESTIONS found at index {questions_index}")
    print("Next step: Check what happens in processing loop...")