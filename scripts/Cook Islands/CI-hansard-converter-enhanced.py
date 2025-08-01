#!/usr/bin/env python3
"""
Enhanced Cook Islands Hansard Converter with robust error handling.
Processes HTML hansard files and splits them into structured parts with metadata.
"""

import re
import os
import sys
from bs4 import BeautifulSoup
import logging
from datetime import datetime
import json

# Add common module to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from common.error_handler import (
    logger, PipelineError, DataValidationError, FileProcessingError,
    safe_file_processing, create_pipeline_monitor, validate_document_data,
    log_error_context, retry_on_failure
)

# Configuration
COLLECTIONS_BASE = "/Users/jacksonkeet/Pacific Hansard Development/collections/Cook Islands"


def normalize_name(name):
    """Remove all spaces and convert to uppercase for comparison"""
    return ''.join(name.split()).upper()


def extract_and_clean_speakers(text):
    """Extract all unique speakers from the text with comprehensive pattern matching"""
    try:
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
            try:
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
            except Exception as e:
                logger.warning(f"Error processing pattern {pattern}: {e}")
                continue
        
        # Sort speakers for consistency
        speakers.sort()
        return speakers
        
    except Exception as e:
        logger.error(f"Failed to extract speakers: {e}")
        return []


def write_speakers_metadata(file_path, speakers):
    """Write speaker metadata to appropriate file"""
    try:
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
        
        logger.debug(f"Written speaker metadata to {file_path}")
        
    except IOError as e:
        logger.error(f"Failed to write speaker metadata to {file_path}: {e}")
        raise FileProcessingError(f"Cannot write metadata file: {e}")


def clean_content(content):
    """Clean HTML content while preserving structure"""
    try:
        soup = BeautifulSoup(content, 'html.parser')
        
        # Remove all style attributes
        for tag in soup.find_all(style=True):
            del tag['style']
        
        # Remove all font tags but preserve content
        for font in soup.find_all('font'):
            font.unwrap()
        
        # Remove empty paragraphs and divs
        for tag in soup.find_all(['p', 'div']):
            if not tag.get_text(strip=True):
                tag.decompose()
        
        # Clean up whitespace
        text = str(soup)
        text = re.sub(r'\n\s*\n', '\n\n', text)
        text = re.sub(r' +', ' ', text)
        
        return text.strip()
        
    except Exception as e:
        logger.error(f"Error cleaning content: {e}")
        return content  # Return original if cleaning fails


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
    
    try:
        text = soup.get_text()
        
        # Extract parliament number
        parl_match = re.search(r'(\d+)(?:st|nd|rd|th)\s+Parliament', text, re.IGNORECASE)
        if parl_match:
            metadata['parliament'] = parl_match.group(1)
        
        # Extract session/meeting info
        session_match = re.search(r'(\d+)(?:st|nd|rd|th)\s+(?:Session|Meeting)', text, re.IGNORECASE)
        if session_match:
            metadata['session'] = session_match.group(1)
        
        # Extract date patterns
        date_patterns = [
            r'(\d{1,2})\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{4})',
            r'(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),?\s+(\d{1,2})\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{4})'
        ]
        
        for pattern in date_patterns:
            date_match = re.search(pattern, text, re.IGNORECASE)
            if date_match:
                groups = date_match.groups()
                if len(groups) == 3:
                    day, month, year = groups
                    metadata['date'] = f"{year}-{month}-{day}"
                elif len(groups) == 4:
                    metadata['day_of_week'] = groups[0]
                    day, month, year = groups[1], groups[2], groups[3]
                    metadata['date'] = f"{year}-{month}-{day}"
                break
        
        # Try to extract date from filename if not found in content
        if not metadata['date']:
            filename_date_match = re.search(r'(\d{4})[-_](\d{1,2})[-_](\d{1,2})', filename)
            if filename_date_match:
                year, month, day = filename_date_match.groups()
                metadata['date'] = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
        
        logger.debug(f"Extracted metadata: {metadata}")
        return metadata
        
    except Exception as e:
        logger.error(f"Error extracting metadata: {e}")
        return metadata


def extract_questions(content, part_number, directory):
    """Extract questions from content with error handling"""
    questions = []
    
    try:
        soup = BeautifulSoup(content, 'html.parser')
        all_elements = soup.find_all(['p', 'div'])
        
        # Determine question type
        text_lower = content.lower()
        if 'oral question' in text_lower:
            question_type = 'oral'
        elif 'written question' in text_lower:
            question_type = 'written'
        else:
            question_type = 'general'
        
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
        
        logger.info(f"Extracted {len(questions)} questions from part {part_number}")
        return questions
        
    except Exception as e:
        logger.error(f"Error extracting questions: {e}")
        return questions


@retry_on_failure(max_retries=2, exceptions=(IOError,))
def write_question_file(directory, question_data):
    """Write individual question to file with retry logic"""
    question_type = question_data['type']
    number = question_data['number']
    content = question_data['content']
    
    # Create flattened filename
    filename = f"part{question_data['part_number']}_{question_type}_question_{number}.html"
    file_path = os.path.join(directory, filename)
    
    try:
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
        
        logger.info(f"Written {question_type} question {number} to {filename}")
        
    except Exception as e:
        logger.error(f"Failed to write question file {filename}: {e}")
        raise


@retry_on_failure(max_retries=2, exceptions=(IOError,))
def write_part(directory, part_number, content, title):
    """Write a part to file with retry logic"""
    part_filename = os.path.join(directory, f"part{part_number}.html")
    
    try:
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
        
        logger.debug(f"Written part {part_number} to {part_filename}")
        
    except Exception as e:
        logger.error(f"Failed to write part {part_number}: {e}")
        raise


@safe_file_processing
def split_html(filename):
    """Split HTML file into parts with comprehensive error handling"""
    logger.info(f"Processing file: {filename}")
    
    # Validate file exists
    if not os.path.exists(filename):
        raise FileProcessingError(f"File not found: {filename}")
    
    # Read and parse HTML
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            html_content = f.read()
    except Exception as e:
        raise FileProcessingError(f"Failed to read file {filename}: {e}")
    
    if not html_content.strip():
        raise DataValidationError(f"File {filename} is empty")
    
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Extract metadata
    metadata = extract_metadata_from_content(soup, filename)
    
    # Create directory for output
    base_filename = os.path.splitext(os.path.basename(filename))[0]
    directory_name = os.path.join(COLLECTIONS_BASE, base_filename)
    
    try:
        os.makedirs(directory_name, exist_ok=True)
    except Exception as e:
        raise FileProcessingError(f"Failed to create directory {directory_name}: {e}")
    
    # Write metadata
    metadata_filename = os.path.join(directory_name, "metadata.json")
    try:
        with open(metadata_filename, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2)
    except Exception as e:
        logger.warning(f"Failed to write metadata: {e}")
    
    # Create contents file
    contents_filename = os.path.join(directory_name, "contents.html")
    try:
        with open(contents_filename, "w", encoding='utf-8') as file:
            file.write(f"<h2>Contents - {base_filename}</h2>\n<ul>\n")
    except Exception as e:
        logger.warning(f"Failed to create contents file: {e}")
    
    # Process the document
    all_divs = soup.find_all('div')
    
    current_part = []
    part_number = 0
    contents_list = []
    current_part_title = ""
    all_questions = []
    processed_parts = 0
    failed_parts = 0
    
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
            try:
                if pattern(div):
                    text = div.text.strip()
                    # Additional validation for headers
                    if (len(text) > 3 and 
                        text.isupper() and 
                        not re.match(r'^\d+$', text) and
                        not text.startswith('PAGE')):
                        is_header = True
                        break
            except Exception as e:
                logger.debug(f"Error checking header pattern: {e}")
                continue
        
        if is_header:
            # Save previous part if exists
            if current_part:
                try:
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
                    
                    processed_parts += 1
                    
                except Exception as e:
                    logger.error(f"Failed to process part {part_number}: {e}")
                    failed_parts += 1
            
            # Start new part
            part_number += 1
            current_part = [div]
            current_part_title = div.text.strip()
            contents_list.append(current_part_title)
            
            try:
                with open(contents_filename, "a", encoding='utf-8') as file:
                    file.write(f"<li>{current_part_title}</li>\n")
            except Exception as e:
                logger.warning(f"Failed to update contents file: {e}")
        else:
            current_part.append(div)
    
    # Process the last part
    if current_part:
        try:
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
            
            processed_parts += 1
            
        except Exception as e:
            logger.error(f"Failed to process last part: {e}")
            failed_parts += 1
    
    # Write all questions as flattened files
    questions_written = 0
    questions_failed = 0
    
    for question in all_questions:
        try:
            write_question_file(directory_name, question)
            questions_written += 1
        except Exception as e:
            logger.error(f"Failed to write question: {e}")
            questions_failed += 1
    
    # Close contents file
    try:
        with open(contents_filename, "a", encoding='utf-8') as file:
            file.write("</ul>")
    except Exception as e:
        logger.warning(f"Failed to close contents file: {e}")
    
    # Create validation report
    validation_report = {
        'directory': directory_name,
        'total_parts': part_number,
        'parts_processed': processed_parts,
        'parts_failed': failed_parts,
        'questions_extracted': len(all_questions),
        'questions_written': questions_written,
        'questions_failed': questions_failed,
        'date': metadata.get('date'),
        'parliament': metadata.get('parliament'),
        'processing_timestamp': datetime.now().isoformat()
    }
    
    try:
        with open(os.path.join(directory_name, 'processing_report.json'), 'w', encoding='utf-8') as f:
            json.dump(validation_report, f, indent=2)
    except Exception as e:
        logger.warning(f"Failed to write processing report: {e}")
    
    logger.info(
        f"Completed processing {filename}: {processed_parts}/{part_number} parts, "
        f"{questions_written}/{len(all_questions)} questions"
    )
    
    # Raise error if significant failures
    if failed_parts > processed_parts * 0.5:  # More than 50% failure rate
        raise PipelineError(f"High failure rate: {failed_parts}/{part_number} parts failed")
    
    return directory_name


def main():
    """Main function with pipeline monitoring"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Enhanced Cook Islands Hansard Converter')
    parser.add_argument('files', nargs='*', help='HTML files to process')
    parser.add_argument('--directory', default='html_hansards', help='Directory containing HTML files')
    parser.add_argument('--continue-on-error', action='store_true', help='Continue processing even if some files fail')
    
    args = parser.parse_args()
    
    # Create pipeline monitor
    with create_pipeline_monitor()('cook_islands_converter') as monitor:
        files_to_process = []
        
        if args.files:
            files_to_process = args.files
        else:
            # Process all HTML files in directory
            if os.path.exists(args.directory):
                files_to_process = [
                    os.path.join(args.directory, f) 
                    for f in os.listdir(args.directory) 
                    if f.endswith('.html')
                ]
            else:
                logger.error(f"Directory {args.directory} not found")
                sys.exit(1)
        
        if not files_to_process:
            logger.warning("No HTML files found to process")
            sys.exit(0)
        
        logger.info(f"Processing {len(files_to_process)} files")
        
        for html_file in files_to_process:
            try:
                split_html(html_file)
                monitor.record_success()
            except Exception as e:
                monitor.record_failure(e)
                logger.error(f"Error processing {html_file}: {str(e)}")
                
                if not args.continue_on_error:
                    logger.error("Stopping due to error. Use --continue-on-error to continue processing remaining files")
                    break


if __name__ == "__main__":
    main()