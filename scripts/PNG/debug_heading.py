#!/usr/bin/env python3
"""
Debug script to test the is_heading function on QUESTIONS element
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

    print(f"is_heading: Checking element '{text}' with tag '{element.name}' and style '{style}'")

    # PNG-specific heading patterns
    png_heading_patterns = [
        r'^QUESTIONS\s*$',
        r'^PERSONAL EXPLANATION\s*$', 
        r'^MOTION BY LEAVE\s*$',
        r'^SUSPENSION OF STANDING ORDERS\s*$',
        r'^ADJOURNMENT\s*$',
    ]
    
    # Check PNG-specific patterns
    for pattern in png_heading_patterns:
        if re.match(pattern, text, re.IGNORECASE):
            print(f"is_heading: Text '{text}' matches PNG pattern {pattern}, returning True")
            return True

    # Check for center alignment
    if 'text-align: center' in style:
        print("is_heading: Found 'text-align: center' in style, returning True")
        return True

    # Check for all-caps headings (PNG style)
    if text.isupper() and len(text) > 3 and not text.startswith('Page'):
        print(f"is_heading: Text '{text}' is uppercase heading, returning True")
        return True

    print("is_heading: None of the conditions met, returning False")
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

# Find all elements and look for QUESTIONS
all_elements = soup.find_all(['p', 'h2', 'h3'])

# Test the QUESTIONS element specifically
for i, element in enumerate(all_elements):
    text = get_inner_text(element).strip()
    if text.upper() == "QUESTIONS":
        print(f"\n=== Testing QUESTIONS element at index {i} ===")
        result = is_heading(element)
        print(f"is_heading result: {result}")
        break