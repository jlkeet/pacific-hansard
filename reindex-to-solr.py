#!/usr/bin/env python3
"""
Re-index existing MySQL documents to Solr
"""
import mysql.connector
import pysolr
from db_config import get_db_config, get_solr_url
import sys
from datetime import datetime

def reindex_to_solr():
    # Get database configuration
    db_config = get_db_config()
    solr_url = get_solr_url()
    
    print(f"Connecting to MySQL...")
    connection = mysql.connector.connect(**db_config)
    cursor = connection.cursor(dictionary=True)
    
    print(f"Connecting to Solr at: {solr_url}")
    solr = pysolr.Solr(solr_url, always_commit=True, timeout=30)
    
    # Test Solr connection
    try:
        solr.ping()
        print("✓ Solr connection successful")
    except Exception as e:
        print(f"✗ Solr connection failed: {e}")
        sys.exit(1)
    
    # Get all documents from MySQL
    print("\nFetching documents from MySQL...")
    cursor.execute("""
        SELECT new_id, title, date, document_type, source, 
               content, speaker, speaker2 
        FROM pacific_hansard_db
    """)
    
    documents = []
    for row in cursor:
        doc = {
            'id': row['new_id'],
            'new_id': row['new_id'],
            'title': row['title'],
            'date': row['date'].isoformat() if row['date'] else '2010-01-01',
            'document_type': row['document_type'],
            'source': row['source'],
            'content': row['content'],
            'speaker': row['speaker'],
            'speaker2': row['speaker2']
        }
        documents.append(doc)
    
    print(f"Found {len(documents)} documents to index")
    
    # Index in batches
    batch_size = 100
    total_indexed = 0
    
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
                except Exception as doc_error:
                    print(f"Failed to index document {doc['new_id']}: {doc_error}")
    
    print(f"\n✓ Indexing complete! {total_indexed} documents indexed to Solr")
    
    # Verify
    results = solr.search('*:*', rows=0)
    print(f"Verification: Solr now contains {results.hits} documents")
    
    cursor.close()
    connection.close()

if __name__ == "__main__":
    reindex_to_solr()