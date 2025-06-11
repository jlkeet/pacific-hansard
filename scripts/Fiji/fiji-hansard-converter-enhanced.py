#!/usr/bin/env python3
"""
Fiji Hansard Converter - Enhanced with Question Extraction
Converts Fiji Parliament hansards with proper question handling
"""

import re
import os
try:
    from bs4 import BeautifulSoup
except ImportError:
    from BeautifulSoup import BeautifulSoup
from datetime import datetime
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Base collections directory
COLLECTIONS_BASE = "/Users/jacksonkeet/Pacific Hansard Development/collections/Fiji"

def normalize_name(name):
    """Remove all spaces and convert to uppercase for comparison"""
    return ''.join(name.split()).upper()

def extract_and_clean_speakers(text):
    """Extract speaker names from text"""
    speakers = []
    seen = set()
    
    # Multiple patterns to catch different speaker formats
    patterns = [
        # HON. NAME.- format (with period-dash)
        r'HON\.\s+([A-Z][A-Z.\s\'-]+(?:\s[A-Z][a-z]+)*)\.?-',
        # HON. TITLE.- format 
        r'HON\.\s+((?:PRIME MINISTER|MINISTER|LEADER|ATTORNEY-GENERAL|SPEAKER|DEPUTY SPEAKER)[A-Z\s\'-]*)\.?-',
        # MR/MRS/MS SPEAKER format
        r'(MR\.?|MRS\.?|MS\.?|MADAM)\s+SPEAKER\.?-',
        # HON. with colon (old format)
        r'HON\.\s+([A-Z][A-Z.\s\'-]+(?:\s[A-Z][a-z]+)*):',
        # MR/MRS/MS/DR SPEAKER
        r'(MR|MRS|MS|DR)\s+SPEAKER:',
        # DEPUTY SPEAKER
        r'(DEPUTY SPEAKER):',
        # SECRETARY-GENERAL
        r'(SECRETARY-GENERAL):'
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            if isinstance(match, tuple):
                name = ' '.join(m for m in match if m).strip()
            else:
                name = match.strip()
            
            name = name.rstrip('.-:').strip()
            
            # Handle special cases
            if 'SPEAKER' in name and not any(title in name for title in ['DEPUTY', 'ASSISTANT']):
                name = 'MR SPEAKER'
            elif name == 'SPEAKER':
                name = 'MR SPEAKER'
            
            normalized_name = normalize_name(name)
            
            if (normalized_name and 
                normalized_name not in seen and 
                len(normalized_name) > 2 and
                not normalized_name.isdigit()):
                seen.add(normalized_name)
                speakers.append(name)
    
    # Sort speakers for consistency
    speakers.sort()
    return speakers if speakers else ["No speakers identified"]

def extract_questions_from_content(content):
    """Extract questions from a content section"""
    questions = []
    
    # Remove HTML tags for analysis
    text = re.sub(r'<[^>]+>', ' ', content)
    lines = text.split('\n')
    
    current_section = None
    current_questions = []
    
    for line in lines:
        line = line.strip()
        
        # Check for question section headers
        if re.match(r'^Oral Questions?\s*$', line, re.IGNORECASE):
            current_section = 'oral'
            continue
        elif re.match(r'^Written Questions?\s*$', line, re.IGNORECASE):
            if current_questions and current_section == 'oral':
                # Save oral questions
                questions.extend([(q, 'oral') for q in current_questions])
                current_questions = []
            current_section = 'written'
            continue
        
        # Extract individual questions
        if current_section:
            # Pattern: (1) Question Title
            match = re.match(r'^\((\d+)\)\s*(.+)', line)
            if match:
                q_num = match.group(1)
                q_title = match.group(2).strip()
                
                # Clean up the title
                q_title = re.sub(r'\s+', ' ', q_title)
                q_title = q_title.rstrip(' -–—')
                
                if len(q_title) > 5:  # Filter out noise
                    current_questions.append({
                        'number': q_num,
                        'title': q_title,
                        'reference': None
                    })
            
            # Pattern: Q/No. XXX/YYYY
            elif 'Q/No.' in line:
                match = re.search(r'\(Q/No\.\s*(\d+/\d+)\)', line)
                if match and current_questions:
                    # Assign reference to the last question
                    current_questions[-1]['reference'] = match.group(1)
    
    # Don't forget the last section
    if current_questions and current_section:
        questions.extend([(q, current_section) for q in current_questions])
    
    return questions

def clean_content(content):
    """Clean HTML content while preserving structure"""
    soup = BeautifulSoup(content, 'html.parser')
    
    # Remove all style attributes
    for tag in soup.find_all(style=True):
        del tag['style']
    
    # Remove all class attributes
    for tag in soup.find_all(class_=True):
        del tag['class']
    
    # Remove empty paragraphs
    for p in soup.find_all('p'):
        if not p.get_text(strip=True):
            p.decompose()
    
    return str(soup)

def process_hansard(input_file):
    """Process a single hansard HTML file"""
    logging.info(f"Processing {input_file}")
    
    # Read the input file
    with open(input_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    soup = BeautifulSoup(content, 'html.parser')
    
    # Extract date from filename
    filename = os.path.basename(input_file)
    date_match = re.search(r'(\d{1,2})[a-z]{0,2}[-\s]+([A-Za-z]+)[-\s]+(\d{4})', filename)
    
    if date_match:
        day = date_match.group(1)
        month = date_match.group(2)
        year = date_match.group(3)
        
        # Convert month name to number
        month_map = {
            'january': '01', 'february': '02', 'march': '03', 'april': '04',
            'may': '05', 'june': '06', 'july': '07', 'august': '08',
            'september': '09', 'october': '10', 'november': '11', 'december': '12'
        }
        month_num = month_map.get(month.lower(), '01')
        
        # Create date object
        date_obj = datetime(int(year), int(month_num), int(day))
        date_str = date_obj.strftime('%Y-%m-%d')
        
        # Convert month to full name for directory
        month_full = date_obj.strftime('%B')
    else:
        # Fallback
        date_obj = datetime.now()
        date_str = date_obj.strftime('%Y-%m-%d')
        year = date_obj.strftime('%Y')
        month_full = date_obj.strftime('%B')
        day = date_obj.strftime('%d')
    
    # Create output directory structure
    output_dir = os.path.join(COLLECTIONS_BASE, year, month_full, str(int(day)))
    os.makedirs(output_dir, exist_ok=True)
    
    # Get all divs (content blocks)
    all_divs = soup.find_all('div')
    if not all_divs:
        all_divs = soup.find_all('p')
    
    # Create contents file
    contents_parts = []
    part_number = 0
    question_counts = {'oral': 0, 'written': 0}
    
    # Process the content
    current_part = []
    current_title = ""
    
    for div in all_divs:
        text = div.get_text(strip=True)
        
        # Check for section headers
        if text and text.isupper() and len(text) > 3 and not all(c in '0123456789.-()' for c in text):
            # Save previous part
            if current_part:
                part_content = '\n'.join(current_part)
                
                # Check if this is a questions section
                if 'QUESTION' in current_title.upper():
                    # Extract questions
                    questions = extract_questions_from_content(part_content)
                    
                    if questions:
                        # Create a questions directory
                        questions_dir = os.path.join(output_dir, f'part{part_number}_questions')
                        os.makedirs(questions_dir, exist_ok=True)
                        
                        for q_data, q_type in questions:
                            q_num = question_counts[q_type] + 1
                            question_counts[q_type] += 1
                            
                            # Create question file
                            q_filename = f"{q_type}_question_{q_num}.html"
                            q_filepath = os.path.join(questions_dir, q_filename)
                            
                            # Extract question content (for now, just the title)
                            q_content = f"""<h4>{q_data['title']}</h4>
<p><em>Question {q_data['number']}</em></p>"""
                            if q_data['reference']:
                                q_content += f"<p><em>Reference: Q/No. {q_data['reference']}</em></p>"
                            
                            with open(q_filepath, 'w', encoding='utf-8') as f:
                                f.write(f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{q_data['title']} - Fiji Hansard {date_str}</title>
</head>
<body>
<h3>{q_type.upper()} QUESTION {q_num}</h3>
{q_content}
</body>
</html>""")
                            
                            # Create metadata
                            metadata_path = q_filepath.replace('.html', '_metadata.txt')
                            with open(metadata_path, 'w', encoding='utf-8') as f:
                                f.write(f"{q_type.capitalize()} Question {q_num} Speakers:\n")
                                f.write("Speaker 1: To be extracted from full debate\n\n")
                        
                        contents_parts.append(f"{current_title} ({len(questions)} questions)")
                
                # Regular part
                part_filename = f"part{part_number}.html"
                part_filepath = os.path.join(output_dir, part_filename)
                
                # Extract speakers
                speakers = extract_and_clean_speakers(part_content)
                
                # Write part file
                with open(part_filepath, 'w', encoding='utf-8') as f:
                    content_html = clean_content(part_content)
                    f.write(f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{current_title} - Fiji Hansard {date_str}</title>
</head>
<body>
<h3>{current_title}</h3>
{content_html}
</body>
</html>""")
                
                # Write metadata
                write_speakers_metadata(output_dir, part_number, speakers)
                
                if 'QUESTION' not in current_title.upper():
                    contents_parts.append(current_title)
                
                part_number += 1
            
            # Start new part
            current_title = text
            current_part = [str(div)]
        else:
            current_part.append(str(div))
    
    # Don't forget the last part
    if current_part:
        part_content = '\n'.join(current_part)
        part_filename = f"part{part_number}.html"
        part_filepath = os.path.join(output_dir, part_filename)
        
        speakers = extract_and_clean_speakers(part_content)
        
        with open(part_filepath, 'w', encoding='utf-8') as f:
            content_html = clean_content(part_content)
            f.write(f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{current_title} - Fiji Hansard {date_str}</title>
</head>
<body>
<h3>{current_title}</h3>
{content_html}
</body>
</html>""")
        
        write_speakers_metadata(output_dir, part_number, speakers)
        contents_parts.append(current_title)
    
    # Create contents.html
    contents_path = os.path.join(output_dir, 'contents.html')
    with open(contents_path, 'w', encoding='utf-8') as f:
        f.write(f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Contents - Fiji Hansard {date_str}</title>
</head>
<body>
<h2>Contents</h2>
<ul>
""")
        for part in contents_parts:
            f.write(f"<li>{part}</li>\n")
        f.write("""</ul>
</body>
</html>""")
    
    logging.info(f"Successfully processed {input_file}")
    logging.info(f"Output directory: {output_dir}")
    logging.info(f"Created {part_number + 1} parts")
    if question_counts['oral'] > 0 or question_counts['written'] > 0:
        logging.info(f"Extracted {question_counts['oral']} oral and {question_counts['written']} written questions")
    
    return True

def write_speakers_metadata(directory, part_number, speakers):
    """Write speaker metadata to file"""
    metadata_path = os.path.join(directory, f"part{part_number}_metadata.txt")
    with open(metadata_path, 'w', encoding='utf-8') as f:
        f.write(f"Part {part_number} Speakers:\n")
        if speakers and speakers[0] != "No speakers identified":
            for i, speaker in enumerate(speakers, 1):
                f.write(f"Speaker {i}: {speaker}\n")
        else:
            f.write("Speaker 1: No speakers identified\n")
        f.write("\n")

def process_all_fiji_hansards():
    """Process all HTML hansards in the html_hansards directory"""
    html_dir = 'html_hansards'
    if not os.path.exists(html_dir):
        html_dir = '.'  # Current directory
    
    processed_count = 0
    
    for filename in os.listdir(html_dir):
        if filename.endswith('.html') and 'hansard' in filename.lower():
            filepath = os.path.join(html_dir, filename)
            if process_hansard(filepath):
                processed_count += 1
    
    logging.info(f"Processed {processed_count} Fiji hansards")
    return processed_count

if __name__ == "__main__":
    process_all_fiji_hansards()