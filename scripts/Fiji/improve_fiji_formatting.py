#!/usr/bin/env python3
"""
Enhanced Fiji Hansard HTML Formatter
This script improves the formatting of Fiji hansard HTML files with better
paragraph structure, speaker identification, and overall readability.
"""

import os
import re
from bs4 import BeautifulSoup, NavigableString
import glob

def is_page_marker(text):
    """Check if text is a page number or marker"""
    patterns = [
        r'^Page \d+$',
        r'^\d+$',  # Just numbers (like "484", "485")
        r'^\d+\s+Questions$',
        r'^Questions\s+\d+$',
        r'^\d+th\s+\w+\.,\s+\d{4}$'  # Date patterns like "10th Feb., 2021"
    ]
    return any(re.match(pattern, text.strip(), re.IGNORECASE) for pattern in patterns)

def is_speaker_line(text):
    """Enhanced speaker detection"""
    # More comprehensive speaker patterns
    speaker_patterns = [
        r'^(HON\.\s+[A-Z][A-Z\s.\'-]+)(\s*\([^)]+\))?[:\-.]',  # HON. NAME (Title):
        r'^(MR\.\s+[A-Z][A-Z\s.\'-]+)[:\-.]',
        r'^(MADAM\s+[A-Z][A-Z\s.\'-]+)[:\-.]',
        r'^(DR\.\s+[A-Z][A-Z\s.\'-]+)[:\-.]',
        r'^(MRS\.\s+[A-Z][A-Z\s.\'-]+)[:\-.]',
        r'^(MS\.\s+[A-Z][A-Z\s.\'-]+)[:\-.]',
        r'^(HON\.\s+SPEAKER)[:\-.]',
        r'^(HON\.\s+DEPUTY\s+SPEAKER)[:\-.]',
        r'^(HON\.\s+ACTING\s+SPEAKER)[:\-.]',
        r'^(HON\.\s+ASSISTANT\s+MINISTER[^:]+)[:\-.]',
        r'^(HON\.\s+MINISTER[^:]+)[:\-.]',
        r'^(HON\.\s+ATTORNEY-GENERAL)[:\-.]',
        r'^(HON\.\s+PRIME\s+MINISTER)[:\-.]',
        r'^(HON\.\s+LEADER\s+OF[^:]+)[:\-.]'
    ]
    
    text = text.strip()
    for pattern in speaker_patterns:
        if re.match(pattern, text, re.IGNORECASE):
            return True
    return False

def extract_speaker_and_dialogue(text):
    """Extract speaker name and their dialogue from a line"""
    for pattern in [
        r'^(HON\.\s+[A-Z][A-Z\s.\'-]+(?:\s*\([^)]+\))?)[\s:\-.]+(.*)$',
        r'^(MR\.\s+[A-Z][A-Z\s.\'-]+)[\s:\-.]+(.*)$',
        r'^(MADAM\s+[A-Z][A-Z\s.\'-]+)[\s:\-.]+(.*)$',
        r'^(DR\.\s+[A-Z][A-Z\s.\'-]+)[\s:\-.]+(.*)$',
        r'^(MRS\.\s+[A-Z][A-Z\s.\'-]+)[\s:\-.]+(.*)$',
        r'^(MS\.\s+[A-Z][A-Z\s.\'-]+)[\s:\-.]+(.*)$',
        r'^(HON\.\s+SPEAKER)[\s:\-.]+(.*)$',
        r'^(HON\.\s+[A-Z\s.\'-]+)[\s:\-.]+(.*)$'
    ]:
        match = re.match(pattern, text.strip(), re.IGNORECASE)
        if match:
            return match.group(1).strip(), match.group(2).strip()
    return None, text

def is_procedural_text(text):
    """Check if text is procedural (e.g., 'Question put.', 'Motion agreed to.')"""
    procedural_patterns = [
        r'^Question put\.?$',
        r'^Motion agreed to\.?$',
        r'^Motion (carried|passed|lost)\.?$',
        r'^Vote recorded\.?$',
        r'^House adjourned\.?$',
        r'^The (House|Parliament) (met|resumed).*$',
        r'^\(.*\)$',  # Text in parentheses
        r'^Amendment.*$',
        r'^Division.*$'
    ]
    return any(re.match(pattern, text.strip(), re.IGNORECASE) for pattern in procedural_patterns)

def is_section_heading(text):
    """Check if text is a section heading"""
    heading_patterns = [
        r'^[A-Z][A-Z\s]+$',  # All caps
        r'^ORAL QUESTIONS?$',
        r'^WRITTEN QUESTIONS?$',
        r'^MINISTERIAL STATEMENTS?$',
        r'^BILLS?$',
        r'^MOTIONS?$',
        r'^MINUTES?$',
        r'^MESSAGES?$',
        r'^PAPERS?$',
        r'^PRESENTATION OF.*$',
        r'^DEBATE ON.*$',
        r'^RESUMPTION OF DEBATE.*$',
        r'^Question No\.\s*\d+.*$',
        r'^\(Question No\.\s*\d+/\d+\)$'
    ]
    
    text = text.strip()
    # Check if it's short (less than 50 chars) and matches a pattern
    if len(text) < 50:
        for pattern in heading_patterns:
            if re.match(pattern, text, re.IGNORECASE):
                return True
    return False

def split_into_sentences(text):
    """Split text into sentences for better paragraph formation"""
    # Improved sentence splitting that handles abbreviations
    sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z])', text)
    # Further split on common sentence boundaries
    result = []
    for sentence in sentences:
        # Don't split on common abbreviations
        if not re.search(r'\b(Mr|Mrs|Ms|Dr|Hon|Sr|Jr|vs|etc|i\.e|e\.g)\.$', sentence):
            result.append(sentence)
        else:
            # If it ends with an abbreviation, combine with next sentence
            if result:
                result[-1] += ' ' + sentence
            else:
                result.append(sentence)
    return result

def create_paragraphs_from_speech(text):
    """Split long speeches into logical paragraphs"""
    # Split by double spaces or specific markers
    paragraphs = re.split(r'\s{2,}|\n\n', text)
    
    # If no natural breaks, split by sentences and group
    if len(paragraphs) == 1 and len(text) > 500:
        sentences = split_into_sentences(text)
        paragraphs = []
        current_para = []
        
        for sentence in sentences:
            current_para.append(sentence)
            # Create paragraph every 3-4 sentences or at natural breaks
            if (len(current_para) >= 3 or 
                re.search(r'(Mr\.\s*Speaker|Honourable Members?|Sir|Madam)', sentence, re.IGNORECASE)):
                paragraphs.append(' '.join(current_para))
                current_para = []
        
        if current_para:
            paragraphs.append(' '.join(current_para))
    
    return [p.strip() for p in paragraphs if p.strip()]

def enhance_fiji_html(html_content):
    """Main function to enhance Fiji hansard HTML formatting"""
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Process existing content
    body = soup.find('body')
    if not body:
        # If there's no body tag, create one
        body = soup.new_tag('body')
        # Move all content into the body
        for element in list(soup.children):
            if element.name and element.name not in ['html', 'head']:
                body.append(element.extract())
        
        # Find or create html tag
        html_tag = soup.find('html')
        if not html_tag:
            html_tag = soup.new_tag('html')
            soup.append(html_tag)
        
        html_tag.append(body)
    
    # Create a new body for reformatted content
    new_body = soup.new_tag('body')
    
    current_speaker = None
    current_speech_parts = []
    
    for element in body.find_all(['h3', 'h4', 'p']):
        text = element.get_text(strip=True)
        
        if not text:
            continue
        
        # Skip page markers
        if is_page_marker(text):
            continue
        
        # Handle existing headings
        if element.name in ['h3', 'h4']:
            # Flush any pending speech
            if current_speaker and current_speech_parts:
                create_speech_block(new_body, current_speaker, current_speech_parts)
                current_speaker = None
                current_speech_parts = []
            
            new_body.append(element)
            continue
        
        # Check for section headings
        if is_section_heading(text) and len(text) < 50:
            # Flush any pending speech
            if current_speaker and current_speech_parts:
                create_speech_block(new_body, current_speaker, current_speech_parts)
                current_speaker = None
                current_speech_parts = []
            
            new_h4 = soup.new_tag('h4')
            new_h4.string = text
            new_body.append(new_h4)
            continue
        
        # Check for speaker lines
        speaker, dialogue = extract_speaker_and_dialogue(text)
        if speaker:
            # Flush previous speaker's content
            if current_speaker and current_speech_parts:
                create_speech_block(new_body, current_speaker, current_speech_parts)
            
            current_speaker = speaker
            current_speech_parts = [dialogue] if dialogue else []
        
        # Check for procedural text
        elif is_procedural_text(text):
            # Flush any pending speech
            if current_speaker and current_speech_parts:
                create_speech_block(new_body, current_speaker, current_speech_parts)
                current_speaker = None
                current_speech_parts = []
            
            proc_p = soup.new_tag('p')
            proc_p['class'] = 'procedural'
            em = soup.new_tag('em')
            em.string = text
            proc_p.append(em)
            new_body.append(proc_p)
        
        # Regular content - accumulate for current speaker
        else:
            if current_speaker:
                current_speech_parts.append(text)
            else:
                # No current speaker, create a regular paragraph
                p = soup.new_tag('p')
                p.string = text
                new_body.append(p)
    
    # Don't forget the last speech
    if current_speaker and current_speech_parts:
        create_speech_block(new_body, current_speaker, current_speech_parts)
    
    # Replace old body with new body
    body.replace_with(new_body)
    
    # Add improved CSS
    style = soup.find('style')
    if style:
        style.string = """
        body { 
            font-family: Arial, sans-serif; 
            line-height: 1.8; 
            padding: 20px; 
            max-width: 900px; 
            margin: 0 auto;
            color: #333;
        }
        h3 { 
            color: #1a1a1a;
            margin-top: 30px;
            margin-bottom: 20px;
            font-size: 1.8em;
        }
        h4 {
            color: #2c2c2c;
            margin-top: 25px;
            margin-bottom: 15px;
            font-size: 1.3em;
            font-weight: 600;
        }
        p { 
            margin-bottom: 18px;
            text-align: justify;
        }
        .speech-block {
            margin-bottom: 25px;
            padding-left: 20px;
            border-left: 3px solid #e0e0e0;
        }
        .speaker-name {
            font-weight: bold;
            color: #0066cc;
            margin-bottom: 10px;
            font-size: 1.1em;
        }
        .speech-content p {
            margin-bottom: 15px;
        }
        .procedural {
            text-align: center;
            margin: 20px 0;
            color: #666;
            font-style: italic;
        }
        .question-number {
            font-weight: bold;
            color: #666;
            margin-bottom: 15px;
        }
        """
    
    return str(soup)

def create_speech_block(parent, speaker, speech_parts):
    """Create a formatted speech block"""
    # Get the BeautifulSoup object from the parent element
    soup = parent
    while soup.parent:
        soup = soup.parent
    
    # Create speech container
    speech_div = soup.new_tag('div')
    speech_div['class'] = 'speech-block'
    
    # Add speaker name
    speaker_p = soup.new_tag('p')
    speaker_p['class'] = 'speaker-name'
    speaker_p.string = speaker + ":"
    speech_div.append(speaker_p)
    
    # Add speech content
    content_div = soup.new_tag('div')
    content_div['class'] = 'speech-content'
    
    # Combine all speech parts and split into paragraphs
    full_speech = ' '.join(speech_parts)
    paragraphs = create_paragraphs_from_speech(full_speech)
    
    for para_text in paragraphs:
        if para_text:
            p = soup.new_tag('p')
            p.string = para_text
            content_div.append(p)
    
    speech_div.append(content_div)
    parent.append(speech_div)

def process_fiji_hansard_files(directory):
    """Process all Fiji hansard HTML files in a directory"""
    html_files = glob.glob(os.path.join(directory, '**/*.html'), recursive=True)
    
    processed = 0
    errors = 0
    
    for file_path in html_files:
        # Skip contents.html files
        if 'contents.html' in file_path:
            continue
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check if this is a Fiji hansard file (simple check)
            if '<body>' in content or '<h3>' in content:
                enhanced_content = enhance_fiji_html(content)
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(enhanced_content)
                
                processed += 1
                if processed % 100 == 0:
                    print(f"Processed {processed} files...")
        
        except Exception as e:
            print(f"Error processing {file_path}: {str(e)}")
            errors += 1
    
    print(f"\nProcessing complete!")
    print(f"Files processed: {processed}")
    print(f"Errors: {errors}")

if __name__ == "__main__":
    # Process Fiji collections
    fiji_dirs = [
        "/Users/jacksonkeet/Pacific Hansard Development/collections/Fiji",
        "/Users/jacksonkeet/Pacific Hansard Development/scripts/Fiji"
    ]
    
    for directory in fiji_dirs:
        if os.path.exists(directory):
            print(f"\nProcessing directory: {directory}")
            process_fiji_hansard_files(directory)