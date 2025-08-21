#!/usr/bin/env python3
"""Debug search issues"""

import pysolr
import json

# Connect to Solr
solr = pysolr.Solr('http://localhost:8983/solr/hansard_core')

# Test the exact query that's failing
query = 'content:("Minister")'
print(f"Testing query: {query}")

try:
    results = solr.search(query, rows=1, fl='*,score', sort='score desc')
    print(f"Found {len(results)} results")
    
    for i, doc in enumerate(results):
        print(f"\nDocument {i}:")
        print(json.dumps(dict(doc), indent=2, default=str))
        
        print(f"\nField types:")
        for key, value in doc.items():
            print(f"  {key}: {type(value)} = {value}")
            
except Exception as e:
    print(f"Error: {e}")