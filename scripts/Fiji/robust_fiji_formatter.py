#!/usr/bin/env python3
"""
Robust Fiji Hansard HTML Formatter
Handles edge cases and provides better error reporting
"""

import os
import re
from bs4 import BeautifulSoup
import glob
import traceback

def is_speaker_line(text):
    """Check if text starts with a speaker designation"""
    speaker_patterns = [
        r'^HON\.\s+[A-Z]',
        r'^MR\.\s+[A-Z]',
        r'^MADAM\s+[A-Z]',
        r'^DR\.\s+[A-Z]',
        r'^MRS\.\s+[A-Z]',
        r'^MS\.\s+[A-Z]',
    ]
    
    text = text.strip()
    for pattern in speaker_patterns:
        if re.match(pattern, text, re.IGNORECASE):
            return True
    return False

def format_fiji_html_simple(html_content):
    """Simplified formatting that focuses on the most important improvements"""
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Add or update styles
        style = soup.find('style')
        if not style:
            head = soup.find('head')
            if head:
                style = soup.new_tag('style')
                head.append(style)
        
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
        h3, h4 { 
            color: #1a1a1a;
            margin-top: 25px;
            margin-bottom: 15px;
        }
        p { 
            margin-bottom: 16px;
            text-align: justify;
        }
        .speaker {
            font-weight: bold;
            color: #0066cc;
            display: block;
            margin-top: 20px;
            margin-bottom: 10px;
        }
        .procedural {
            text-align: center;
            font-style: italic;
            color: #666;
            margin: 20px 0;
        }
        """
        
        # Process paragraphs to identify speakers
        body = soup.find('body')
        if body:
            paragraphs = body.find_all('p')
            
            for p in paragraphs:
                text = p.get_text(strip=True)
                
                # Check if this is a procedural line
                if text in ['Question put.', 'Motion agreed to.', 'House adjourned.']:
                    p['class'] = 'procedural'
                
                # Check if paragraph starts with a speaker
                elif is_speaker_line(text):
                    # Find where the speaker name ends (usually at : or .- or -)
                    match = re.match(r'^([A-Z][A-Z\s.\'-]+(?:\([^)]+\))?)[:\-.](.*)$', text, re.IGNORECASE)
                    if match:
                        speaker = match.group(1).strip()
                        dialogue = match.group(2).strip()
                        
                        # Create new structure
                        new_p = soup.new_tag('p')
                        speaker_span = soup.new_tag('span')
                        speaker_span['class'] = 'speaker'
                        speaker_span.string = speaker + ":"
                        new_p.append(speaker_span)
                        
                        if dialogue:
                            new_p.append(" " + dialogue)
                        
                        p.replace_with(new_p)
        
        return str(soup)
    
    except Exception as e:
        print(f"Error in format_fiji_html_simple: {str(e)}")
        return html_content  # Return original if error

def process_file(file_path):
    """Process a single file with error handling"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Skip if already processed (has our custom styles)
        if 'class="speaker"' in content or 'margin: 0 auto;' in content:
            return 'already_processed'
        
        formatted_content = format_fiji_html_simple(content)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(formatted_content)
        
        return 'success'
    
    except Exception as e:
        return f'error: {str(e)}'

def process_fiji_hansards():
    """Process all Fiji hansard files with detailed reporting"""
    fiji_dirs = [
        "/Users/jacksonkeet/Pacific Hansard Development/collections/Fiji",
        "/Users/jacksonkeet/Pacific Hansard Development/scripts/Fiji"
    ]
    
    stats = {
        'success': 0,
        'already_processed': 0,
        'errors': 0,
        'total': 0
    }
    
    error_files = []
    
    for directory in fiji_dirs:
        if not os.path.exists(directory):
            continue
            
        print(f"\nProcessing directory: {directory}")
        html_files = glob.glob(os.path.join(directory, '**/*.html'), recursive=True)
        
        for file_path in html_files:
            # Skip certain files
            if any(skip in file_path for skip in ['contents.html', 'env/', '__pycache__']):
                continue
            
            stats['total'] += 1
            result = process_file(file_path)
            
            if result == 'success':
                stats['success'] += 1
                if stats['success'] % 50 == 0:
                    print(f"  Processed {stats['success']} files...")
            elif result == 'already_processed':
                stats['already_processed'] += 1
            else:
                stats['errors'] += 1
                error_files.append((file_path, result))
    
    # Print summary
    print(f"\n{'='*50}")
    print(f"PROCESSING COMPLETE")
    print(f"{'='*50}")
    print(f"Total files found: {stats['total']}")
    print(f"Successfully processed: {stats['success']}")
    print(f"Already processed: {stats['already_processed']}")
    print(f"Errors: {stats['errors']}")
    
    if error_files:
        print(f"\nFirst 10 errors:")
        for file_path, error in error_files[:10]:
            print(f"  {file_path}")
            print(f"    -> {error}")
    
    print(f"\nOverall success rate: {((stats['success'] + stats['already_processed']) / stats['total'] * 100):.1f}%")

if __name__ == "__main__":
    process_fiji_hansards()