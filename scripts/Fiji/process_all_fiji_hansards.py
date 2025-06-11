#!/usr/bin/env python3
"""
Process all Fiji hansards
Converts PDFs to HTML and processes them to collections structure
"""

import os
import logging
from datetime import datetime
from pdfminer.high_level import extract_text_to_fp
from pdfminer.layout import LAParams
from io import StringIO
import subprocess

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'logs/fiji_processing_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)

# Create directories
os.makedirs('logs', exist_ok=True)
os.makedirs('html_hansards', exist_ok=True)

def pdf_to_html(pdf_path, html_path):
    """Convert PDF to HTML using pdfminer"""
    try:
        output_string = StringIO()
        with open(pdf_path, 'rb') as fin:
            extract_text_to_fp(fin, output_string, laparams=LAParams(), 
                             output_type='html', codec=None)
        
        with open(html_path, 'w', encoding='utf-8') as fout:
            fout.write(output_string.getvalue())
        
        logging.info(f"Converted {pdf_path} to {html_path}")
        return True
    except Exception as e:
        logging.error(f"Error converting {pdf_path}: {str(e)}")
        return False

def process_fiji_hansards():
    """Process all Fiji hansards"""
    
    # List all PDF files
    pdf_files = []
    
    # Check current directory
    for f in os.listdir('.'):
        if f.endswith('.pdf') and 'hansard' in f.lower():
            pdf_files.append(f)
    
    # Check pdf_hansards directory if it exists
    if os.path.exists('pdf_hansards'):
        for f in os.listdir('pdf_hansards'):
            if f.endswith('.pdf'):
                pdf_files.append(os.path.join('pdf_hansards', f))
    
    logging.info(f"Found {len(pdf_files)} PDF files to process")
    
    # Convert PDFs to HTML
    html_files = []
    for pdf_file in pdf_files:
        base_name = os.path.basename(pdf_file)
        html_name = base_name.replace('.pdf', '.html')
        html_path = os.path.join('html_hansards', html_name)
        
        # Skip if already converted
        if os.path.exists(html_path):
            logging.info(f"HTML already exists: {html_name}")
            html_files.append(html_path)
            continue
        
        if pdf_to_html(pdf_file, html_path):
            html_files.append(html_path)
    
    logging.info(f"Have {len(html_files)} HTML files ready for processing")
    
    # Process HTML files with the integrated converter
    processed_count = 0
    for html_file in html_files:
        try:
            cmd = ['python', 'fiji-hansard-converter-integrated.py', html_file]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                logging.info(f"Successfully processed {os.path.basename(html_file)}")
                processed_count += 1
            else:
                logging.error(f"Error processing {html_file}: {result.stderr}")
        except Exception as e:
            logging.error(f"Error running converter: {str(e)}")
    
    # Summary
    logging.info("=" * 50)
    logging.info(f"Processing complete!")
    logging.info(f"Total PDFs found: {len(pdf_files)}")
    logging.info(f"Total HTMLs processed: {processed_count}")
    
    # List of successfully processed files
    logging.info("\nProcessed hansards:")
    collections_base = "/Users/jacksonkeet/Pacific Hansard Development/collections/Fiji"
    if os.path.exists(collections_base):
        for year in sorted(os.listdir(collections_base)):
            year_path = os.path.join(collections_base, year)
            if os.path.isdir(year_path):
                logging.info(f"\n{year}:")
                for month in sorted(os.listdir(year_path)):
                    month_path = os.path.join(year_path, month)
                    if os.path.isdir(month_path):
                        days = sorted(os.listdir(month_path))
                        logging.info(f"  {month}: {len(days)} days")

if __name__ == "__main__":
    process_fiji_hansards()