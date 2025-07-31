import sqlite3
import os
import json
from datetime import datetime
import time
import uuid
from bs4 import BeautifulSoup

# Create SQLite database
def create_sqlite_table():
    try:
        conn = sqlite3.connect('/data/pacific_hansard.db')
        cursor = conn.cursor()
        
        create_table_query = """
        CREATE TABLE IF NOT EXISTS pacific_hansard_db (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            document_type TEXT,
            date TEXT,
            source TEXT,
            speaker TEXT,
            speaker2 TEXT,
            content TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            new_id TEXT,
            order_num INTEGER
        )
        """
        cursor.execute(create_table_query)
        conn.commit()
        print("SQLite table created/verified")
        
    except sqlite3.Error as error:
        print(f"Failed to create SQLite table: {error}")
    finally:
        if conn:
            conn.close()

def insert_into_sqlite(data):
    try:
        conn = sqlite3.connect('/data/pacific_hansard.db')
        cursor = conn.cursor()
        
        insert_query = """
        INSERT INTO pacific_hansard_db 
        (title, document_type, date, source, speaker, speaker2, content, new_id, order_num) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        values = (
            data['title'], data['document_type'], data['date'], 
            data['source'], data['speaker'], data['speaker2'], data['content'], 
            data['new_id'], data.get('order', 9999)
        )
        
        cursor.execute(insert_query, values)
        conn.commit()
        print("Record inserted successfully into SQLite")
        
    except sqlite3.Error as error:
        print(f"Failed to insert into SQLite: {error}")
    finally:
        if conn:
            conn.close()

# Parse functions remain the same
def parse_hansard_document(html_content, metadata_content, file_path):
    soup = BeautifulSoup(html_content, 'html.parser')
    
    title = None
    title_tag = soup.find('title')
    if title_tag and 'Hansard Oral Question' in title_tag.text:
        title = title_tag.text.strip()
    if not title:
        h3_tag = soup.find('h3')
        if h3_tag:
            title = h3_tag.text.strip()
    if not title and title_tag:
        title = title_tag.text.strip()
    if not title:
        title = "Untitled Document"
    
    date = extract_date_from_path(file_path)
    
    if 'Hansard Oral Question' in title and date:
        title = f"{title} - {date}"
    
    content = soup.get_text(separator=' ', strip=True)
    
    speakers = metadata_content.strip().split('\n')[1:]
    speaker1 = speakers[0].split(': ')[1] if len(speakers) > 0 else None
    speaker2 = speakers[1].split(': ')[1] if len(speakers) > 1 else None
    
    new_id = str(uuid.uuid4())
    source = get_source_from_path(file_path)
    
    hansard_json = {
        "title": title,
        "document_type": "Oral Question" if 'Oral Question' in title else "Hansard Document",
        "date": date,
        "source": source,
        "speaker": speaker1,
        "speaker2": speaker2,
        "content": content,
        "new_id": new_id
    }
    
    return hansard_json

def get_source_from_path(file_path):
    parts = file_path.split(os.sep)
    try:
        collections_index = parts.index('collections')
        if collections_index + 1 < len(parts):
            return parts[collections_index + 1]
    except ValueError:
        pass
    return "Unknown Source"

def extract_date_from_path(file_path):
    path_parts = file_path.split(os.sep)
    try:
        year = int(path_parts[-4])
        month = path_parts[-3]
        day = int(path_parts[-2])
        
        month_num = datetime.strptime(month, '%B').month
        date = datetime(year, month_num, day)
        
        return date.strftime('%Y-%m-%d')
    except (ValueError, IndexError):
        print(f"Could not extract date from path: {file_path}")
        return None

def process_document(html_file_path, metadata_file_path):
    try:
        with open(html_file_path, 'r', encoding='utf-8') as html_file:
            html_content = html_file.read()

        with open(metadata_file_path, 'r', encoding='utf-8') as metadata_file:
            metadata_content = metadata_file.read()

        parsed_data = parse_hansard_document(html_content, metadata_content, html_file_path)
        return parsed_data
    except FileNotFoundError:
        print(f"File not found: {html_file_path} or {metadata_file_path}")
    except Exception as e:
        print(f"Error processing {html_file_path}: {str(e)}")
    return None

def process_all_documents(directory):
    for root, dirs, files in os.walk(directory):
        for filename in files:
            if filename.endswith(".html") and filename != "contents.html":
                html_file = os.path.join(root, filename)
                metadata_file = os.path.join(root, filename.replace('.html', '_metadata.txt'))
                if os.path.exists(metadata_file):
                    parsed_data = process_document(html_file, metadata_file)
                    if parsed_data:
                        insert_into_sqlite(parsed_data)
                else:
                    print(f"Metadata file not found for {filename}")

if __name__ == "__main__":
    # Create directory for database if it doesn't exist
    os.makedirs('/data', exist_ok=True)
    
    # Create SQLite table
    create_sqlite_table()
    
    # Process documents if collections directory exists
    if os.path.exists("/app/collections/"):
        process_all_documents("/app/collections/")
    else:
        print("No collections directory found - web interface only mode")