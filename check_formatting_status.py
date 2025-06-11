#!/usr/bin/env python3
"""Check the status of Fiji formatting improvements"""

import os
import glob
from bs4 import BeautifulSoup

def check_if_processed(file_path):
    """Check if a file has been processed with new formatting"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for new CSS styles that indicate processing
        indicators = [
            'speech-block',
            'speaker-name',
            'speech-content',
            'procedural',
            'line-height: 1.8',
            'max-width: 900px'
        ]
        
        return any(indicator in content for indicator in indicators)
    except Exception:
        return False

# Check all Fiji HTML files
fiji_dirs = [
    "/Users/jacksonkeet/Pacific Hansard Development/collections/Fiji",
    "/Users/jacksonkeet/Pacific Hansard Development/scripts/Fiji"
]

processed = 0
unprocessed = 0
total = 0

for directory in fiji_dirs:
    if os.path.exists(directory):
        html_files = glob.glob(os.path.join(directory, '**/*.html'), recursive=True)
        
        for file_path in html_files:
            if 'contents.html' in file_path or 'env/' in file_path:
                continue
            
            total += 1
            if check_if_processed(file_path):
                processed += 1
            else:
                unprocessed += 1
                if unprocessed <= 10:  # Show first 10 unprocessed files
                    print(f"Unprocessed: {file_path}")

print(f"\n=== Formatting Status Summary ===")
print(f"Total HTML files: {total}")
print(f"Successfully processed: {processed}")
print(f"Not processed: {unprocessed}")
print(f"Success rate: {(processed/total*100):.1f}%")

# Show a sample of processed files
print(f"\nSample of processed files:")
count = 0
for directory in fiji_dirs:
    if os.path.exists(directory):
        html_files = glob.glob(os.path.join(directory, '**/*.html'), recursive=True)
        for file_path in html_files:
            if 'contents.html' not in file_path and check_if_processed(file_path):
                print(f"✓ {file_path}")
                count += 1
                if count >= 5:
                    break
        if count >= 5:
            break