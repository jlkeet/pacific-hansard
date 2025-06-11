#!/usr/bin/env python3
"""
Convert Fiji Parliament PDF hansards to HTML using pdfminer
Same method as Cook Islands hansards which produces good results
"""

import os
import logging
from datetime import datetime
from pdfminer.high_level import extract_text_to_fp
from pdfminer.layout import LAParams
from io import StringIO

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def pdf_to_html(pdf_path, html_path):
    """Convert PDF to HTML using pdfminer - same as Cook Islands method"""
    try:
        output_string = StringIO()
        with open(pdf_path, 'rb') as fin:
            extract_text_to_fp(fin, output_string, laparams=LAParams(), output_type='html', codec=None)
        
        with open(html_path, 'w', encoding='utf-8') as fout:
            fout.write(output_string.getvalue())
        
        return True
    except Exception as e:
        logging.error(f"Error converting {pdf_path}: {str(e)}")
        return False

def convert_all_pdfs():
    """Convert all PDFs in pdf_hansards to HTML in html_hansards"""
    pdf_dir = 'pdf_hansards'
    html_dir = 'html_hansards'
    
    if not os.path.exists(pdf_dir):
        logging.error(f"PDF directory {pdf_dir} not found")
        return 0
    
    # Create output directory
    os.makedirs(html_dir, exist_ok=True)
    
    converted_count = 0
    pdf_files = [f for f in os.listdir(pdf_dir) if f.endswith('.pdf')]
    
    logging.info(f"Found {len(pdf_files)} PDF files to convert")
    
    for filename in pdf_files:
        pdf_path = os.path.join(pdf_dir, filename)
        html_filename = filename.replace('.pdf', '.html')
        html_path = os.path.join(html_dir, html_filename)
        
        logging.info(f"Converting: {filename}")
        
        if pdf_to_html(pdf_path, html_path):
            logging.info(f"  ✓ Successfully converted {filename}")
            converted_count += 1
        else:
            logging.error(f"  ✗ Failed to convert {filename}")
    
    logging.info(f"\nConversion complete: {converted_count}/{len(pdf_files)} PDFs converted")
    return converted_count

if __name__ == "__main__":
    convert_all_pdfs()