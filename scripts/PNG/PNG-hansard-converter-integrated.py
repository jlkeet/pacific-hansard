#!/usr/bin/env python3
"""
Papua New Guinea Hansard Converter - Integrated Version
Converts PNG Parliament hansards and outputs directly to collections structure
Based on the existing PNG converter but integrated with pipeline architecture
"""

import re
import os
import sys
from bs4 import BeautifulSoup
from datetime import datetime
import logging
import json
import uuid

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Base collections directory
COLLECTIONS_BASE = "/Users/jacksonkeet/Pacific Hansard Development/collections/Papua New Guinea"

def normalize_name(name):
    """Remove all spaces and convert to uppercase for comparison"""
    return ''.join(name.split()).upper()

def extract_and_clean_speakers(text):
    """Extract speaker names from text using PNG-specific patterns"""
    speakers = []
    seen = set()
    
    # PNG-specific patterns based on actual content analysis
    patterns = [
        # PNG format after preprocessing: Mr FIRSTNAME LASTNAME (Title-Minister
        r'(Mr|Mrs|Ms|Dr|Hon\.?)\s+([A-Z][A-Z\s]+[A-Z])\s*\([^)]*(?:Minister|Speaker|Leader)[^)]*\)',
        # PNG format: Mr FIRSTNAME LASTNAME - (with dash)
        r'(Mr|Mrs|Ms|Dr|Hon\.?)\s+([A-Z][A-Z\s]+[A-Z])\s*-',
        # PNG format: The Acting Speaker (Title Name)
        r'(The Acting Speaker)\s*\([^)]+\)',
        # PNG format: Mr ACTING SPEAKER- 
        r'(Mr|Mrs|Ms|Dr)\s+(ACTING\s+SPEAKER)\s*-?',
        # PNG format: Simple Speaker.
        r'^(Speaker)\.',
        # PNG format: Mr NAME at start of paragraph
        r'^(Mr|Mrs|Ms|Dr|Hon\.?)\s+([A-Z][A-Z\.\s\'-]+)(?:\s+\([^)]+\))?\s*-',
        # Generic patterns for safety
        r'HON\.\s+((?:PROFESSOR|DR\.|MR\.|MRS\.|MS\.)?\s*[A-Z][A-Z.\s\'-]+(?:\s[A-Z][a-z]+)*):',
        # PNG format: Mr NAME ( followed by constituency or title
        r'(Mr|Mrs|Ms|Dr)\s+([A-Z][A-Z\s]+)\s*\([^)]+\)',
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, text, re.MULTILINE | re.IGNORECASE)
        for match in matches:
            if isinstance(match, tuple):
                name = ' '.join(m for m in match if m).strip()
            else:
                name = match.strip()
            
            # Clean up the name
            name = name.rstrip('.-:').rstrip('-').rstrip('–').rstrip('—').strip()
            
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

def extract_date_from_filename(filename):
    """Extract date from PNG hansard filename: H-11-20230314-M06-D01"""
    patterns = [
        r'H-\d+-(\d{4})(\d{2})(\d{2})-',  # H-11-20230314-M06-D01 format
        r'(\d{4})-(\d{2})-(\d{2})',        # YYYY-MM-DD format
        r'(\d{2})-(\w+)-(\d{4})',          # DD-Month-YYYY format
    ]
    
    for pattern in patterns:
        match = re.search(pattern, filename)
        if match:
            groups = match.groups()
            try:
                if len(groups) == 3:
                    if groups[0].isdigit() and len(groups[0]) == 4:  # Year first
                        year, month, day = groups[0], groups[1], groups[2]
                        if month.isdigit():
                            date = datetime(int(year), int(month), int(day))
                        else:
                            month_num = datetime.strptime(month, '%B').month
                            date = datetime(int(year), month_num, int(day))
                    else:  # Day first
                        day, month, year = groups[0], groups[1], groups[2]
                        if month.isdigit():
                            date = datetime(int(year), int(month), int(day))
                        else:
                            month_num = datetime.strptime(month, '%B').month
                            date = datetime(int(year), month_num, int(day))
                    return date
            except (ValueError, AttributeError):
                continue
    
    logging.warning(f"Could not extract date from filename: {filename}")
    return None

def clean_content(content):
    """Clean HTML content while preserving structure"""
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
    
    # Remove any remaining attributes except 'src' for images
    for tag in soup.find_all():
        if tag.name != 'img':
            tag.attrs = {}
    
    return str(soup)

def create_collections_directory(date):
    """Create the collections directory structure"""
    if not date:
        date = datetime.now()
    
    year = str(date.year)
    month = date.strftime('%B')
    day = str(date.day)
    
    directory = os.path.join(COLLECTIONS_BASE, year, month, day)
    os.makedirs(directory, exist_ok=True)
    
    return directory

def write_metadata_json(directory, title, date, speakers_count, parts_count):
    """Write metadata JSON file for collections"""
    metadata = {
        "id": str(uuid.uuid4()),
        "title": title,
        "date": date.strftime('%Y-%m-%d') if date else "Unknown",
        "country": "Papua New Guinea",
        "parliament": "National Parliament of Papua New Guinea",
        "document_type": "Hansard",
        "speakers_count": speakers_count,
        "parts_count": parts_count,
        "processed_date": datetime.now().isoformat(),
        "processing_status": "completed"
    }
    
    metadata_path = os.path.join(directory, "metadata.json")
    with open(metadata_path, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)
    
    return metadata

def write_part(directory, part_number, content, title=""):
    """Write a part HTML file and its metadata"""
    part_filename = os.path.join(directory, f"part{part_number}.html")
    cleaned_content = clean_content("\n".join(content))
    
    with open(part_filename, "w", encoding='utf-8') as part_file:
        part_file.write(f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PNG Hansard Part {part_number}{' - ' + title if title else ''}</title>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; padding: 20px; max-width: 800px; margin: 0 auto; }}
        h3 {{ color: #333; }}
        p {{ margin-bottom: 15px; }}
    </style>
</head>
<body>
{cleaned_content}
</body>
</html>""")
    
    # Extract speakers and write metadata
    speakers = extract_and_clean_speakers(cleaned_content)
    metadata_filename = os.path.join(directory, f"part{part_number}_metadata.txt")
    
    with open(metadata_filename, 'w', encoding='utf-8') as f:
        f.write(f"Part {part_number} Speakers:\n")
        if speakers:
            for i, speaker in enumerate(speakers, 1):
                f.write(f"Speaker {i}: {speaker}\n")
        else:
            f.write("No speakers identified\n")
        f.write("\n")
    
    return speakers

def write_question(directory, part_number, question_number, title, content):
    """Write a question HTML file and its metadata"""
    questions_dir = os.path.join(directory, f"part{part_number}_questions")
    os.makedirs(questions_dir, exist_ok=True)
    
    filename = os.path.join(questions_dir, f"oral_question_{question_number}.html")
    cleaned_content = clean_content(content)
    
    with open(filename, "w", encoding='utf-8') as file:
        file.write(f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>{title}</title>
    <style>
        body {{ font-family: Arial, sans-serif; padding: 20px; }}
        h3 {{ color: #333; }}
        p {{ margin-bottom: 10px; }}
    </style>
</head>
<body>
<h3>{title}</h3>
{cleaned_content}
</body>
</html>""")
    
    # Extract speakers and write metadata
    speakers = extract_and_clean_speakers(cleaned_content)
    metadata_filename = os.path.join(questions_dir, f"oral_question_{question_number}_metadata.txt")
    
    with open(metadata_filename, 'w', encoding='utf-8') as f:
        f.write(f"Oral Question {question_number} Speakers:\n")
        if speakers:
            for i, speaker in enumerate(speakers, 1):
                f.write(f"Speaker {i}: {speaker}\n")
        else:
            f.write("No speakers identified\n")
        f.write("\n")
    
    return speakers

def extract_date_from_content(soup):
    """Extract date from PNG hansard content (copied from original PNG converter)"""
    date_texts = []
    date_elements = []
    date_pattern = re.compile(r'\b\d{1,2}\s+\w+\s+\d{4}\b')  # e.g., '13 February 2021'
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

def get_inner_text(element):
    """Get inner text from element (copied from original PNG converter)"""
    a_tag = element.find('a')
    if a_tag:
        text = a_tag.get_text(separator=' ', strip=True)
        logging.debug(f"get_inner_text: Found <a> tag with text '{text}'")
        return text
    else:
        text = element.get_text(separator=' ', strip=True)
        logging.debug(f"get_inner_text: No <a> tag found, using element text '{text}'")
        return text

def is_heading(element):
    """Check if element is a heading (PNG-specific patterns)"""
    if element.name not in ['p', 'h2', 'h3']:
        return False

    style = element.get('style', '')
    text = get_inner_text(element).strip()

    logging.debug(f"is_heading: Checking element '{text}' with tag '{element.name}' and style '{style}'")

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
            logging.debug(f"is_heading: Text '{text}' matches PNG pattern, returning True")
            return True

    # Check for center alignment
    if 'text-align: center' in style:
        logging.debug("is_heading: Found 'text-align: center' in style, returning True")
        return True

    # Check for significant padding-left
    def parse_padding_left(style):
        match = re.search(r'padding-left:\s*(\d+(?:\.\d+)?)(pt|px)', style)
        if match:
            value, unit = match.groups()
            return float(value)
        return 0
    
    padding_left = parse_padding_left(style)
    if padding_left >= 110 and element.name == 'h3' or element.name == 'h2':
        logging.debug(f"is_heading: Found 'padding-left' >= 110 ({padding_left}), returning True")
        return True

    # Exclude numeric headings (page numbers)
    def is_purely_numeric(text):
        cleaned_text = re.sub(r'[^0-9]', '', text)
        return cleaned_text.isdigit()
        
    if is_purely_numeric(text):
        logging.debug(f"is_heading: Text '{text}' is purely numeric, returning False")
        return False

    # Exclude speaker names
    speaker_pattern = r'^(?:The Acting Speaker|Speaker|Mr|Mrs|Ms|Dr|Hon\.?)\s+'
    if re.match(speaker_pattern, text):
        logging.debug(f"is_heading: Text '{text}' matches speaker pattern, returning False")
        return False

    # Check for all-caps headings (PNG style)
    if text.isupper() and len(text) > 3 and not text.startswith('Page'):
        logging.debug(f"is_heading: Text '{text}' is uppercase heading, returning True")
        return True

    # Consider h2 and h3 tags with text in title case as headings
    if element.name in ['h2', 'h3'] and text == text.title():
        logging.debug(f"is_heading: Element is '{element.name}' with title case text, returning True")
        return True

    logging.debug("is_heading: None of the conditions met, returning False")
    return False

def is_uppercase_heading(element):
    """Check if element is uppercase heading"""
    text = get_inner_text(element)
    # Remove non-alphabetic characters
    letters_only = re.sub(r'[^A-Za-z]+', '', text)
    is_upper = letters_only.isupper() and len(letters_only) > 0
    logging.debug(f"is_uppercase_heading: Checking if '{text}' is uppercase heading: {is_upper}")
    return is_upper

def is_question_heading(element):
    """Check if element is a question heading (PNG-specific patterns)"""
    if element.name not in ['p', 'h2', 'h3']:
        return False

    text = get_inner_text(element).strip()
    style = element.get('style', '')

    logging.debug(f"is_question_heading: Checking element '{text}' with tag '{element.name}' and style '{style}'")

    # PNG-specific question patterns based on content analysis
    png_question_patterns = [
        r"^Contracting SME's to Deliver School Supplies$",
        r"^Supplementary Question$",
        r"^Closure of companies in PNG$",
        r"^Power project in.*Province$",
        r"^Provide Financial Report.*$",
        r"^Length of Repayment Term.*$",
        r"^Promote Police Officers$", 
        r"^National Development Bank$",
        r"^Status of the Economy$",
        # Very specific patterns only
        r"^\([0-9]+\).*\?$",  # Numbered questions like "(1) Why can't..."
    ]

    # Check PNG question patterns
    for pattern in png_question_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            logging.debug(f"is_question_heading: Text '{text}' matches PNG question pattern, returning True")
            return True

    # Exclude purely numeric elements
    def is_purely_numeric(text):
        cleaned_text = re.sub(r'[^0-9]', '', text)
        return cleaned_text.isdigit()
        
    if is_purely_numeric(text):
        logging.debug(f"is_question_heading: Text is purely numeric: {text}")
        return False

    # Exclude speaker names
    speaker_pattern = r'^(?:The Acting Speaker|Speaker|Mr|Mrs|Ms|Dr|Hon\.?)\s+'
    if re.match(speaker_pattern, text):
        logging.debug(f"is_question_heading: Text matches speaker pattern: {text}")
        return False

    # Exclude the 'QUESTIONS' heading itself
    if text.upper() == 'QUESTIONS':
        logging.debug("is_question_heading: Text is 'QUESTIONS', returning False")
        return False

    # Check for significant padding-left
    def parse_padding_left(style):
        match = re.search(r'padding-left:\s*(\d+(?:\.\d+)?)(pt|px)', style)
        if match:
            value, unit = match.groups()
            return float(value)
        return 0
        
    padding_left = parse_padding_left(style)
    
    if padding_left >= 110 and element.name == 'h3' or element.name == 'h2':
        return True

    # Consider h2 and h3 tags with text in title case as question headings
    if element.name in ['h2', 'h3'] and text == text.title():
        logging.debug(f"is_question_heading: Element is '{element.name}' with title case text, returning True")
        return True

    logging.debug("is_question_heading: None of the conditions met, returning False")
    return False

def process_questions(directory, part_number, questions):
    """Process questions and write them to files"""
    questions_dir = os.path.join(directory, f"part{part_number}_questions")
    os.makedirs(questions_dir, exist_ok=True)

    question_titles = []

    for i, (title, content_elements) in enumerate(questions, 1):
        question_content = "\n".join(content_elements)
        cleaned_content = clean_content(question_content)
        write_question(directory, part_number, i, title, cleaned_content)
        question_titles.append(title)

    return question_titles

def preprocess_png_html(soup):
    """Preprocess PNG HTML to convert <br> separated content into proper paragraphs"""
    content_div = soup.find('div', class_='content')
    if not content_div:
        return soup
    
    # Get the text content and split by <br> tags
    html_content = str(content_div)
    
    # Split content by <br> variations
    import re
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
    
    logging.info(f"Preprocessed HTML: created {len(paragraphs)} paragraphs from original content")
    return soup

def process_png_hansard(filename):
    """Process a PNG hansard HTML file and output to collections structure"""
    try:
        # Extract date from filename
        date = extract_date_from_filename(filename)
        
        # Create collections directory
        output_dir = create_collections_directory(date)
        
        # Load the HTML content
        with open(filename, "r", encoding='utf-8') as file:
            soup = BeautifulSoup(file, 'html.parser')
        
        # Preprocess PNG HTML structure
        soup = preprocess_png_html(soup)
        
        logging.info(f"Processing {filename} -> {output_dir}")
        
        # Extract title
        title_tag = soup.find('title')
        title = title_tag.text.strip() if title_tag else f"PNG Hansard {date.strftime('%Y-%m-%d') if date else 'Unknown Date'}"
        
        # Extract the date from the content and get all date elements
        date_str, date_elements = extract_date_from_content(soup)
        logging.info(f"Extracted date from content: {date_str}")
        
        all_elements = soup.find_all(['p', 'h2', 'h3'])
        logging.info(f"Total elements found: {len(all_elements)}")
        
        # Skip table of contents and find actual parliamentary proceedings
        # Look for the actual start of proceedings (usually after "PARLIAMENTARY DEBATES" or session start)
        start_index = 0
        
        # Look for indicators that we've moved past the table of contents
        for i, element in enumerate(all_elements):
            text = get_inner_text(element).strip()
            
            # Look for session start indicators
            if (re.search(r'took the Chair at \d+', text) or 
                re.search(r'PARLIAMENTARY DEBATES', text) or
                re.search(r'The Acting Speaker.*took the Chair', text) or
                (text.startswith('Page ') and any(digit in text for digit in '456789'))):  # Skip early pages
                start_index = i
                logging.info(f"Found start of actual proceedings at index {i}: {text[:60]}...")
                break
        
        if start_index > 0:
            logging.info(f"Skipping table of contents, starting from index {start_index}")
            all_elements = all_elements[start_index:]
        else:
            logging.warning("Could not identify table of contents boundary, processing all content")
        
        # Initialize variables for parsing
        current_part = []
        part_number = 0
        in_questions_section = False
        questions = []
        current_question = []
        question_title = None
        contents_structure = []
        current_part_title = ""
        
        i = 0
        while i < len(all_elements):
            element = all_elements[i]
            text = get_inner_text(element)
            style = element.get('style', '')
            element_tag = element.name
            logging.debug(f"Processing element at index {i}: '{text}' with tag '{element_tag}'")

            if is_heading(element):
                heading_text = text.strip()
                heading_style = style
                heading_tag = element_tag
                logging.debug(f"Found heading: '{heading_text}' at index {i}")

                # Check for consecutive headings and concatenate their texts
                while i + 1 < len(all_elements):
                    next_element = all_elements[i + 1]
                    next_text = get_inner_text(next_element).strip()
                    next_style = next_element.get('style', '')
                    next_tag = next_element.name

                    if is_heading(next_element) and next_tag == heading_tag and next_style == heading_style:
                        i += 1
                        heading_text += ' ' + next_text  # Concatenate with a space
                        logging.debug(f"Concatenated heading: '{heading_text}' at index {i}")
                    else:
                        break  # Stop concatenating

                if in_questions_section:
                    if is_uppercase_heading(element):
                        # Detected the end of the Questions section
                        logging.debug("Detected end of Questions section")
                        # Process any remaining questions
                        if question_title and current_question:
                            questions.append((question_title, current_question))
                        if questions:
                            process_questions(output_dir, part_number, questions)
                            contents_structure.append(("QUESTIONS", [q[0] for q in questions]))
                        in_questions_section = False
                        question_title = None
                        current_question = []
                        # Start a new part with the current heading
                        part_number += 1
                        current_part = [str(element)]
                        current_part_title = heading_text
                    elif is_question_heading(element):
                        heading_text = text.strip()
                        logging.info(f"Found new Question Heading: '{heading_text}'")
                        if question_title and current_question:
                            # Save the previous question
                            logging.info(f"Saved previous question: '{question_title}' with {len(current_question)} elements")
                            questions.append((question_title, current_question))
                        question_title = heading_text
                        current_question = [str(element)]
                    else:
                        # This is a heading but not a question heading; include in current question
                        current_question.append(str(element))
                else:
                    # Outside of questions section
                    if heading_text.upper() == "QUESTIONS":
                        # Save the current part before entering the questions section
                        if current_part:
                            speakers = write_part(output_dir, part_number, current_part, current_part_title)
                            contents_structure.append((current_part_title, []))
                            current_part = []

                        in_questions_section = True
                        part_number += 1
                        current_part_title = heading_text
                        questions = []
                        current_question = []
                        question_title = None
                        logging.info(f"Entered QUESTIONS section at part {part_number}")
                    else:
                        # Start a new part
                        if current_part:
                            speakers = write_part(output_dir, part_number, current_part, current_part_title)
                            contents_structure.append((current_part_title, []))
                        part_number += 1
                        current_part = [str(element)]
                        current_part_title = heading_text
            else:
                # Non-heading elements  
                if in_questions_section:
                    # Check if this non-heading element is actually a question heading
                    if is_question_heading(element):
                        heading_text = text.strip()
                        logging.info(f"Found Question Heading (non-heading element): '{heading_text}'")
                        if question_title and current_question:
                            # Save the previous question
                            logging.info(f"Saved previous question: '{question_title}' with {len(current_question)} elements")
                            questions.append((question_title, current_question))
                        question_title = heading_text
                        current_question = [str(element)]
                    else:
                        current_question.append(str(element))
                else:
                    current_part.append(str(element))
            i += 1

        # Process any remaining content
        if in_questions_section:
            if question_title and current_question:
                logging.info(f"Processing final question: '{question_title}' with {len(current_question)} elements")
                questions.append((question_title, current_question))
            if questions:
                logging.info(f"Processing {len(questions)} questions total")
                process_questions(output_dir, part_number, questions)
                contents_structure.append(("QUESTIONS", [q[0] for q in questions]))
            else:
                logging.warning("QUESTIONS section was detected but no questions were found!")
        if current_part:
            speakers = write_part(output_dir, part_number, current_part, current_part_title)
            contents_structure.append((current_part_title, []))

        # Write the contents structure
        with open(os.path.join(output_dir, "contents.html"), "w", encoding='utf-8') as file:
            file.write("<h2>Contents</h2>\n<ul>")
            for item in contents_structure:
                if item[0] == "QUESTIONS":
                    file.write(f"<li>QUESTIONS<ul>")
                    for title in item[1]:
                        file.write(f"<li>{title}</li>")
                    file.write("</ul></li>")
                else:
                    file.write(f"<li>{item[0]}</li>")
            file.write("</ul>")

        # Count parts and total speakers
        parts_count = len([f for f in os.listdir(output_dir) if f.startswith('part') and f.endswith('.html')])
        
        all_speakers = set()
        for metadata_file in os.listdir(output_dir):
            if metadata_file.endswith('_metadata.txt'):
                with open(os.path.join(output_dir, metadata_file), 'r') as f:
                    content = f.read()
                    speakers = extract_and_clean_speakers(content)
                    all_speakers.update(speakers)
        
        # Write metadata JSON
        metadata = write_metadata_json(output_dir, title, date, len(all_speakers), parts_count)
        
        # Write processing report
        processing_report = {
            "processing_date": datetime.now().isoformat(),
            "source_file": filename,
            "output_directory": output_dir,
            "parts_processed": parts_count,
            "speakers_identified": len(all_speakers),
            "status": "success",
            "metadata": metadata
        }
        
        report_path = os.path.join(output_dir, "processing_report.json")
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(processing_report, f, indent=2, ensure_ascii=False)
        
        logging.info(f"Successfully processed {filename} with {parts_count} parts and {len(all_speakers)} speakers")
        return output_dir, metadata
        
    except Exception as e:
        logging.error(f"Error processing {filename}: {str(e)}")
        raise

def main():
    """Main function to process PNG hansards"""
    import sys
    
    if len(sys.argv) != 2:
        print("Usage: python PNG-hansard-converter-integrated.py <input_html_file>")
        sys.exit(1)
    
    input_file = sys.argv[1]
    
    if not os.path.exists(input_file):
        print(f"Error: File {input_file} does not exist")
        sys.exit(1)
    
    try:
        output_dir, metadata = process_png_hansard(input_file)
        print(f"Successfully processed: {input_file}")
        print(f"Output directory: {output_dir}")
        print(f"Title: {metadata['title']}")
        print(f"Date: {metadata['date']}")
        print(f"Parts: {metadata['parts_count']}")
        print(f"Speakers: {metadata['speakers_count']}")
        
    except Exception as e:
        print(f"Error processing file: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()