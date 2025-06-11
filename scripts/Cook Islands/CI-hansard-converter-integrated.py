import re
import os
from bs4 import BeautifulSoup
import logging
from datetime import datetime
import json

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Configuration
COLLECTIONS_BASE = "/Users/jacksonkeet/Pacific Hansard Development/collections/Cook Islands"

def normalize_name(name):
    """Remove all spaces and convert to uppercase for comparison"""
    return ''.join(name.split()).upper()

def extract_and_clean_speakers(text):
    """Extract all unique speakers from the text with comprehensive pattern matching"""
    speakers = []
    seen = set()
    
    # Comprehensive patterns to capture all speaker formats
    patterns = [
        # HON. followed by name with optional titles
        r'HON\.\s+((?:SIR|PROFESSOR|DR\.|MR\.|MRS\.|MS\.)?\s*[A-Z][A-Z.\s\'-]+(?:\s[A-Z][a-z]+)*):',
        # MR/MRS/MS/DR followed by name with colon
        r'(MR|MRS|MS|DR)\.?\s+([A-Z]\.?\s*[A-Z][A-Z.\s\'-]+):',
        # MR/MRS/MS SPEAKER or other titles
        r'(MR|MRS|MS|DR)\s+SPEAKER:',
        # CLERK or other official positions
        r'(CLERK(?:\s+ASSISTANT)?|SERGEANT-AT-ARMS|DEPUTY\s+SPEAKER):',
        # Generic pattern for NAME: format (must be at start of line or after punctuation)
        r'(?:^|\.\s+|\?\s+|\!\s+)([A-Z][A-Z.\s\'-]+(?:\s[A-Z][a-z]+)*):',
        # Special pattern for compound names like T. PUPUKE BROWNE
        r'(HON\.|MR\.|MRS\.|MS\.|DR\.)?\s*([A-Z]\.\s+[A-Z][A-Z\s\'-]+):',
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, text, re.MULTILINE)
        for match in matches:
            if isinstance(match, tuple):
                # Handle patterns that capture multiple groups
                parts = [part for part in match if part and part not in ['MR', 'MRS', 'MS', 'DR', 'HON.', '']]
                name = ' '.join(parts)
            else:
                name = match
            
            # Clean up the name
            name = name.strip().rstrip(':').rstrip('.').strip()
            
            # Handle special cases
            if name == "SPEAKER":
                name = "MR SPEAKER"
            elif name.startswith("CLERK"):
                name = "CLERK"
            
            normalized_name = normalize_name(name)
            
            # Filter out noise
            if (normalized_name and 
                normalized_name not in seen and 
                len(normalized_name) > 2 and
                not normalized_name.isdigit() and
                not all(c in '.,!?;:' for c in normalized_name)):
                seen.add(normalized_name)
                speakers.append(name)
    
    # Sort speakers for consistency
    speakers.sort()
    return speakers

def write_speakers_metadata(file_path, speakers):
    """Write speaker metadata to appropriate file"""
    with open(file_path, 'w', encoding='utf-8') as f:
        # Determine file type from path
        if 'oral_question' in file_path:
            f.write(f"Oral Question Speakers:\n")
        elif 'written_question' in file_path:
            f.write(f"Written Question Speakers:\n")
        else:
            # Extract part number from filename
            match = re.search(r'part(\d+)_metadata', file_path)
            if match:
                f.write(f"Part {match.group(1)} Speakers:\n")
            else:
                f.write(f"Speakers:\n")
        
        if speakers:
            for i, speaker in enumerate(speakers, 1):
                f.write(f"Speaker {i}: {speaker}\n")
        else:
            f.write("No speakers identified\n")
        f.write("\n")

def clean_content(content):
    """Clean HTML content while preserving structure"""
    soup = BeautifulSoup(content, 'html.parser')
    
    # Remove all style attributes
    for tag in soup.find_all(style=True):
        del tag['style']
    
    # Remove all class attributes
    for tag in soup.find_all(class_=True):
        del tag['class']
    
    # Preserve line breaks
    for br in soup.find_all("br"):
        br.replace_with("\n")
    
    # Remove empty tags
    for tag in soup.find_all():
        if len(tag.get_text(strip=True)) == 0 and tag.name not in ['br', 'img']:
            tag.decompose()
    
    # Remove any remaining attributes except 'src' for images
    for tag in soup.find_all():
        if tag.name != 'img':
            tag.attrs = {}
    
    return str(soup)

def extract_date_info(filename, content_soup):
    """Extract date information from filename and content"""
    year = None
    month = None
    day = None
    
    # Try to extract from filename first
    # Pattern for modern format: DAY-40-Wed-21-May-25
    modern_pattern = r'DAY-\d+-\w+-(\d+)-(\w+)-(\d+)'
    match = re.search(modern_pattern, filename)
    if match:
        day = int(match.group(1))
        month = match.group(2)
        year = 2000 + int(match.group(3))  # Assuming 20XX
        return year, month, day
    
    # Pattern for older format: Wednesday-3-March-1999
    old_pattern = r'\w+-(\d+)-(\w+)-(\d{4})'
    match = re.search(old_pattern, filename)
    if match:
        day = int(match.group(1))
        month = match.group(2)
        year = int(match.group(3))
        return year, month, day
    
    # If not found in filename, try content
    text = content_soup.get_text()
    date_patterns = [
        r'(\w+day,?\s+\d{1,2}(?:st|nd|rd|th)?\s+([A-Z][a-z]+),?\s+(\d{4}))',
        r'([A-Z][a-z]+)\s+(\d{1,2}),?\s+(\d{4})'
    ]
    
    for pattern in date_patterns:
        match = re.search(pattern, text)
        if match:
            try:
                if len(match.groups()) == 3:
                    if match.group(1).endswith('day'):
                        # Format: Monday, 22nd March, 2021
                        day = int(re.search(r'\d+', match.group(0)).group())
                        month = match.group(2)
                        year = int(match.group(3))
                    else:
                        # Format: March 22, 2021
                        month = match.group(1)
                        day = int(match.group(2))
                        year = int(match.group(3))
                return year, month, day
            except:
                continue
    
    return None, None, None

def extract_questions(content, part_number, directory):
    """Extract oral and written questions from content"""
    soup = BeautifulSoup(content, 'html.parser')
    text = soup.get_text()
    
    questions = []
    
    # Check if this section contains questions
    is_oral_section = re.search(r'ORAL\s+QUESTIONS?|Question\s+Time', text, re.IGNORECASE)
    is_written_section = re.search(r'WRITTEN\s+QUESTIONS?', text, re.IGNORECASE)
    
    if not (is_oral_section or is_written_section):
        return []
    
    question_type = "oral" if is_oral_section else "written"
    
    # Get all elements
    all_elements = soup.find_all(['p', 'div'])
    
    # Identify question boundaries
    question_starts = []
    current_question = []
    in_question = False
    
    for i, element in enumerate(all_elements):
        elem_text = element.get_text().strip()
        
        # Check if this is a new question starting
        if re.match(r'^(MR|MRS|MS|HON|DR)\.?\s+[A-Z].*?:', elem_text):
            # Check if "question" appears in the next few lines
            context_text = ' '.join(el.get_text() for el in all_elements[i:min(i+5, len(all_elements))])
            if re.search(r'\bquestion\b|\basking\b|\bask\b', context_text, re.IGNORECASE):
                if current_question:
                    questions.append({
                        'type': question_type,
                        'content': '\n'.join(current_question),
                        'number': len(questions) + 1
                    })
                current_question = []
                in_question = True
        
        if in_question:
            current_question.append(str(element))
            
            # Check if we've reached the end of this Q&A exchange
            if i + 1 < len(all_elements):
                next_text = all_elements[i + 1].get_text().strip()
                if (re.match(r'^(MR|MRS|MS|HON|DR)\.?\s+[A-Z].*?:', next_text) and 
                    re.search(r'\bquestion\b|\basking\b', ' '.join(el.get_text() for el in all_elements[i+1:min(i+6, len(all_elements))]), re.IGNORECASE)):
                    in_question = False
    
    # Don't forget the last question
    if current_question:
        questions.append({
            'type': question_type,
            'content': '\n'.join(current_question),
            'number': len(questions) + 1
        })
    
    return questions

def write_question_file(directory, question_data):
    """Write individual question to file"""
    question_type = question_data['type']
    number = question_data['number']
    content = question_data['content']
    
    # Create flattened filename
    filename = f"part{question_data['part_number']}_{question_type}_question_{number}.html"
    file_path = os.path.join(directory, filename)
    
    cleaned_content = clean_content(content)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Hansard {question_type.capitalize()} Question {number}</title>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; padding: 20px; max-width: 800px; margin: 0 auto; }}
        h3 {{ color: #333; }}
        p {{ margin-bottom: 10px; }}
        .speaker {{ font-weight: bold; color: #0066cc; }}
        .question {{ background-color: #f0f8ff; padding: 10px; margin: 10px 0; border-left: 3px solid #0066cc; }}
        .answer {{ background-color: #f5f5f5; padding: 10px; margin: 10px 0; border-left: 3px solid #666; }}
    </style>
</head>
<body>
<h3>{question_type.capitalize()} Question {number}</h3>
{cleaned_content}
</body>
</html>
        """)
    
    # Write metadata
    speakers = extract_and_clean_speakers(content)
    metadata_path = file_path.replace('.html', '_metadata.txt')
    write_speakers_metadata(metadata_path, speakers)
    
    logging.info(f"Written {question_type} question {number} to {filename}")

def extract_metadata_from_content(soup, filename):
    """Extract metadata like date, parliament number, session from content"""
    metadata = {
        'date': None,
        'parliament': None,
        'session': None,
        'meeting': None,
        'day_of_week': None,
        'sitting_type': None
    }
    
    text = soup.get_text()
    
    # Extract parliament number
    parl_match = re.search(r'(\d+)(?:st|nd|rd|th)\s+Parliament', text, re.IGNORECASE)
    if parl_match:
        metadata['parliament'] = parl_match.group(1)
    
    # Extract session/meeting info
    session_match = re.search(r'(\d+)(?:st|nd|rd|th)\s+Session', text, re.IGNORECASE)
    if session_match:
        metadata['session'] = session_match.group(1)
        
    meeting_match = re.search(r'(\w+)\s+Meeting', text, re.IGNORECASE)
    if meeting_match:
        metadata['meeting'] = meeting_match.group(1)
    
    return metadata

def split_html(filename):
    """Main function to split HTML hansard into parts and save to collections structure"""
    with open(filename, "r", encoding='utf-8') as file:
        soup = BeautifulSoup(file, 'html.parser')
    
    # Extract date information for directory structure
    year, month, day = extract_date_info(filename, soup)
    
    if not all([year, month, day]):
        logging.error(f"Could not extract date from {filename}")
        # Create a fallback directory
        directory_name = os.path.join(COLLECTIONS_BASE, "undated", 
                                     os.path.splitext(os.path.basename(filename))[0])
    else:
        # Create proper collections directory structure
        directory_name = os.path.join(COLLECTIONS_BASE, str(year), month, str(day))
    
    # Check if already processed
    if os.path.exists(directory_name) and os.listdir(directory_name):
        logging.info(f"Directory {directory_name} already exists and contains files, skipping")
        return directory_name
    
    os.makedirs(directory_name, exist_ok=True)
    logging.info(f"Processing {filename} -> {directory_name}")
    
    # Extract metadata
    metadata = extract_metadata_from_content(soup, filename)
    if year and month and day:
        metadata['date'] = f"{year}-{month}-{day}"
    
    # Write metadata file
    with open(os.path.join(directory_name, "metadata.json"), 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2)
    
    all_divs = soup.find_all('div', style=True)
    
    # Create contents file
    contents_filename = os.path.join(directory_name, "contents.html")
    with open(contents_filename, "w", encoding='utf-8') as file:
        file.write("<h2>Contents</h2>\n<ul>")
    
    current_part = []
    part_number = 0
    contents_list = []
    current_part_title = ""
    all_questions = []
    
    # Patterns for section headers
    header_patterns = [
        lambda div: div.find('span', {'style': lambda v: v and 'Bold' in v and 'font-size:12px' in v}),
        lambda div: div.text.strip().isupper() and len(div.text.strip()) > 3,
        lambda div: re.match(r'^[A-Z\s]+$', div.text.strip()) and len(div.text.strip().split()) > 1
    ]
    
    for i, div in enumerate(all_divs):
        is_header = False
        
        # Check if this is a section header
        for pattern in header_patterns:
            if pattern(div):
                text = div.text.strip()
                # Additional validation for headers
                if (len(text) > 3 and 
                    text.isupper() and 
                    not re.match(r'^\d+$', text) and
                    not text.startswith('PAGE')):
                    is_header = True
                    break
        
        if is_header:
            # Save previous part if exists
            if current_part:
                write_part(directory_name, part_number, current_part, current_part_title)
                
                # Extract speakers from the part
                part_text = "\n".join(str(d) for d in current_part)
                speakers = extract_and_clean_speakers(part_text)
                metadata_path = os.path.join(directory_name, f"part{part_number}_metadata.txt")
                write_speakers_metadata(metadata_path, speakers)
                
                # Check for questions in this part
                questions_content = "".join(str(d) for d in current_part)
                questions = extract_questions(questions_content, part_number, directory_name)
                
                # Add part number to questions and collect them
                for q in questions:
                    q['part_number'] = part_number
                    all_questions.append(q)
            
            # Start new part
            part_number += 1
            current_part = [div]
            current_part_title = div.text.strip()
            contents_list.append(current_part_title)
            
            with open(contents_filename, "a", encoding='utf-8') as file:
                file.write(f"<li>{current_part_title}</li>\n")
        else:
            current_part.append(div)
    
    # Process the last part
    if current_part:
        write_part(directory_name, part_number, current_part, current_part_title)
        part_text = "\n".join(str(d) for d in current_part)
        speakers = extract_and_clean_speakers(part_text)
        metadata_path = os.path.join(directory_name, f"part{part_number}_metadata.txt")
        write_speakers_metadata(metadata_path, speakers)
        
        # Check for questions
        questions_content = "".join(str(d) for d in current_part)
        questions = extract_questions(questions_content, part_number, directory_name)
        for q in questions:
            q['part_number'] = part_number
            all_questions.append(q)
    
    # Write all questions as flattened files
    for question in all_questions:
        write_question_file(directory_name, question)
    
    with open(contents_filename, "a", encoding='utf-8') as file:
        file.write("</ul>")
    
    # Create validation report
    validation_report = {
        'directory': directory_name,
        'total_parts': part_number,
        'questions_extracted': len(all_questions),
        'date': metadata.get('date'),
        'parliament': metadata.get('parliament')
    }
    
    with open(os.path.join(directory_name, 'processing_report.json'), 'w', encoding='utf-8') as f:
        json.dump(validation_report, f, indent=2)
    
    logging.info(f"Completed processing {filename}: {part_number} parts, {len(all_questions)} questions")
    return directory_name

def write_part(directory, part_number, content, title):
    """Write a part to file"""
    part_filename = os.path.join(directory, f"part{part_number}.html")
    cleaned_content = clean_content("".join(str(div) for div in content))
    
    with open(part_filename, "w", encoding='utf-8') as part_file:
        part_file.write(f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; padding: 20px; max-width: 800px; margin: 0 auto; }}
        h3 {{ color: #333; }}
        p {{ margin-bottom: 15px; }}
        .speaker {{ font-weight: bold; color: #0066cc; }}
    </style>
</head>
<body>
{cleaned_content}
</body>
</html>
        """)

if __name__ == "__main__":
    # Test with a sample file
    import sys
    if len(sys.argv) > 1:
        filename = sys.argv[1]
    else:
        # Process all HTML files in html_hansards directory
        html_dir = "html_hansards"
        if os.path.exists(html_dir):
            for html_file in os.listdir(html_dir):
                if html_file.endswith('.html'):
                    try:
                        split_html(os.path.join(html_dir, html_file))
                    except Exception as e:
                        logging.error(f"Error processing {html_file}: {str(e)}")
        else:
            logging.error(f"Directory {html_dir} not found")
    
    if len(sys.argv) > 1 and os.path.exists(sys.argv[1]):
        split_html(sys.argv[1])
    else:
        logging.info("Run with: python CI-hansard-converter-integrated.py [filename.html]")