import os
import json
import mysql.connector
import pysolr
from datetime import datetime
import hashlib
from db_config import get_db_config, get_solr_url
from pipelines_enhanced import (
    parse_hansard_document, 
    get_source_from_path,
    extract_date_from_path,
    create_mysql_table,
    insert_into_mysql,
    index_in_solr
)

def get_file_hash(filepath):
    """Generate a hash of the file content to detect changes"""
    with open(filepath, 'rb') as f:
        return hashlib.md5(f.read()).hexdigest()

def is_already_indexed(connection, file_path, file_hash):
    """Check if this file has already been indexed"""
    try:
        cursor = connection.cursor()
        cursor.execute(
            "SELECT file_hash FROM indexed_files WHERE file_path = %s",
            (file_path,)
        )
        result = cursor.fetchone()
        
        if result and result[0] == file_hash:
            return True  # File unchanged
        return False
    except:
        return False
    finally:
        cursor.close()

def mark_as_indexed(connection, file_path, file_hash):
    """Mark a file as indexed"""
    try:
        cursor = connection.cursor()
        cursor.execute("""
            INSERT INTO indexed_files (file_path, file_hash, indexed_at) 
            VALUES (%s, %s, NOW())
            ON DUPLICATE KEY UPDATE 
            file_hash = VALUES(file_hash),
            indexed_at = NOW()
        """, (file_path, file_hash))
        connection.commit()
    except Exception as e:
        print(f"Error marking file as indexed: {e}")
    finally:
        cursor.close()

def create_tracking_table(connection):
    """Create table to track indexed files"""
    try:
        cursor = connection.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS indexed_files (
                file_path VARCHAR(500) PRIMARY KEY,
                file_hash VARCHAR(32),
                indexed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        connection.commit()
        print("Tracking table ready")
    except Exception as e:
        print(f"Error creating tracking table: {e}")
    finally:
        cursor.close()

def smart_index_documents(directory):
    """Only index new or changed documents"""
    
    # Get database configuration
    from db_config import get_db_config
    db_config = get_db_config()
    
    # Setup database connection
    connection = mysql.connector.connect(**db_config)
    
    create_tracking_table(connection)
    
    indexed_count = 0
    skipped_count = 0
    
    for root, dirs, files in os.walk(directory):
        for filename in files:
            if filename.endswith(".html") and filename != "contents.html":
                html_file = os.path.join(root, filename)
                metadata_file = os.path.join(root, filename.replace('.html', '_metadata.txt'))
                
                if os.path.exists(metadata_file):
                    # Check if already indexed
                    file_hash = get_file_hash(html_file)
                    
                    if is_already_indexed(connection, html_file, file_hash):
                        skipped_count += 1
                        continue
                    
                    # Mark as indexed FIRST to prevent infinite reprocessing
                    mark_as_indexed(connection, html_file, file_hash)
                    
                    # Process and index the document
                    try:
                        with open(html_file, 'r', encoding='utf-8') as f:
                            html_content = f.read()
                        with open(metadata_file, 'r', encoding='utf-8') as f:
                            metadata_content = f.read()
                        
                        parsed_data = parse_hansard_document(
                            html_content, metadata_content, html_file
                        )
                        
                        if parsed_data:
                            insert_into_mysql(parsed_data)
                            index_in_solr(parsed_data)
                            indexed_count += 1
                            print(f"Indexed: {filename}")
                        else:
                            print(f"No data parsed for: {filename}")
                    
                    except Exception as e:
                        print(f"Error processing {filename}: {e}")
                        # File is already marked as indexed, so it won't be retried
    
    connection.close()
    
    print(f"\nIndexing complete!")
    print(f"New documents indexed: {indexed_count}")
    print(f"Documents already indexed: {skipped_count}")

if __name__ == "__main__":
    import time
    print("Starting smart indexing...")
    
    # Wait for services to be ready
    time.sleep(10)
    
    # Create tables
    create_mysql_table()
    
    # Index only new/changed documents
    if os.path.exists("/app/collections/"):
        smart_index_documents("/app/collections/")
    else:
        print("No collections directory found")