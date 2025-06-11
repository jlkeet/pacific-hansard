#!/usr/bin/env python3
"""
Fix formatting in Fiji hansard HTML files by improving paragraph structure
"""
import os
import re
import logging
from pathlib import Path
from bs4 import BeautifulSoup

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('fix_formatting.log'),
        logging.StreamHandler()
    ]
)

# Base directory
BASE_DIR = Path("/Users/jacksonkeet/Pacific Hansard Development")
COLLECTIONS_DIR = BASE_DIR / "collections" / "Fiji"

def fix_html_formatting(html_content):
    """
    Fix HTML formatting by:
    1. Converting spans with br tags to proper paragraphs
    2. Removing empty divs and spans
    3. Improving overall structure
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # First, let's fix line breaks within text
    # Replace standalone <br/> tags between words with spaces
    for br in soup.find_all('br'):
        # Check if br is between text nodes
        prev_text = br.previous_sibling
        next_text = br.next_sibling
        
        if prev_text and next_text:
            # Check if previous ends with a character and next starts with a character
            prev_str = str(prev_text).strip() if isinstance(prev_text, str) else prev_text.get_text().strip()
            next_str = str(next_text).strip() if isinstance(next_text, str) else next_text.get_text().strip()
            
            if prev_str and next_str and prev_str[-1].isalnum() and next_str[0].isalnum():
                # This is a line break within a word/sentence - replace with space
                br.replace_with(' ')
    
    # Create new body content
    new_body = soup.new_tag('body')
    
    # Keep the h3 title if present
    h3 = soup.find('h3')
    if h3:
        new_body.append(h3.extract())
    
    # Collect all text content from divs
    all_content = []
    
    for div in soup.find_all('div'):
        # Skip page markers
        if div.find('a', attrs={'name': True}):
            page_marker = div.extract()
            all_content.append(('page_marker', page_marker))
            continue
        
        # Get text content
        text = div.get_text(separator=' ', strip=True)
        if text:
            # Clean up extra spaces
            text = re.sub(r'\s+', ' ', text)
            all_content.append(('text', text))
    
    # Process content to create proper paragraphs
    current_section = []
    
    for content_type, content in all_content:
        if content_type == 'page_marker':
            # Add accumulated paragraphs
            if current_section:
                para_text = ' '.join(current_section).strip()
                if para_text:
                    new_p = create_paragraph(soup, para_text)
                    new_body.append(new_p)
                current_section = []
            # Add page marker
            new_body.append(content)
        else:
            # Check if this is a new section/heading
            if is_section_heading(content):
                # End current section
                if current_section:
                    para_text = ' '.join(current_section).strip()
                    if para_text:
                        new_p = create_paragraph(soup, para_text)
                        new_body.append(new_p)
                    current_section = []
                # Add heading
                new_h4 = soup.new_tag('h4')
                new_h4.string = content
                new_body.append(new_h4)
            # Check if this is a speaker line
            elif is_speaker_line(content):
                # End current section
                if current_section:
                    para_text = ' '.join(current_section).strip()
                    if para_text:
                        new_p = create_paragraph(soup, para_text)
                        new_body.append(new_p)
                    current_section = []
                # Add speaker line
                new_p = soup.new_tag('p')
                strong = soup.new_tag('strong')
                strong.string = content
                new_p.append(strong)
                new_body.append(new_p)
            else:
                # Regular content - add to current section
                current_section.append(content)
    
    # Handle remaining content
    if current_section:
        para_text = ' '.join(current_section).strip()
        if para_text:
            new_p = create_paragraph(soup, para_text)
            new_body.append(new_p)
    
    # Replace body content
    soup.body.clear()
    for child in list(new_body.children):
        soup.body.append(child)
    
    return str(soup)

def is_section_heading(text):
    """Check if text is likely a section heading"""
    # Common section headings in hansards
    headings = [
        'PRESENT', 'MINUTES', 'QUESTIONS', 'ORAL QUESTIONS', 'WRITTEN QUESTIONS',
        'MINISTERIAL STATEMENT', 'ADJOURNMENT', 'SUSPENSION OF STANDING ORDERS',
        'PRESENTATION OF PAPERS', 'COMMUNICATIONS FROM THE SPEAKER',
        'BILLS', 'MOTIONS', 'PETITIONS'
    ]
    
    # Check if text matches common headings
    text_upper = text.upper().strip()
    for heading in headings:
        if heading in text_upper and len(text) < 100:
            return True
    
    # Check if all caps and short
    if text.isupper() and len(text) < 50:
        return True
        
    return False

def is_speaker_line(text):
    """Check if text is a speaker identification line"""
    # Skip if too long to be a speaker line
    if len(text) > 100:
        return False
        
    # Common patterns for speakers
    patterns = [
        r'^HON\.\s+[A-Z][A-Z\s\.\'-]*[\.-]\s*$',  # HON. NAME.- or HON. NAME.
        r'^(MR|MRS|MS|MADAM)\.?\s+SPEAKER[\.-]\s*$',  # MR. SPEAKER.-
        r'^HON\.\s+.*[\.-]\s*$',  # Any HON. ending with .-
        r'^[A-Z][A-Z\s\.\'-]+[\.-]\s*$'  # All caps name ending with .- or -
    ]
    
    for pattern in patterns:
        if re.match(pattern, text):
            return True
    
    return False

def create_paragraph(soup, text):
    """Create a properly formatted paragraph"""
    # Clean up the text
    text = text.strip()
    
    # Fix common issues
    # Fix spaces before punctuation
    text = re.sub(r'\s+([.,;:!?])', r'\1', text)
    
    # Fix missing spaces after punctuation
    text = re.sub(r'([.,;:!?])([A-Z])', r'\1 \2', text)
    
    # Create paragraph
    new_p = soup.new_tag('p')
    new_p.string = text
    
    return new_p

def process_html_file(file_path):
    """Process a single HTML file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Skip if already has proper paragraphs
        if '<p>' in content:
            logging.info(f"Skipping {file_path} - already has paragraphs")
            return False
            
        # Fix formatting
        fixed_content = fix_html_formatting(content)
        
        # Write back
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(fixed_content)
            
        logging.info(f"Fixed formatting in {file_path}")
        return True
        
    except Exception as e:
        logging.error(f"Error processing {file_path}: {str(e)}")
        return False

def process_all_fiji_hansards():
    """Process all Fiji hansard HTML files"""
    total_files = 0
    fixed_files = 0
    
    # Find all HTML files in Fiji collections
    for html_file in COLLECTIONS_DIR.rglob("*.html"):
        # Skip contents.html files
        if html_file.name == "contents.html":
            continue
            
        total_files += 1
        if process_html_file(html_file):
            fixed_files += 1
    
    logging.info(f"\nProcessing complete!")
    logging.info(f"Total files: {total_files}")
    logging.info(f"Fixed files: {fixed_files}")
    logging.info(f"Already formatted: {total_files - fixed_files}")

def test_single_file():
    """Test on a single file first"""
    test_file = COLLECTIONS_DIR / "2024" / "December" / "6" / "part10.html"
    
    if test_file.exists():
        logging.info(f"Testing on {test_file}")
        
        # Read original
        with open(test_file, 'r', encoding='utf-8') as f:
            original = f.read()
        
        # Fix formatting
        fixed = fix_html_formatting(original)
        
        # Save test output
        test_output = test_file.parent / f"{test_file.stem}_test.html"
        with open(test_output, 'w', encoding='utf-8') as f:
            f.write(fixed)
            
        logging.info(f"Test output saved to {test_output}")
        logging.info("Please review the test output before running on all files")
        
        return test_output
    else:
        logging.error(f"Test file not found: {test_file}")
        return None

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        # Run test mode
        test_output = test_single_file()
        if test_output:
            print(f"\nTest completed. Review the output at: {test_output}")
            print("If satisfied, run without --test flag to process all files")
    else:
        # Confirm before running on all files
        response = input("This will modify all Fiji hansard HTML files. Continue? (y/n): ")
        if response.lower() == 'y':
            process_all_fiji_hansards()
        else:
            print("Operation cancelled")