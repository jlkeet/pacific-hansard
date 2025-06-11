import re
import os
from bs4 import BeautifulSoup

def normalize_name(name):
    # Remove all spaces and convert to uppercase
    return ''.join(name.split()).upper()

def extract_and_clean_speakers(text):
    speakers = []
    seen = set()
    # Pattern to capture HON. followed by titles and names
    pattern = r'HON\.\s+((?:PROFESSOR|DR\.|MR\.|MRS\.|MS\.)?\s*[A-Z][A-Z.\s]+(?:\s[A-Z][a-z]+)*)'
    
    matches = re.findall(pattern, text)
    for match in matches:
        name = match.strip().rstrip('.')  # Remove trailing period if present
        normalized_name = normalize_name(name)
        if normalized_name and normalized_name not in seen:
            seen.add(normalized_name)
            speakers.append(name)  # Add the original name, not the normalized version
    
    return speakers

def speaker_str(speakers):
    return "\n".join([f"Speaker {i+1}: {speaker}" for i, speaker in enumerate(speakers)])

def write_speakers_metadata(directory, part_number, part_type, speakers, question_number=None):
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

def split_questions(content):
    soup = BeautifulSoup(content, 'html.parser')
    questions = []
    current_question = []
    
    for element in soup.find_all(['h3', 'p']):
        if element.name == 'h3' or (element.name == 'p' and element.find('span') and '(Question No.' in element.text):
            if current_question:
                questions.append('\n'.join(current_question))
            current_question = [str(element)]
        else:
            current_question.append(str(element))
    
    if current_question:
        questions.append('\n'.join(current_question))
    
    return questions

def split_html(filename):
    date_pattern = re.compile(r'\d{1,2}\w{2}-[A-Z][a-z]+-\d{4}')
    match = date_pattern.search(filename)
    date_str = match.group() if match else "Unknown-Date"
    
    directory_name = f"Hansard_{date_str}"
    os.makedirs(directory_name, exist_ok=True)

    with open(filename, "r", encoding='utf-8') as file:
        soup = BeautifulSoup(file, 'html.parser')

    all_divs = soup.find_all('div')

    contents_filename = os.path.join(directory_name, "contents.html")
    with open(contents_filename, "w", encoding='utf-8') as file:
        file.write("<h2>Contents</h2>\n<ul>")
        
        current_part = []
        part_number = 0
        in_questions_section = False
        oral_questions = []
        written_questions = []
        current_question_type = None
        contents_structure = []
        current_part_title = ""

        for div in all_divs:
            span = div.find('span', {'style': lambda value: value and 'TimesNewRomanPS-BoldMT' and 'font-size:12px' in value or 'Times New Roman,Bold' and 'font-size:12px' in value})
            
            if span and span.text.strip().isupper():
                if current_part:
                    if in_questions_section:
                        oral_titles, written_titles = process_questions(directory_name, part_number, oral_questions, written_questions)
                        contents_structure.append(("QUESTIONS", oral_titles, written_titles))
                        in_questions_section = False
                    else:
                        write_part(directory_name, part_number, current_part)
                        speakers = extract_and_clean_speakers("\n".join(current_part))
                        write_speakers_metadata(directory_name, part_number, "Part", speakers)
                        contents_structure.append((current_part_title, []))
                
                part_number += 1
                current_part = [f"<h3>{span.text.strip()}</h3>"]
                current_part_title = span.text.strip()
                
                if current_part_title == "QUESTIONS":
                    in_questions_section = True
                    oral_questions = []
                    written_questions = []
                    current_question_type = None
            else:
                if in_questions_section:
                    if "Oral Questions" in div.text:
                        current_question_type = "oral"
                        oral_questions.append(str(div))
                    elif "Written Question" in div.text or "Written Questions" in div.text:
                        current_question_type = "written"
                        written_questions.append(str(div))
                    else:
                        if current_question_type == "oral":
                            oral_questions.append(str(div))
                        elif current_question_type == "written":
                            written_questions.append(str(div))
                else:
                    current_part.append(str(div))

        # Process the last part
        if in_questions_section:
            oral_titles, written_titles = process_questions(directory_name, part_number, oral_questions, written_questions)
            contents_structure.append(("QUESTIONS", oral_titles, written_titles))
        elif current_part:
            write_part(directory_name, part_number, current_part)
            speakers = extract_and_clean_speakers("\n".join(current_part))
            write_speakers_metadata(directory_name, part_number, "Part", speakers)
            contents_structure.append((current_part_title, []))

        # Write the contents structure
    with open(contents_filename, "w", encoding='utf-8') as file:
        file.write("<h2>Contents</h2>\n<ul>")
        for item in contents_structure:
            if item[0] == "QUESTIONS":
                file.write(f"<li>QUESTIONS<ul>")
                if item[1]:  # Oral Questions
                    file.write("<li>Oral Questions<ul>")
                    for title in item[1]:
                        file.write(f"<li>{title}</li>")
                    file.write("</ul></li>")
                if item[2]:  # Written Questions
                    file.write("<li>Written Questions<ul>")
                    for title in item[2]:
                        file.write(f"<li>{title}</li>")
                    file.write("</ul></li>")
                file.write("</ul></li>")
            else:
                file.write(f"<li>{item[0]}</li>")
        file.write("</ul>")

    return contents_structure  # Return this for debugging purposes

def process_questions(directory, part_number, oral_questions, written_questions):
    questions_dir = os.path.join(directory, f"part{part_number}_questions")
    os.makedirs(questions_dir, exist_ok=True)
    
    oral_titles = []
    written_titles = []
    
    if oral_questions:
        oral_content = clean_content("\n".join(oral_questions))
        oral_split = split_questions(oral_content)
        for i, question in enumerate(oral_split[1:], 1):  # Start from the second item (index 1)
            title = extract_question_title(question)
            if title and title != "Oral Questions":
                oral_titles.append(title)
                write_question(questions_dir, "oral", i, question)
                speakers = extract_and_clean_speakers(question)
                write_speakers_metadata(directory, part_number, "Oral", speakers, i)
    
    if written_questions:
        written_content = clean_content("\n".join(written_questions))
        written_split = split_questions(written_content)
        if not written_split:  # If split_questions failed to split, treat entire content as one question
            written_split = [written_content]
        for i, question in enumerate(written_split, 1):
            title = extract_question_title(question)
            if title and title != "Written Questions" and title != "Written Question":
                written_titles.append(title)
                write_question(questions_dir, "written", i, question)
                speakers = extract_and_clean_speakers(question)
                write_speakers_metadata(directory, part_number, "Written", speakers, i)
    
    return oral_titles, written_titles

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


def write_question(questions_dir, question_type, question_number, content):
    filename = os.path.join(questions_dir, f"{question_type}_question_{question_number}.html")
    
    # Process content to preserve formatting
    soup = BeautifulSoup(content, 'html.parser')
    formatted_content = ""
    for p in soup.find_all('p'):
        text = p.get_text(strip=True)
        if text.startswith(('(a)', '(b)', '(c)', '(d)', '(e)', '(f)')):
            formatted_content += f"<p style='margin-left: 20px;'>{text}</p>\n"
        else:
            formatted_content += f"<p>{text}</p>\n"
    
    with open(filename, "w", encoding='utf-8') as file:
        file.write(f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Hansard {question_type.capitalize()} Question {question_number}</title>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; padding: 20px; max-width: 800px; margin: 0 auto; }}
        h3 {{ color: #333; }}
        p {{ margin-bottom: 10px; }}
    </style>
</head>
<body>
{formatted_content}
</body>
</html>
        """)

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

if __name__ == "__main__":
    filename = "Final-DH-Tuesday-9th-February-2021v2.html"
    split_html(filename)