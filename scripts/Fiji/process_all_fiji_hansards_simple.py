#!/usr/bin/env python3
"""
Process all Fiji hansards - simple version
"""
import os
import subprocess
import re

def process_all():
    # Get all HTML files
    html_files = []
    for f in os.listdir('.'):
        if f.endswith('.html') and 'hansard' in f.lower():
            html_files.append(f)
    
    print(f"Found {len(html_files)} HTML files to process")
    
    processed = 0
    for html_file in sorted(html_files):
        print(f"\nProcessing: {html_file}")
        try:
            # Use python3 explicitly
            result = subprocess.run(['python3', 'fiji-hansard-converter-integrated.py', html_file], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                print(f"  ✓ Success")
                processed += 1
            else:
                print(f"  ✗ Error: {result.stderr}")
        except Exception as e:
            print(f"  ✗ Exception: {str(e)}")
    
    print(f"\nProcessed {processed}/{len(html_files)} files successfully")

if __name__ == "__main__":
    process_all()