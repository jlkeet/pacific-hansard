#!/usr/bin/env python3
"""
Cook Islands Hansard Converter
Splits HTML hansards into parts for processing
Simple wrapper for the integrated converter
"""

import sys
import os

# Import the integrated converter (using the actual filename)
from CI_hansard_converter_integrated import split_html as integrated_split_html

def split_html(html_path):
    """Split HTML hansard into parts - wrapper function"""
    return integrated_split_html(html_path)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python CI_hansard_converter.py <html_file>")
        sys.exit(1)
    
    html_file = sys.argv[1]
    if not os.path.exists(html_file):
        print(f"Error: File {html_file} not found")
        sys.exit(1)
    
    result = split_html(html_file)
    if result:
        print(f"Successfully processed {html_file}")
    else:
        print(f"Failed to process {html_file}")
        sys.exit(1)