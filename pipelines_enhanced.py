import re
from bs4 import BeautifulSoup
import json
from datetime import datetime
import mysql.connector
import pysolr
import os
import time
import uuid
from db_config import get_db_config, get_solr_url

def parse_hansard_document(html_content, metadata_content, file_path):
    # Parse HTML
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Extract title (keeping the previous title extraction logic)
    title = None
    title_tag = soup.find('title')
    if title_tag and 'Hansard Oral Question' in title_tag.text:
        title = title_tag.text.strip()
    if not title:
        h3_tag = soup.find('h3')
        if h3_tag:
            title = h3_tag.text.strip()
    if not title:
        title = title_tag.text.strip()
    if not title:
        title = "Untitled Document"
    
    # Extract date from file path
    date = extract_date_from_path(file_path)
    
    # Append date to Oral Question titles
    if 'Hansard Oral Question' in title and date:
        title = f"{title} - {date}"
    
    # Extract content - preserve HTML structure for Fiji
    source = get_source_from_path(file_path)
    
    if source == 'Fiji':
        # For Fiji, extract the body HTML content
        body = soup.find('body')
        if body:
            # Remove the title from the content if it exists
            h3 = body.find('h3')
            if h3:
                h3.extract()
            
            # Get the inner HTML
            content = str(body).replace('<body>', '').replace('</body>', '').strip()
        else:
            content = html_content
    else:
        # For other sources, use plain text extraction
        content = soup.get_text(separator=' ', strip=True)
    
    # Parse metadata
    speakers = metadata_content.strip().split('\n')[1:]  # Skip the first line
    speaker1 = speakers[0].split(': ')[1] if len(speakers) > 0 else None
    speaker2 = speakers[1].split(': ')[1] if len(speakers) > 1 else None
    

    new_id = str(uuid.uuid4())

    # Create JSON structure
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
    # Assuming that the structure is /app/collections/{source}/...
    parts = file_path.split(os.sep)
    try:
        source = parts[3]  # Index 3 assumes /app/collections/{source}/...
        return source
    except IndexError:
        return "Unknown Source"

def extract_date_from_path(file_path):
    # Split the path and extract relevant parts
    path_parts = file_path.split(os.sep)
    try:
        # Debug: print path structure if we get index error
        if len(path_parts) < 4:
            print(f"Path too short: {file_path} has only {len(path_parts)} parts: {path_parts}")
            return None
            
        year = int(path_parts[-4])  # Assuming year is 4 levels up from the filename
        month = path_parts[-3]  # Month name
        day = int(path_parts[-2])  # Day of the month
        
        # Convert month name to number - handle both full and abbreviated month names
        month_mappings = {
            'January': 1, 'Jan': 1,
            'February': 2, 'Feb': 2,
            'March': 3, 'Mar': 3,
            'April': 4, 'Apr': 4,
            'May': 5,
            'June': 6, 'Jun': 6,
            'July': 7, 'Jul': 7,
            'August': 8, 'Aug': 8,
            'September': 9, 'Sep': 9, 'Sept': 9,
            'October': 10, 'Oct': 10,
            'November': 11, 'Nov': 11,
            'December': 12, 'Dec': 12
        }
        
        month_num = month_mappings.get(month)
        if month_num is None:
            # Try parsing with strptime as fallback
            month_num = datetime.strptime(month, '%B').month
        
        # Create a date object
        date = datetime(year, month_num, day)
        
        # Return formatted date string
        return date.strftime('%Y-%m-%d')
    except (ValueError, IndexError, KeyError) as e:
        print(f"Could not extract date from path: {file_path} - Error: {str(e)}")
        return None

def create_mysql_table():
    connection = None
    cursor = None
    try:
        db_config = get_db_config()
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor()
        
        # First, create the table if it doesn't exist
        create_table_query = """
        CREATE TABLE IF NOT EXISTS pacific_hansard_db (
            id INT AUTO_INCREMENT PRIMARY KEY,
            title VARCHAR(255),
            document_type VARCHAR(50),
            date DATE,
            source VARCHAR(100),
            speaker VARCHAR(100),
            speaker2 VARCHAR(100),
            content MEDIUMTEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            new_id VARCHAR(255)
        )
        """
        cursor.execute(create_table_query)
        
        # Then, check if the 'order' column exists, and add it if it doesn't
        cursor.execute("SHOW COLUMNS FROM pacific_hansard_db LIKE 'order'")
        result = cursor.fetchone()
        if not result:
            add_column_query = "ALTER TABLE pacific_hansard_db ADD COLUMN `order` INT"
            cursor.execute(add_column_query)
            print("Added 'order' column to the table")
        
        # Check if content column is MEDIUMTEXT
        cursor.execute("SHOW COLUMNS FROM pacific_hansard_db WHERE Field = 'content'")
        result = cursor.fetchone()
        if result and result[1] != 'mediumtext':
            alter_query = "ALTER TABLE pacific_hansard_db MODIFY COLUMN content MEDIUMTEXT"
            cursor.execute(alter_query)
            print("Updated content column to MEDIUMTEXT")
        
        print("Table structure is up to date")
    except mysql.connector.Error as error:
        print(f"Failed to update table in MySQL: {error}")
    finally:
        if connection and connection.is_connected():
            if cursor:
                cursor.close()
            connection.close()


def insert_into_mysql(data):
    try:
        from db_config import get_db_config
        db_config = get_db_config()
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor()
        
        # Check if 'order' column exists
        cursor.execute("SHOW COLUMNS FROM pacific_hansard_db LIKE 'order'")
        order_column_exists = cursor.fetchone() is not None
        
        if order_column_exists:
            insert_query = """
            INSERT INTO pacific_hansard_db 
            (title, document_type, date, source, speaker, speaker2, content, new_id, `order`) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            values = (
                data['title'], data['document_type'], data['date'], 
                data['source'], data['speaker'], data['speaker2'], data['content'], 
                data['new_id'], data.get('order', 9999)  # Use a high default order if not specified
            )
        else:
            insert_query = """
            INSERT INTO pacific_hansard_db 
            (title, document_type, date, source, speaker, speaker2, content, new_id) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            values = (
                data['title'], data['document_type'], data['date'], 
                data['source'], data['speaker'], data['speaker2'], data['content'], 
                data['new_id']
            )
        
        cursor.execute(insert_query, values)
        connection.commit()
        print("Record inserted successfully into MySQL")
    except mysql.connector.Error as error:
        print(f"Failed to insert into MySQL table: {error}")
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

            

def index_in_solr(data):
    solr = pysolr.Solr(get_solr_url(), always_commit=True)
    try:
        # For Solr, we need plain text, so extract it if content contains HTML
        if data['source'] == 'Fiji' and '<' in data['content']:
            soup = BeautifulSoup(data['content'], 'html.parser')
            plain_text_content = soup.get_text(separator=' ', strip=True)
            # Create a copy of data for Solr with plain text
            solr_data = data.copy()
            solr_data['content'] = plain_text_content
        else:
            solr_data = data
            
        # Ensure date is not None before indexing
        if solr_data['date'] is None:
            solr_data['date'] = '2010-01-01'
        solr.add([solr_data])
        print(f"Document indexed successfully in Solr: {data['title']}")
    except pysolr.SolrError as error:
        print(f"Failed to index document in Solr: {error}")
        print(f"Problematic document: {data}")


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
        contents_order = parse_contents_html(root)
        for filename in files:
            if filename.endswith(".html") and filename != "contents.html":
                html_file = os.path.join(root, filename)
                metadata_file = os.path.join(root, filename.replace('.html', '_metadata.txt'))
                if os.path.exists(metadata_file):
                    parsed_data = process_document(html_file, metadata_file)
                    if parsed_data:
                        # Assign order based on the title match in contents_order
                        parsed_data['order'] = contents_order.get(parsed_data['title'], 9999)
                        insert_into_mysql(parsed_data)
                        index_in_solr(parsed_data)
                else:
                    print(f"Metadata file not found for {filename}")

def parse_contents_html(directory):
    contents_file = os.path.join(directory, 'contents.html')
    order_dict = {}
    try:
        with open(contents_file, 'r', encoding='utf-8') as f:
            soup = BeautifulSoup(f.read(), 'html.parser')
        
        items = soup.find_all(['h2', 'li'])  # Find all h2 and li elements
        order = 0
        for item in items:
            if item.name == 'h2':
                # Main sections are h2, increase order significantly
                order += 100
            else:
                # List items are individual documents
                order += 1
            order_dict[item.text.strip()] = order
    except FileNotFoundError:
        print(f"Contents file not found in {directory}")
    return order_dict

if __name__ == "__main__":
    # Wait for MySQL and Solr to be ready
    time.sleep(20)  # Adjust this as needed
    
    # Create MySQL table if it doesn't exist
    create_mysql_table()
    
    # Process all documents
    process_all_documents("/app/collections/")