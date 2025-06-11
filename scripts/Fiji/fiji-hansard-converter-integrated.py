#!/usr/bin/env python3
"""
Fiji Hansard Converter - Integrated Version
Converts Fiji Parliament hansards and outputs directly to collections structure
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
        # HON. with optional titles
        r'HON\.\s+((?:PROFESSOR|DR\.|MR\.|MRS\.|MS\.)?\s*[A-Z][A-Z.\s\'-]+(?:\s[A-Z][a-z]+)*):',
        # MR/MRS/MS/DR SPEAKER
        r'(MR|MRS|MS|DR)\s+SPEAKER:',
        # Just titles with names
        r'(MR|MRS|MS|DR)\.?\s+([A-Z]\.?\s*[A-Z][A-Z.\s\'-]+):',
        # DEPUTY SPEAKER
        r'(DEPUTY SPEAKER):',
        # SECRETARY-GENERAL
        r'(SECRETARY-GENERAL):'
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            if isinstance(match, tuple):
                name = ' '.join(match).strip()
            else:
                name = match.strip()
            
            name = name.rstrip('.').rstrip(':')
            normalized_name = normalize_name(name)
            
            if normalized_name and normalized_name not in seen:
                seen.add(normalized_name)
                speakers.append(name)
    
    return speakers if speakers else ["No speakers identified"]

def extract_date_from_filename(filename):
    """Extract date from Fiji hansard filename"""
    # Pattern: Daily-Hansard-{Day}-{Date}-{Month}-{Year}
    patterns = [
        r'(\w+)-(\d+)\w*-(\w+)-(\d{4})',  # Standard pattern
        r'DH-\w+-(\d+)\w*-(\w+)-(\d{4})',  # DH- pattern
        r'(\d+)\w*-(\w+)-(\d{4})'  # Just date pattern
    ]
    
    for pattern in patterns:
        match = re.search(pattern, filename)
        if match:
            groups = match.groups()
            if len(groups) == 4:
                day_num = groups[1]
                month = groups[2]
                year = groups[3]
            else:
                day_num = groups[0]
                month = groups[1]
                year = groups[2]
            
            try:
                month_num = datetime.strptime(month, '%B').month
                date = datetime(int(year), month_num, int(day_num))
                return date
            except:
                continue
    
    return None

def clean_content(content):
    """Clean HTML content"""
    soup = BeautifulSoup(content, 'html.parser')
    
    # Remove all style attributes
    for tag in soup.find_all(style=True):
        del tag['style']
    
    # Remove all class attributes
    for tag in soup.find_all(class_=True):
        del tag['class']
    
    # Convert div tags to p tags
    for div in soup.find_all('div'):
        div.name = 'p'
    
    # Preserve line breaks
    for br in soup.find_all("br"):
        br.replace_with("\n")
    
    # Remove empty paragraphs
    for p in soup.find_all('p'):
        if len(p.get_text(strip=True)) == 0:
            p.decompose()
    
    return str(soup)

def detect_questions(text):
    """Detect if content contains questions"""
    question_patterns = [
        r'Question\s+No\.\s*\d+',
        r'Oral\s+Questions?',
        r'Written\s+Questions?',
        r'QUESTIONS\s+AND\s+ANSWERS',
        r'\(Question\s+No\.\s*\d+\)'
    ]
    
    for pattern in question_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return True
    return False

def split_questions(content):
    """Split content into individual questions"""
    soup = BeautifulSoup(content, 'html.parser')
    questions = []
    current_question = []
    question_num = 0
    
    for element in soup.find_all(['h3', 'p']):
        text = element.get_text()
        
        # Check if this starts a new question
        if re.search(r'Question\s+No\.\s*\d+', text, re.IGNORECASE) or \
           re.search(r'\(Question\s+No\.\s*\d+\)', text, re.IGNORECASE):
            if current_question:
                questions.append({
                    'number': question_num,
                    'content': '\n'.join(current_question),
                    'type': 'oral' if 'oral' in ' '.join(current_question).lower() else 'written'
                })
            question_num += 1
            current_question = [str(element)]
        else:
            current_question.append(str(element))
    
    # Don't forget the last question
    if current_question:
        questions.append({
            'number': question_num,
            'content': '\n'.join(current_question),
            'type': 'oral' if 'oral' in ' '.join(current_question).lower() else 'written'
        })
    
    return questions

def process_hansard(input_file, output_base_dir=None):
    """Process a single hansard file"""
    logging.info(f"Processing {input_file}")
    
    # Extract date from filename
    date_obj = extract_date_from_filename(os.path.basename(input_file))
    if not date_obj:
        logging.error(f"Could not extract date from {input_file}")
        return False
    
    # Create output directory structure
    year = date_obj.strftime('%Y')
    month = date_obj.strftime('%B')
    day = date_obj.strftime('%d').lstrip('0')
    
    if output_base_dir:
        output_dir = os.path.join(output_base_dir, year, month, day)
    else:
        output_dir = os.path.join(COLLECTIONS_BASE, year, month, day)
    
    os.makedirs(output_dir, exist_ok=True)
    
    # Read the input file
    with open(input_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    soup = BeautifulSoup(content, 'html.parser')
    all_divs = soup.find_all('div')
    
    # Create contents file
    contents_parts = []
    part_number = 0
    
    # Process the content
    current_part = []
    current_title = ""
    in_questions = False
    
    for div in all_divs:
        text = div.get_text(strip=True)
        
        # Check for section headers (usually in uppercase)
        span = div.find('span', {'style': lambda value: value and 'Bold' in value})
        
        if span and span.text.strip().isupper() and len(span.text.strip()) > 3:
            # Save previous part
            if current_part:
                if in_questions:
                    # Process questions
                    questions = split_questions('\n'.join(current_part))
                    for i, q in enumerate(questions):
                        q_filename = f"{q['type']}_question_{i+1}.html"
                        q_filepath = os.path.join(output_dir, q_filename)
                        
                        # Extract speakers from question
                        speakers = extract_and_clean_speakers(q['content'])
                        
                        # Write question file
                        with open(q_filepath, 'w', encoding='utf-8') as f:
                            date_str = date_obj.strftime('%Y-%m-%d')
                            q_type = q['type'].capitalize()
                            f.write(f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Fiji Hansard {q_type} Question {i+1} - {date_str}</title>
</head>
<body>
{clean_content(q['content'])}
</body>
</html>""")
                        
                        # Write metadata
                        metadata_path = q_filepath.replace('.html', '_metadata.txt')
                        with open(metadata_path, 'w', encoding='utf-8') as f:
                            q_type = q['type'].capitalize()
                            f.write(f"{q_type} Question {i+1} Speakers:\n")
                            for j, speaker in enumerate(speakers):
                                f.write(f"Speaker {j+1}: {speaker}\n")
                        
                        q_type = q['type'].capitalize()
                        contents_parts.append(f"{q_type} Question {i+1}")
                else:
                    # Regular part
                    part_filename = f"part{part_number}.html"
                    part_filepath = os.path.join(output_dir, part_filename)
                    
                    # Extract speakers
                    speakers = extract_and_clean_speakers('\n'.join(current_part))
                    
                    # Write part file
                    with open(part_filepath, 'w', encoding='utf-8') as f:
                        date_str = date_obj.strftime('%Y-%m-%d')
                        content = clean_content('\n'.join(current_part))
                        html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{current_title} - Fiji Hansard {date_str}</title>
</head>
<body>
<h3>{current_title}</h3>
{content}
</body>
</html>"""
                        f.write(html_content)
                    
                    # Write metadata
                    metadata_path = part_filepath.replace('.html', '_metadata.txt')
                    with open(metadata_path, 'w', encoding='utf-8') as f:
                        f.write(f"Part {part_number} Speakers:\n")
                        for j, speaker in enumerate(speakers):
                            f.write(f"Speaker {j+1}: {speaker}\n")
                    
                    contents_parts.append(current_title)
            
            # Start new part
            part_number += 1
            current_title = span.text.strip()
            current_part = [str(div)]
            in_questions = 'QUESTION' in current_title.upper()
        else:
            current_part.append(str(div))
    
    # Don't forget the last part
    if current_part:
        if in_questions:
            questions = split_questions('\n'.join(current_part))
            for i, q in enumerate(questions):
                q_filename = f"{q['type']}_question_{i+1}.html"
                q_filepath = os.path.join(output_dir, q_filename)
                
                speakers = extract_and_clean_speakers(q['content'])
                
                with open(q_filepath, 'w', encoding='utf-8') as f:
                    date_str = date_obj.strftime('%Y-%m-%d')
                    q_type = q['type'].capitalize()
                    f.write(f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Fiji Hansard {q_type} Question {i+1} - {date_str}</title>
</head>
<body>
{clean_content(q['content'])}
</body>
</html>""")
                
                metadata_path = q_filepath.replace('.html', '_metadata.txt')
                with open(metadata_path, 'w', encoding='utf-8') as f:
                    f.write(f"{q['type'].capitalize()} Question {i+1} Speakers:\n")
                    for j, speaker in enumerate(speakers):
                        f.write(f"Speaker {j+1}: {speaker}\n")
                
                contents_parts.append(f"{q['type'].capitalize()} Question {i+1}")
        else:
            part_filename = f"part{part_number}.html"
            part_filepath = os.path.join(output_dir, part_filename)
            
            speakers = extract_and_clean_speakers('\n'.join(current_part))
            
            with open(part_filepath, 'w', encoding='utf-8') as f:
                date_str = date_obj.strftime('%Y-%m-%d')
                content = clean_content('\n'.join(current_part))
                f.write(f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{current_title} - Fiji Hansard {date_str}</title>
</head>
<body>
<h3>{current_title}</h3>
{content}
</body>
</html>""")
            
            metadata_path = part_filepath.replace('.html', '_metadata.txt')
            with open(metadata_path, 'w', encoding='utf-8') as f:
                f.write(f"Part {part_number} Speakers:\n")
                for j, speaker in enumerate(speakers):
                    f.write(f"Speaker {j+1}: {speaker}\n")
            
            contents_parts.append(current_title)
    
    # Write contents file
    contents_path = os.path.join(output_dir, 'contents.html')
    with open(contents_path, 'w', encoding='utf-8') as f:
        date_str = date_obj.strftime('%Y-%m-%d')
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
    logging.info(f"Created {len(contents_parts)} parts")
    
    return True

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
    import sys
    
    if len(sys.argv) > 1:
        # Process specific file
        input_file = sys.argv[1]
        process_hansard(input_file)
    else:
        # Process all files
        process_all_fiji_hansards()