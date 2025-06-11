import re
import os
from bs4 import BeautifulSoup

def normalize_name(name):
    """Remove all spaces and convert to uppercase."""
    return ''.join(name.split()).upper()

def extract_and_clean_speakers(text):
    """Extract and deduplicate speaker names from the text."""
    speakers = []
    seen = set()
    # Pattern to capture HON. followed by titles and names
    pattern = r'HON\.|MR\s+((?:PROFESSOR|DR\.|MR\.|MRS\.|MS\.)?\s*[A-Z][A-Z.\s]+(?:\s[A-Z][a-z]+)*)'
    
    matches = re.findall(pattern, text)
    for match in matches:
        name = match.strip().rstrip('.')  # Remove trailing period if present
        normalized_name = normalize_name(name)
        if normalized_name and normalized_name not in seen:
            seen.add(normalized_name)
            speakers.append(name)  # Add the original name, not the normalized version
    
    return speakers

def speaker_str(speakers):
    """Format a list of speakers into a string."""
    return "\n".join([f"Speaker {i+1}: {speaker}" for i, speaker in enumerate(speakers)])

def write_speakers_metadata(directory, part_number, part_type, speakers, question_number=None):
    """Write speaker metadata to a file."""
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
        for i, speaker in enumerate(speakers, 1):
            f.write(f"Speaker {i}: {speaker}\n")
        f.write("\n")

def clean_content(content):
    """Clean HTML content by removing attributes and replacing <br> with newlines."""
    soup = BeautifulSoup(content, 'html.parser')
    
    for tag in soup.find_all():
        if tag.name != 'img':
            tag.attrs = {}
    
    for br in soup.find_all("br"):
        br.replace_with("\n")
    
    return str(soup)

def split_html(filename):
    """
    Split an HTML file into multiple parts based on section headings.
    
    Args:
        filename: Path to the HTML file to process
        
    Returns:
        A list of tuples (section_title, []) representing the structure of the document
    """
    with open(filename, "r", encoding='utf-8') as file:
        soup = BeautifulSoup(file, 'html.parser')

    date_pattern = re.compile(r'\d{1,2}\w{2}\s+[A-Z][a-z]+,\s+\d{4}')
    date_div = soup.find('div', string=date_pattern)
    if date_div:
        date_str = date_div.text.strip()
    else:
        date_str = filename
    
    directory_name = f"Hansard_{date_str}"
    os.makedirs(directory_name, exist_ok=True)

    all_divs = soup.find_all('div', style=True)

    contents_filename = os.path.join(directory_name, "contents.html")
    with open(contents_filename, "w", encoding='utf-8') as file:
        file.write("<h2>Contents</h2>\n<ul>")
    
    current_part = []
    part_number = 0
    in_questions_section = False
    contents_structure = []
    current_part_title = []

    for div in all_divs:
        span = div.find('span', {'style': lambda value: value and 'TimesNewRomanPS-BoldMT' and 'font-size:12px' in value or 'Times New Roman,Bold' and 'font-size:12px' in value})
        if span and div.text.strip().isupper():
            if current_part:
                write_part(directory_name, part_number, current_part, current_part_title)
                speakers = extract_and_clean_speakers("\n".join(str(d) for d in current_part))
                write_speakers_metadata(directory_name, part_number, "Part", speakers)
                contents_structure.append((current_part_title, []))
            
            part_number += 1
            current_part = [div]
            current_part_title = div.text.strip()
            
            if "QUESTION TIME" in current_part_title:
                in_questions_section = True
            
            with open(contents_filename, "a", encoding='utf-8') as file:
                file.write(f"<li>{current_part_title}</li>\n")
        else:
            current_part.append(div)

    # Process the last part
    if current_part:
        write_part(directory_name, part_number, current_part, current_part_title)
        speakers = extract_and_clean_speakers("\n".join(str(d) for d in current_part))
        write_speakers_metadata(directory_name, part_number, "Part", speakers)
        contents_structure.append((current_part_title, []))

    with open(contents_filename, "a", encoding='utf-8') as file:
        file.write("</ul>")

    return contents_structure

def write_part(directory, part_number, content, title):
    """Write a single part of the hansard to an HTML file."""
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
    </style>
</head>
<body>
{cleaned_content}
</body>
</html>
        """)

if __name__ == "__main__":
    # When run directly, process files specified as command line arguments
    import sys
    
    if len(sys.argv) > 1:
        # Process all HTML files provided as arguments
        for html_file in sys.argv[1:]:
            print(f"Processing {html_file}...")
            split_html(html_file)
    else:
        print("Usage: python CI_hansard_converter.py <html_file1> [html_file2] [...]")
        print("No files specified, no action taken.")