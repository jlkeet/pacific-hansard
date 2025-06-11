import re
import os
import logging
from bs4 import BeautifulSoup
from datetime import datetime
import dateparser

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

def normalize_name(name):
    # Remove all spaces and convert to uppercase
    return ''.join(name.split()).upper()

def extract_and_clean_speakers(content):
    soup = BeautifulSoup(content, 'html.parser')
    speakers = []
    seen = set()
    for p in soup.find_all('p'):
        # Get the full text of the paragraph with spaces between elements
        text = p.get_text(separator=' ').strip()
        # Updated regex pattern to handle double-barreled names and titles with or without periods
        pattern = r'^((?:Hon\.?|Professor|Dr\.?|Mr\.?|Mrs\.?|Ms\.?|Madam)\s+[A-Z][A-Za-z\'\.\-]+\s*[\-\–\—])'
        match = re.match(pattern, text)
        if match:
            # Extract the name before the hyphen
            name = match.group(1).strip().rstrip('-').strip()
            normalized_name = normalize_name(name)
            if normalized_name and normalized_name not in seen:
                seen.add(normalized_name)
                speakers.append(name)
    return speakers

def speaker_str(speakers):
    return "\n".join([f"Speaker {i+1}: {speaker}" for i, speaker in enumerate(speakers)])

def write_speakers_metadata(directory, part_number, part_type, speakers, question_number=None):
    if question_number is None:
        filename = os.path.join(directory, f"part{part_number}_metadata.txt")
    else:
        questions_dir = os.path.join(directory, f"part{part_number}_questions")
        os.makedirs(questions_dir, exist_ok=True)
        filename = os.path.join(questions_dir, f"oral_question_{question_number}_metadata.txt")
    
    with open(filename, 'w', encoding='utf-8') as f:
        if question_number is None:
            f.write(f"Part {part_number} Speakers:\n")
        else:
            f.write(f"{part_type} Question {question_number} Speakers:\n")
        for i, speaker in enumerate(speakers, 1):
            f.write(f"Speaker {i}: {speaker}\n")
        f.write("\n")

def clean_content(content):
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

def is_uppercase_heading(element):
    text = get_inner_text(element)
    # Remove non-alphabetic characters
    letters_only = re.sub(r'[^A-Za-z]+', '', text)
    is_upper = letters_only.isupper() and len(letters_only) > 0
    logging.debug(f"is_uppercase_heading: Checking if '{text}' is uppercase heading: {is_upper}")
    return is_upper

def split_questions(content):
    soup = BeautifulSoup(content, 'html.parser')
    questions = []
    current_question = []
    
    for element in soup.find_all(['h3', 'p']):
        if element.name == 'h3' or (element.name == 'p' and element.find('span') and '-' in element.get_text()):
            if current_question:
                questions.append('\n'.join(current_question))
            current_question = [str(element)]
        else:
            current_question.append(str(element))
    
    if current_question:
        questions.append('\n'.join(current_question))
    
    return questions

def parse_padding_left(style):
    match = re.search(r'padding-left:\s*(\d+(?:\.\d+)?)(pt|px)', style)
    if match:
        value, unit = match.groups()
        return float(value)
    return 0

def get_inner_text(element):
    # Find the <a> tag inside the element
    a_tag = element.find('a')
    if a_tag:
        text = a_tag.get_text(separator=' ', strip=True)
        logging.debug(f"get_inner_text: Found <a> tag with text '{text}'")
        return text
    else:
        # If there's no <a> tag, get the text from the element itself
        text = element.get_text(separator=' ', strip=True)
        logging.debug(f"get_inner_text: No <a> tag found, using element text '{text}'")
        return text

def is_heading(element):
    if element.name not in ['p', 'h2', 'h3']:
        return False

    style = element.get('style', '')
    text = get_inner_text(element)

    logging.debug(f"is_heading: Checking element '{text}' with tag '{element.name}' and style '{style}'")

    # Check for center alignment
    if 'text-align: center' in style:
        logging.debug("is_heading: Found 'text-align: center' in style, returning True")
        return True

    # Check for significant padding-left
    padding_left = parse_padding_left(style)
    if padding_left >= 110 and element.name == 'h3' or element.name == 'h2':
        logging.debug(f"is_heading: Found 'padding-left' >= 110 ({padding_left}), returning True")
        return True

    # Exclude numeric headings
    if is_purely_numeric(text):
        logging.debug(f"is_heading: Text '{text}' is purely numeric, returning False")
        return False

    # Exclude speaker names
    speaker_pattern = r'^(?:Hon\.?|Professor|Dr\.?|Mr\.?|Mrs\.?|Ms\.?|Madam)\s+[A-Z]'
    if re.match(speaker_pattern, text):
        logging.debug(f"is_heading: Text '{text}' matches speaker pattern, returning False")
        return False

    # Consider h2 and h3 tags with text in title case as headings
    if element.name in ['h2', 'h3'] and text == text.title():
        logging.debug(f"is_heading: Element is '{element.name}' with title case text, returning True")
        return True

    logging.debug("is_heading: None of the conditions met, returning False")
    return False

def is_question_heading(element):
    """
    Determines if the element is a question heading based on specific patterns.
    """
    if element.name not in ['p', 'h2', 'h3']:
        return False

    text = get_inner_text(element)
    style = element.get('style', '')

    logging.debug(f"is_question_heading: Checking element '{text}' with tag '{element.name}' and style '{style}'")

    # Exclude elements that are purely numeric (e.g., page numbers)
    if is_purely_numeric(text):
        logging.debug(f"is_question_heading: Text is purely numeric: {text}")
        return False

    # Exclude elements that start with speaker names
    speaker_pattern = r'^(?:Hon\.?|Professor|Dr\.?|Mr\.?|Mrs\.?|Ms\.?|Madam)\s+[A-Z]'
    if re.match(speaker_pattern, text):
        logging.debug(f"is_question_heading: Text matches speaker pattern: {text}")
        return False

    # Exclude the 'QUESTIONS' heading itself
    if text.upper() == 'QUESTIONS':
        logging.debug("is_question_heading: Text is 'QUESTIONS', returning False")
        return False

    # Check if text contains 'Question' (case-insensitive)
    # if 'question' in text.lower():
    #     logging.debug("is_question_heading: Text contains 'question', returning True")
    #     return True

    # Check for significant padding-left
    padding_left = parse_padding_left(style)
    
    if padding_left >= 110 and element.name == 'h3' or element.name == 'h2':
        get_inner_text(element)
        return True

    # Consider h2 and h3 tags with text in title case as question headings
    if element.name in ['h2', 'h3'] and text == text.title():
        logging.debug(f"is_question_heading: Element is '{element.name}' with title case text, returning True")
        return True

    logging.debug("is_question_heading: None of the conditions met, returning False")
    return False

def is_numeric_heading(text):
    """
    Returns True if the heading contains only numbers (after removing non-digit characters), False otherwise.
    """
    cleaned_text = re.sub(r'[^0-9]', '', text)
    return cleaned_text.isdigit()

def is_purely_numeric(text):
    """
    Returns True if the text is purely numeric or contains only numbers and certain delimiters (like slashes).
    """
    cleaned_text = re.sub(r'[^0-9]', '', text)
    return cleaned_text.isdigit()

def extract_date_from_content(soup):
    date_texts = []
    date_elements = []
    date_pattern = re.compile(r'\b\d{1,2}\s+\w+\s+\d{4}\b')  # e.g., '13 February 2021'
    for p in soup.find_all('p', style=True):
        style = p.get('style', '')
        if 'text-align: center' in style:
            text = p.get_text(separator=' ', strip=True)
            if date_pattern.search(text):
                date_obj = dateparser.parse(text)
                if date_obj:
                    date_str = date_obj.strftime('%Y-%m-%d')
                    date_texts.append(date_str)
                    date_elements.append(p)
    if date_texts:
        return date_texts[0], date_elements
    else:
        return "Unknown-Date", []

def write_question(questions_dir, question_number, title, content):
    filename = os.path.join(questions_dir, f"oral_question_{question_number}.html")
    with open(filename, "w", encoding='utf-8') as file:
        file.write(f"""
<!DOCTYPE html>
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
{content}
</body>
</html>
    """)

def process_questions(directory, part_number, questions):
    questions_dir = os.path.join(directory, f"part{part_number}_questions")
    os.makedirs(questions_dir, exist_ok=True)

    question_titles = []

    for i, (title, content_elements) in enumerate(questions, 1):
        question_content = "\n".join(content_elements)
        cleaned_content = clean_content(question_content)
        write_question(questions_dir, i, title, cleaned_content)
        speakers = extract_and_clean_speakers(cleaned_content)
        # Pass "Oral" as the part_type since we are using 'oral_question_' prefix
        write_speakers_metadata(directory, part_number, "Oral", speakers, i)
        question_titles.append(title)

    return question_titles

def write_part(directory, part_number, content):
    part_filename = os.path.join(directory, f"part{part_number}.html")
    cleaned_content = clean_content("\n".join(content))
    with open(part_filename, "w", encoding='utf-8') as part_file:
        part_file.write(f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Hansard Part {part_number}</title>
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
    speakers = extract_and_clean_speakers(cleaned_content)
    write_speakers_metadata(directory, part_number, "Part", speakers)

def split_html(filename):
    # Load the HTML content
    with open(filename, "r", encoding='utf-8') as file:
        soup = BeautifulSoup(file, 'html.parser')
    
    # Extract the date from the content and get all date elements
    date_str, date_elements = extract_date_from_content(soup)
    logging.info(f"Extracted date: {date_str}")
    
    # Create the directory using the date
    directory_name = f"Hansard_{date_str}"
    os.makedirs(directory_name, exist_ok=True)
    
    all_elements = soup.find_all(['p', 'h2', 'h3'])
    logging.info(f"Total elements found: {len(all_elements)}")
    
    # Find the indices of the date elements in all_elements
    date_indices = []
    for date_el in date_elements:
        try:
            index = all_elements.index(date_el)
            date_indices.append(index)
        except ValueError:
            continue  # date_el not in all_elements
    
    if len(date_indices) >= 2:
        # Start parsing from the element after the second date occurrence
        start_index = date_indices[1] + 1
        logging.info(f"Starting parsing from index {start_index} after the second date occurrence.")
        all_elements = all_elements[start_index:]
    else:
        logging.warning("Less than two date occurrences found. Starting from the beginning.")
        # If less than two dates found, start from the beginning
        all_elements = all_elements[date_indices[0]:] if date_indices else all_elements
    
    # Proceed with parsing as before
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
                        process_questions(directory_name, part_number, questions)
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
                    logging.debug(f"Found new Question Heading: '{heading_text}'")
                    if question_title and current_question:
                        # Save the previous question
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
                        write_part(directory_name, part_number, current_part)
                        speakers = extract_and_clean_speakers("\n".join(current_part))
                        write_speakers_metadata(directory_name, part_number, "Part", speakers)
                        contents_structure.append((current_part_title, []))
                        current_part = []

                    in_questions_section = True
                    part_number += 1
                    current_part_title = heading_text
                    questions = []
                    current_question = []
                    question_title = None
                else:
                    # Start a new part
                    if current_part:
                        write_part(directory_name, part_number, current_part)
                        speakers = extract_and_clean_speakers("\n".join(current_part))
                        write_speakers_metadata(directory_name, part_number, "Part", speakers)
                        contents_structure.append((current_part_title, []))
                    part_number += 1
                    current_part = [str(element)]
                    current_part_title = heading_text
        else:
            # Non-heading elements
            if in_questions_section:
                current_question.append(str(element))
            else:
                current_part.append(str(element))
        i += 1

    # Process any remaining content
    if in_questions_section:
        if question_title and current_question:
            questions.append((question_title, current_question))
        if questions:
            process_questions(directory_name, part_number, questions)
            contents_structure.append(("QUESTIONS", [q[0] for q in questions]))
    if current_part:
        write_part(directory_name, part_number, current_part)
        speakers = extract_and_clean_speakers("\n".join(current_part))
        write_speakers_metadata(directory_name, part_number, "Part", speakers)
        contents_structure.append((current_part_title, []))

    # Write the contents structure
    with open(os.path.join(directory_name, "contents.html"), "w", encoding='utf-8') as file:
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

    logging.info(f"Total parts processed: {part_number}")
    return contents_structure  # Return this for debugging purposes

def extract_question_title(question):
    soup = BeautifulSoup(question, 'html.parser')
    title = soup.find('h3')
    if title:
        return title.text.strip()
    else:
        # If no h3, try to find the first paragraph or span
        first_p = soup.find('p')
        if first_p:
            return first_p.text.strip().split('\n')[0]  # Take only the first line
        first_span = soup.find('span')
        if first_span:
            return first_span.text.strip().split('\n')[0]  # Take only the first line
    return None  # Return None instead of "Untitled Question"

if __name__ == "__main__":
    filename = "content.html"
    split_html(filename)