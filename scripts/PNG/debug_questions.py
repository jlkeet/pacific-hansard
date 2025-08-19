#!/usr/bin/env python3
"""
Debug script to understand why QUESTIONS section is not being detected
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
    
    print(f"Preprocessed HTML: created {len(paragraphs)} paragraphs from original content")
    return soup

# Load the HTML content
with open("H-11-20230315-M06-D02.html", "r", encoding='utf-8') as file:
    soup = BeautifulSoup(file, 'html.parser')

# Preprocess 
soup = preprocess_png_html(soup)

# Find all elements and look for QUESTIONS
all_elements = soup.find_all(['p', 'h2', 'h3'])
print(f"Total elements found: {len(all_elements)}")

# Look for QUESTIONS specifically
questions_found = False
for i, element in enumerate(all_elements):
    text = get_inner_text(element).strip()
    if text.upper() == "QUESTIONS":
        print(f"Found QUESTIONS at index {i}: '{text}'")
        print(f"Element tag: {element.name}")
        print(f"Element style: {element.get('style', '')}")
        print(f"Element attributes: {element.attrs}")
        print(f"Previous element: {get_inner_text(all_elements[i-1]).strip() if i > 0 else 'None'}")
        print(f"Next element: {get_inner_text(all_elements[i+1]).strip() if i < len(all_elements)-1 else 'None'}")
        questions_found = True
        break

if not questions_found:
    print("QUESTIONS section not found!")
    # Look for partial matches
    for i, element in enumerate(all_elements):
        text = get_inner_text(element).strip()
        if "QUESTION" in text.upper():
            print(f"Found partial match at index {i}: '{text}'")