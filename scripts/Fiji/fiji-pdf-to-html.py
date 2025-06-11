#!/usr/bin/env python3
"""
Convert Fiji Parliament PDF hansards to HTML
"""

import os
import subprocess
import logging
from datetime import datetime
import re

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def pdf_to_html_pdftohtml(pdf_path, html_path):
    """Convert PDF to HTML using pdftohtml"""
    try:
        # Create a temporary directory for pdftohtml output
        temp_dir = html_path.replace('.html', '_temp')
        os.makedirs(temp_dir, exist_ok=True)
        
        # Run pdftohtml
        cmd = ['pdftohtml', '-enc', 'UTF-8', '-noframes', pdf_path, os.path.join(temp_dir, 'output')]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            # Read the generated HTML
            output_file = os.path.join(temp_dir, 'output.html')
            if os.path.exists(output_file):
                with open(output_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Write to final location
                with open(html_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                # Clean up temp directory
                for file in os.listdir(temp_dir):
                    os.remove(os.path.join(temp_dir, file))
                os.rmdir(temp_dir)
                
                return True
        
        return False
        
    except Exception as e:
        logging.error(f"pdftohtml error for {pdf_path}: {str(e)}")
        return False

def pdf_to_html_pdfplumber(pdf_path, html_path):
    """Convert PDF to HTML using pdfplumber"""
    try:
        import pdfplumber
        
        html_content = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Fiji Hansard</title>
</head>
<body>
"""
        
        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages, 1):
                text = page.extract_text()
                if text:
                    # Convert text to HTML paragraphs
                    paragraphs = text.split('\n\n')
                    for para in paragraphs:
                        if para.strip():
                            html_content += f"<p>{para.strip()}</p>\n"
                    
                    # Add page break
                    html_content += f'<p><a name="{page_num}">Page {page_num}</a></p>\n'
        
        html_content += """
</body>
</html>"""
        
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        return True
        
    except Exception as e:
        logging.error(f"pdfplumber error for {pdf_path}: {str(e)}")
        return False

def pdf_to_html_pdfminer(pdf_path, html_path):
    """Convert PDF to HTML using pdfminer"""
    try:
        from pdfminer.high_level import extract_text_to_fp
        from pdfminer.layout import LAParams
        from io import StringIO
        
        # Extract text
        output_string = StringIO()
        with open(pdf_path, 'rb') as pdf_file:
            extract_text_to_fp(pdf_file, output_string, laparams=LAParams(), output_type='html')
        
        html_content = output_string.getvalue()
        
        # Write to file
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        return True
        
    except Exception as e:
        logging.error(f"pdfminer error for {pdf_path}: {str(e)}")
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
        
        # Skip if already converted
        if os.path.exists(html_path):
            logging.info(f"Already converted: {filename}")
            converted_count += 1
            continue
        
        logging.info(f"Converting: {filename}")
        
        # Try different conversion methods
        success = False
        
        # Method 1: pdftohtml (if available)
        if not success:
            success = pdf_to_html_pdftohtml(pdf_path, html_path)
            if success:
                logging.info(f"  ✓ Converted with pdftohtml")
        
        # Method 2: pdfplumber
        if not success:
            success = pdf_to_html_pdfplumber(pdf_path, html_path)
            if success:
                logging.info(f"  ✓ Converted with pdfplumber")
        
        # Method 3: pdfminer
        if not success:
            success = pdf_to_html_pdfminer(pdf_path, html_path)
            if success:
                logging.info(f"  ✓ Converted with pdfminer")
        
        if success:
            converted_count += 1
        else:
            logging.error(f"  ✗ Failed to convert {filename}")
    
    logging.info(f"\nConversion complete: {converted_count}/{len(pdf_files)} PDFs converted")
    return converted_count

if __name__ == "__main__":
    convert_all_pdfs()