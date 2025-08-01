#!/usr/bin/env python3
"""
Manual re-index script to push MySQL documents to Solr
"""
import mysql.connector
import pysolr
from db_config import get_db_config, get_solr_url
import sys
from datetime import datetime
from bs4 import BeautifulSoup

def reindex_to_solr():
    # Get configurations
    db_config = get_db_config()
    solr_url = get_solr_url()
    
    print(f"Connecting to MySQL...")
    print(f"DB Config: {db_config['host']}:{db_config['port']}/{db_config['database']}")
    
    try:
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor(dictionary=True)
        print("✓ MySQL connection successful")
    except Exception as e:
        print(f"✗ MySQL connection failed: {e}")
        sys.exit(1)
    
    print(f"\nConnecting to Solr at: {solr_url}")
    solr = pysolr.Solr(solr_url, always_commit=True, timeout=30)
    
    # Test Solr connection
    try:
        solr.ping()
        print("✓ Solr connection successful")
    except Exception as e:
        print(f"✗ Solr connection failed: {e}")
        print("Make sure SOLR_URL environment variable is set correctly")
        sys.exit(1)
    
    # Clear existing Solr documents (optional)
    print("\nClearing existing Solr documents...")
    try:
        solr.delete(q='*:*')
        print("✓ Solr cleared")
    except Exception as e:
        print(f"Warning: Could not clear Solr: {e}")
    
    # Get all documents from MySQL
    print("\nFetching documents from MySQL...")
    cursor.execute("""
        SELECT new_id, title, date, document_type, source, 
               content, speaker, speaker2 
        FROM pacific_hansard_db
    """)
    
    documents = []
    for row in cursor:
        # Process content for Fiji documents
        content = row['content']
        if row['source'] == 'Fiji' and content and '<' in content:
            soup = BeautifulSoup(content, 'html.parser')
            content = soup.get_text(separator=' ', strip=True)
        
        doc = {
            'id': row['new_id'],
            'new_id': row['new_id'],
            'title': row['title'],
            'date': row['date'].isoformat() if row['date'] else '2010-01-01',
            'document_type': row['document_type'],
            'source': row['source'],
            'content': content,
            'speaker': row['speaker'],
            'speaker2': row['speaker2']
        }
        documents.append(doc)
    
    print(f"Found {len(documents)} documents to index")
    
    # Index in batches
    batch_size = 100
    total_indexed = 0
    failed_docs = []
    
    for i in range(0, len(documents), batch_size):
        batch = documents[i:i+batch_size]
        try:
            solr.add(batch)
            total_indexed += len(batch)
            print(f"Indexed {total_indexed}/{len(documents)} documents...")
        except Exception as e:
            print(f"Error indexing batch {i//batch_size + 1}: {e}")
            # Try indexing one by one to find problematic document
            for doc in batch:
                try:
                    solr.add([doc])
                    total_indexed += 1
                except Exception as doc_error:
                    print(f"Failed to index document {doc['new_id']}: {doc_error}")
                    failed_docs.append(doc['new_id'])
    
    print(f"\n✓ Indexing complete!")
    print(f"Successfully indexed: {total_indexed} documents")
    if failed_docs:
        print(f"Failed documents: {len(failed_docs)}")
        print(f"Failed IDs: {', '.join(failed_docs[:10])}{'...' if len(failed_docs) > 10 else ''}")
    
    # Verify
    results = solr.search('*:*', rows=0)
    print(f"\nVerification: Solr now contains {results.hits} documents")
    
    cursor.close()
    connection.close()

if __name__ == "__main__":
    reindex_to_solr()