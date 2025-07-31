#!/usr/bin/env python3
"""
Re-index all documents from MySQL to Solr with speaker fields
"""
import mysql.connector
import pysolr
import os
from datetime import datetime

def reindex_to_solr():
    # Database connection
    connection = mysql.connector.connect(
        host=os.environ.get('DB_HOST', 'mysql'),
        database=os.environ.get('DB_NAME', 'pacific_hansard_db'),
        user=os.environ.get('DB_USER', 'hansard_user'),
        password=os.environ.get('DB_PASSWORD', 'test_pass')
    )
    
    # Solr connection
    solr = pysolr.Solr(os.environ.get('SOLR_URL', 'http://solr:8983/solr/hansard_core'), always_commit=True)
    
    cursor = connection.cursor(dictionary=True)
    
    # First, clear the existing index
    print("Clearing existing Solr index...")
    solr.delete(q='*:*')
    
    # Get all documents from MySQL
    print("Fetching documents from MySQL...")
    cursor.execute("SELECT * FROM pacific_hansard_db")
    documents = cursor.fetchall()
    
    print(f"Found {len(documents)} documents to index")
    
    # Check how many have speakers
    speaker_count = sum(1 for doc in documents if doc['speaker'] and doc['speaker'] != 'No speakers identified')
    print(f"Documents with speakers: {speaker_count}")
    
    # Prepare documents for Solr
    solr_docs = []
    for doc in documents:
        solr_doc = {
            'id': str(doc['id']),
            'title': doc['title'],
            'document_type': doc['document_type'],
            'source': doc['source'],
            'content': doc['content'],
            'new_id': doc['new_id']
        }
        
        # Add date if present
        if doc['date']:
            solr_doc['date'] = doc['date'].strftime('%Y-%m-%dT%H:%M:%SZ')
        
        # Add speakers if present
        if doc['speaker'] and doc['speaker'] != 'No speakers identified':
            solr_doc['speaker'] = doc['speaker']
            
        if doc['speaker2'] and doc['speaker2'] != 'No speakers identified':
            solr_doc['speaker2'] = doc['speaker2']
            
        solr_docs.append(solr_doc)
    
    # Index in batches
    batch_size = 50
    total_indexed = 0
    
    print("Indexing documents to Solr...")
    for i in range(0, len(solr_docs), batch_size):
        batch = solr_docs[i:i + batch_size]
        try:
            solr.add(batch)
            total_indexed += len(batch)
            print(f"Indexed {total_indexed}/{len(solr_docs)} documents...")
        except Exception as e:
            print(f"Error indexing batch: {e}")
    
    print(f"\nIndexing complete! Total documents indexed: {total_indexed}")
    
    # Verify speaker facets
    print("\nVerifying speaker facets...")
    results = solr.search('*:*', **{
        'facet': 'true',
        'facet.field': ['speaker', 'speaker2'],
        'facet.mincount': 1,
        'rows': 0
    })
    
    if results.facets:
        speaker_facet = results.facets['facet_fields'].get('speaker', [])
        speaker2_facet = results.facets['facet_fields'].get('speaker2', [])
        
        # Facets come as [name, count, name, count, ...]
        speaker_names = [speaker_facet[i] for i in range(0, len(speaker_facet), 2)]
        speaker2_names = [speaker2_facet[i] for i in range(0, len(speaker2_facet), 2)]
        
        print(f"Unique speakers in 'speaker' field: {len(speaker_names)}")
        print(f"Unique speakers in 'speaker2' field: {len(speaker2_names)}")
        
        if speaker_names:
            print("\nSample speakers:")
            for speaker in speaker_names[:5]:
                print(f"  - {speaker}")
    
    cursor.close()
    connection.close()

if __name__ == "__main__":
    reindex_to_solr()