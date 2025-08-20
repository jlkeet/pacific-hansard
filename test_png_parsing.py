#!/usr/bin/env python3

import sys
import os
sys.path.append('/Users/jacksonkeet/Pacific Hansard Development')

from pipelines_enhanced import parse_hansard_document, get_source_from_path, extract_date_from_path

# Test PNG file path
test_file = "/Users/jacksonkeet/Pacific Hansard Development/collections/Papua New Guinea/2025/August/19/part6.html"
metadata_file = "/Users/jacksonkeet/Pacific Hansard Development/collections/Papua New Guinea/2025/August/19/part6_metadata.txt"

print("=== Testing PNG Path Parsing ===")
print(f"Test file: {test_file}")

# Test source extraction
source = get_source_from_path(test_file)
print(f"Extracted source: '{source}'")

# Test date extraction  
date = extract_date_from_path(test_file)
print(f"Extracted date: '{date}'")

# Test full parsing if metadata exists
if os.path.exists(metadata_file):
    with open(test_file, 'r') as f:
        html_content = f.read()
    with open(metadata_file, 'r') as f:
        metadata_content = f.read()
    
    print(f"\nMetadata content:\n{metadata_content}")
    
    parsed_data = parse_hansard_document(html_content, metadata_content, test_file)
    print(f"\nParsed data:")
    for key, value in parsed_data.items():
        if key == 'content':
            print(f"  {key}: {value[:100]}..." if len(str(value)) > 100 else f"  {key}: {value}")
        else:
            print(f"  {key}: {value}")
else:
    print(f"Metadata file not found: {metadata_file}")