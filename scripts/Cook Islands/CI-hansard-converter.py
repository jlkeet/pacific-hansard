import re
import os
from bs4 import BeautifulSoup
import logging
from datetime import datetime
import json

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

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

def write_speakers_metadata(directory, part_number, part_type, speakers, question_number=None):
    """Write speaker metadata to appropriate file"""
    if question_number is None:
        filename = os.path.join(directory, f"part{part_number}_metadata.txt")
    else:
        questions_dir = os.path.join(directory, f"part{part_number}_questions")
        os.makedirs(questions_dir, exist_ok=True)
        filename = os.path.join(questions_dir, f"{part_type.lower()}_question_{question_number}_metadata.txt")
    
    with open(filename, 'w', encoding='utf-8') as f:
        if question_number is None:
            f.write(f"Part {part_number} Speakers:\n")
        else:
            f.write(f"{part_type} Question {question_number} Speakers:\n")
        
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

def extract_questions(content, part_number, directory):
    """Extract oral and written questions from content with improved Q&A detection"""
    soup = BeautifulSoup(content, 'html.parser')
    text = soup.get_text()
    
    oral_questions = []
    written_questions = []
    
    # Check if this section contains questions
    is_oral_section = re.search(r'ORAL\s+QUESTIONS?|Question\s+Time', text, re.IGNORECASE)
    is_written_section = re.search(r'WRITTEN\s+QUESTIONS?', text, re.IGNORECASE)
    
    if not (is_oral_section or is_written_section):
        return 0, 0
    
    # Get all elements
    all_elements = soup.find_all(['p', 'div'])
    
    if is_oral_section:
        # Identify question boundaries by looking for MPs asking questions
        question_starts = []
        current_question = []
        in_question = False
        
        for i, element in enumerate(all_elements):
            elem_text = element.get_text().strip()
            
            # Check if this is a new question starting
            # Look for patterns like "MR T. HEATHER: ... question ..."
            if re.match(r'^(MR|MRS|MS|HON|DR)\.?\s+[A-Z].*?:', elem_text):
                # Check if "question" appears in the next few lines
                context_text = ' '.join(el.get_text() for el in all_elements[i:min(i+5, len(all_elements))])
                if re.search(r'\bquestion\b|\basking\b|\bask\b', context_text, re.IGNORECASE):
                    if current_question:
                        oral_questions.append('\n'.join(current_question))
                    current_question = []
                    in_question = True
            
            if in_question:
                current_question.append(str(element))
                
                # Check if we've reached the end of this Q&A exchange
                # Look for transitions like new speaker asking question or section end
                if i + 1 < len(all_elements):
                    next_text = all_elements[i + 1].get_text().strip()
                    if (re.match(r'^(MR|MRS|MS|HON|DR)\.?\s+[A-Z].*?:', next_text) and 
                        re.search(r'\bquestion\b|\basking\b', ' '.join(el.get_text() for el in all_elements[i+1:min(i+6, len(all_elements))]), re.IGNORECASE)):
                        in_question = False
        
        # Don't forget the last question
        if current_question:
            oral_questions.append('\n'.join(current_question))
    
    # Process written questions similarly if needed
    if is_written_section:
        # Similar logic for written questions
        pass
    
    # Write individual question files
    if oral_questions or written_questions:
        questions_dir = os.path.join(directory, f"part{part_number}_questions")
        os.makedirs(questions_dir, exist_ok=True)
        
        for i, question in enumerate(oral_questions, 1):
            write_question_file(questions_dir, "oral", i, question)
            speakers = extract_and_clean_speakers(question)
            write_speakers_metadata(directory, part_number, "Oral", speakers, i)
            
        for i, question in enumerate(written_questions, 1):
            write_question_file(questions_dir, "written", i, question)
            speakers = extract_and_clean_speakers(question)
            write_speakers_metadata(directory, part_number, "Written", speakers, i)
        
        logging.info(f"Part {part_number}: Extracted {len(oral_questions)} oral and {len(written_questions)} written questions")
        return len(oral_questions), len(written_questions)
    
    return 0, 0

def write_question_file(directory, question_type, number, content):
    """Write individual question to file"""
    filename = os.path.join(directory, f"{question_type}_question_{number}.html")
    cleaned_content = clean_content(content)
    
    with open(filename, 'w', encoding='utf-8') as f:
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
    
    # Try to extract date from various patterns
    date_patterns = [
        r'(\w+day,?\s+\d{1,2}(?:st|nd|rd|th)?\s+[A-Z][a-z]+,?\s+\d{4})',
        r'([A-Z][a-z]+\s+\d{1,2},?\s+\d{4})',
        r'(\d{1,2}-\d{1,2}-\d{4})'
    ]
    
    for pattern in date_patterns:
        match = re.search(pattern, text)
        if match:
            metadata['date'] = match.group(1)
            # Extract day of week if present
            day_match = re.match(r'(\w+day)', match.group(1))
            if day_match:
                metadata['day_of_week'] = day_match.group(1)
            break
    
    # Try to extract from filename if not found in content
    if not metadata['date']:
        date_match = re.search(r'(\w+-\d{1,2}-\w+-\d{2,4})', filename)
        if date_match:
            metadata['date'] = date_match.group(1)
    
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

def validate_extraction(directory_name):
    """Validate the quality of extraction and provide report"""
    validation_report = {
        'directory': directory_name,
        'total_parts': 0,
        'parts_with_speakers': 0,
        'total_speakers': set(),
        'questions_extracted': 0,
        'issues': []
    }
    
    # Count parts
    part_files = [f for f in os.listdir(directory_name) if f.startswith('part') and f.endswith('.html')]
    validation_report['total_parts'] = len(part_files)
    
    # Check speaker extraction
    for part_file in part_files:
        part_num = re.search(r'part(\d+)\.html', part_file).group(1)
        metadata_file = os.path.join(directory_name, f'part{part_num}_metadata.txt')
        
        if os.path.exists(metadata_file):
            with open(metadata_file, 'r', encoding='utf-8') as f:
                content = f.read()
                speakers = re.findall(r'Speaker \d+: (.+)', content)
                if speakers:
                    validation_report['parts_with_speakers'] += 1
                    validation_report['total_speakers'].update(speakers)
                else:
                    validation_report['issues'].append(f"Part {part_num}: No speakers extracted")
    
    # Check questions
    question_dirs = [d for d in os.listdir(directory_name) if d.endswith('_questions')]
    for q_dir in question_dirs:
        q_files = [f for f in os.listdir(os.path.join(directory_name, q_dir)) if f.endswith('.html')]
        validation_report['questions_extracted'] += len(q_files)
    
    # Convert set to list for JSON serialization
    validation_report['total_speakers'] = list(validation_report['total_speakers'])
    
    # Write validation report
    with open(os.path.join(directory_name, 'validation_report.json'), 'w', encoding='utf-8') as f:
        json.dump(validation_report, f, indent=2)
    
    logging.info(f"Validation Report: {validation_report['parts_with_speakers']}/{validation_report['total_parts']} parts have speakers")
    logging.info(f"Total unique speakers: {len(validation_report['total_speakers'])}")
    logging.info(f"Questions extracted: {validation_report['questions_extracted']}")
    
    return validation_report

def split_html(filename):
    """Main function to split HTML hansard into parts"""
    with open(filename, "r", encoding='utf-8') as file:
        soup = BeautifulSoup(file, 'html.parser')
    
    # Extract metadata
    metadata = extract_metadata_from_content(soup, filename)
    
    # Create directory name
    base_name = os.path.splitext(os.path.basename(filename))[0]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    directory_name = f"{base_name.replace('.html', '')}.html_{timestamp}"
    os.makedirs(directory_name, exist_ok=True)
    
    # Write metadata file
    with open(os.path.join(directory_name, "metadata.json"), 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2)
    
    logging.info(f"Processing {filename} -> {directory_name}")
    
    all_divs = soup.find_all('div', style=True)
    
    # Create contents file
    contents_filename = os.path.join(directory_name, "contents.html")
    with open(contents_filename, "w", encoding='utf-8') as file:
        file.write("<h2>Contents</h2>\n<ul>")
    
    current_part = []
    part_number = 0
    contents_list = []
    current_part_title = ""
    
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
                write_speakers_metadata(directory_name, part_number, "Part", speakers)
                
                # Check for questions in this part
                questions_content = "".join(str(d) for d in current_part)
                oral_count, written_count = extract_questions(questions_content, part_number, directory_name)
            
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
        write_speakers_metadata(directory_name, part_number, "Part", speakers)
        
        # Check for questions
        questions_content = "".join(str(d) for d in current_part)
        oral_count, written_count = extract_questions(questions_content, part_number, directory_name)
    
    with open(contents_filename, "a", encoding='utf-8') as file:
        file.write("</ul>")
    
    # Run validation
    validation_report = validate_extraction(directory_name)
    
    logging.info(f"Completed processing {filename}: {part_number} parts created")
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
        filename = "Tue-23-March-2021.html"
    
    if os.path.exists(filename):
        split_html(filename)
    else:
        logging.error(f"File {filename} not found")