#!/usr/bin/env python3
"""Debug script to understand the PNG parser flow"""

import re
import os
from bs4 import BeautifulSoup
import logging

logging.basicConfig(level=logging.INFO)

def preprocess_png_html(soup):
    """Copy of preprocessing function for debugging"""
    content_div = soup.find('div', class_='content')
    if not content_div:
        return soup
    
    html_content = str(content_div)
    lines = re.split(r'<br[^>]*>', html_content)
    
    paragraphs = []
    for line in lines:
        clean_line = BeautifulSoup(line, 'html.parser').get_text().strip()
        if (clean_line and 
            not clean_line.startswith('<div') and 
            not clean_line.endswith('</div>') and
            not clean_line.startswith('class=') and
            len(clean_line) > 2):
            paragraphs.append(clean_line)
    
    content_div.clear()
    for para_text in paragraphs:
        if para_text:
            p_tag = soup.new_tag('p')
            p_tag.string = para_text
            content_div.append(p_tag)
    
    print(f"Preprocessed HTML: created {len(paragraphs)} paragraphs from original content")
    return soup

def extract_date_from_content(soup):
    """Copy of date extraction for debugging"""
    date_texts = []
    date_elements = []
    date_pattern = re.compile(r'\b\d{1,2}\s+\w+\s+\d{4}\b')
    for p in soup.find_all('p', style=True):
        style = p.get('style', '')
        if 'text-align: center' in style:
            text = p.get_text(separator=' ', strip=True)
            if date_pattern.search(text):
                import dateparser
                date_obj = dateparser.parse(text)
                if date_obj:
                    date_str = date_obj.strftime('%Y-%m-%d')
                    date_texts.append(date_str)
                    date_elements.append(p)
    if date_texts:
        return date_texts[0], date_elements
    else:
        return "Unknown-Date", []

# Load and process the HTML
with open('H-11-20230315-M06-D02.html', 'r') as f:
    soup = BeautifulSoup(f, 'html.parser')

print("=== BEFORE PREPROCESSING ===")
all_elements_before = soup.find_all(['p', 'h2', 'h3'])
print(f"Elements before preprocessing: {len(all_elements_before)}")

# Preprocess
soup = preprocess_png_html(soup)

print("\n=== AFTER PREPROCESSING ===")
date_str, date_elements = extract_date_from_content(soup)
print(f"Extracted date: {date_str}")

all_elements = soup.find_all(['p', 'h2', 'h3'])
print(f"Total elements found: {len(all_elements)}")

# Find date indices
date_indices = []
for date_el in date_elements:
    try:
        index = all_elements.index(date_el)
        date_indices.append(index)
    except ValueError:
        continue

print(f"Date indices: {date_indices}")

if len(date_indices) >= 2:
    start_index = date_indices[1] + 1
    print(f"Starting parsing from index {start_index} after the second date occurrence.")
    all_elements = all_elements[start_index:]
else:
    print("Less than two date occurrences found. Starting from the beginning.")
    all_elements = all_elements[date_indices[0]:] if date_indices else all_elements

print(f"Elements after date filtering: {len(all_elements)}")

# Check content around Page 5
for i, el in enumerate(all_elements[:100]):
    text = el.get_text().strip()
    if 'Page 5:' in text:
        print(f"\nPage 5 found at element {i}: {text}")
        print("Context:")
        for j in range(max(0, i-2), min(len(all_elements), i+5)):
            print(f"  {j}: {all_elements[j].get_text().strip()[:80]}...")
        break
else:
    print("\nPage 5 NOT FOUND in remaining elements!")

# Check for Patrick Basa
for i, el in enumerate(all_elements[:100]):
    text = el.get_text().strip()
    if 'PATRICK BASA' in text:
        print(f"\nPatrick Basa found at element {i}: {text}")
        break
else:
    print("\nPatrick Basa NOT FOUND in remaining elements!")