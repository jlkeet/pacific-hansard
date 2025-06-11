#!/usr/bin/env python3
"""
Fiji Hansard Daily Checker
Runs daily to check for new hansards and process them
"""

import os
import json
import logging
from datetime import datetime
import subprocess
from fiji_hansard_scraper import check_for_updates
from pdfminer.high_level import extract_text_to_fp
from pdfminer.layout import LAParams
from io import StringIO

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'logs/fiji_daily_checker_{datetime.now().strftime("%Y-%m-%d")}.log'),
        logging.StreamHandler()
    ]
)

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

def process_new_hansards(new_files):
    """Process newly downloaded hansards"""
    processed_count = 0
    
    for filename in new_files:
        if filename.endswith('.pdf'):
            pdf_path = os.path.join('pdf_hansards', filename)
            html_filename = filename.replace('.pdf', '.html')
            html_path = os.path.join('html_hansards', html_filename)
            
            # Convert PDF to HTML
            if pdf_to_html(pdf_path, html_path):
                logging.info(f"Converted {filename} to HTML")
                
                # Run the hansard converter
                try:
                    cmd = ['python', 'fiji-hansard-converter.py', html_path]
                    result = subprocess.run(cmd, capture_output=True, text=True)
                    
                    if result.returncode == 0:
                        logging.info(f"Successfully processed {filename}")
                        processed_count += 1
                    else:
                        logging.error(f"Error processing {filename}: {result.stderr}")
                except Exception as e:
                    logging.error(f"Error running converter: {str(e)}")
    
    return processed_count

def main():
    """Main function for daily checking"""
    logging.info("=" * 50)
    logging.info("Starting Fiji Hansard Daily Check")
    logging.info(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logging.info("=" * 50)
    
    # Check for new hansards
    new_files = check_for_updates()
    
    if new_files:
        # Process the new files
        processed = process_new_hansards(new_files)
        logging.info(f"Processed {processed} new hansards")
        
        # Send notification (could be email, webhook, etc.)
        notify_new_hansards(new_files, processed)
    else:
        logging.info("No new hansards found today")
    
    logging.info("Daily check complete")

def notify_new_hansards(new_files, processed_count):
    """Send notification about new hansards"""
    # This could be extended to send emails, Slack messages, etc.
    summary = {
        'date': datetime.now().isoformat(),
        'new_files': new_files,
        'processed_count': processed_count
    }
    
    # Save summary
    with open(f'logs/fiji_summary_{datetime.now().strftime("%Y%m%d")}.json', 'w') as f:
        json.dump(summary, f, indent=2)
    
    logging.info(f"Summary saved. {len(new_files)} new files, {processed_count} processed.")

if __name__ == "__main__":
    main()