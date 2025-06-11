#!/usr/bin/env python3
"""
Daily checker for new Cook Islands Hansards.
This script is designed to run daily and only process new hansards.
"""

import os
import sys
import logging
import json
from datetime import datetime

# Add the script directory to the path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(SCRIPT_DIR)

# Import the main scraper using direct import
import importlib.util

scraper_path = os.path.join(SCRIPT_DIR, "CI-hansard-scraper.py")
spec = importlib.util.spec_from_file_location("scraper", scraper_path)
scraper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(scraper)

# Import the functions we need
setup_directories = scraper.setup_directories
load_processed_hansards = scraper.load_processed_hansards
save_processed_hansards = scraper.save_processed_hansards
get_hansard_pdfs = scraper.get_hansard_pdfs
download_pdf = scraper.download_pdf
convert_pdf_to_html = scraper.convert_pdf_to_html
process_html = scraper.process_html
logger = scraper.logger
PDF_DIR = scraper.PDF_DIR
HTML_DIR = scraper.HTML_DIR
PROCESSED_DIR = scraper.PROCESSED_DIR

def main():
    """Main function for daily checking."""
    logger.info("=" * 60)
    logger.info("Starting daily checker for new Cook Islands Hansards")
    logger.info(f"Run time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 60)
    
    try:
        # Setup directories
        setup_directories()
        
        # Load previously processed hansards
        processed_hansards = load_processed_hansards()
        logger.info(f"Previously processed hansards: {len(processed_hansards)}")
        
        # Get current list of hansards
        logger.info("Fetching current list of hansards from website...")
        pdf_links = get_hansard_pdfs()
        
        if not pdf_links:
            logger.error("Failed to fetch hansard list from website")
            return 1
        
        logger.info(f"Total hansards on website: {len(pdf_links)}")
        
        # Find new hansards
        new_hansards = []
        for pdf_url, filename, date_str in pdf_links:
            # Use filename as the key since URLs might change
            if filename not in [v.get('filename') for v in processed_hansards.values()]:
                new_hansards.append((pdf_url, filename, date_str))
        
        logger.info(f"New hansards found: {len(new_hansards)}")
        
        if not new_hansards:
            logger.info("No new hansards to process")
            return 0
        
        # Process only new hansards
        successfully_processed = 0
        failed = 0
        
        for i, (pdf_url, filename, date_str) in enumerate(new_hansards, 1):
            logger.info(f"\nProcessing new hansard {i}/{len(new_hansards)}: {filename}")
            
            try:
                # Download PDF
                pdf_path = download_pdf(pdf_url, filename)
                if not pdf_path:
                    logger.error(f"Failed to download {filename}")
                    failed += 1
                    continue
                
                # Convert to HTML
                html_path = convert_pdf_to_html(pdf_path)
                if not html_path:
                    logger.error(f"Failed to convert {filename} to HTML")
                    failed += 1
                    continue
                
                # Process HTML
                processed_dir = process_html(html_path)
                if not processed_dir:
                    logger.error(f"Failed to process HTML for {filename}")
                    failed += 1
                    continue
                
                # Record as processed
                # Generate a unique key for this hansard
                import hashlib
                pdf_hash = hashlib.md5(pdf_url.encode()).hexdigest()
                
                processed_hansards[pdf_hash] = {
                    'url': pdf_url,
                    'filename': filename,
                    'date': date_str,
                    'processed_dir': processed_dir,
                    'processed_date': datetime.now().isoformat()
                }
                
                successfully_processed += 1
                logger.info(f"Successfully processed: {filename}")
                
            except Exception as e:
                logger.error(f"Error processing {filename}: {str(e)}")
                failed += 1
        
        # Save updated processed list
        save_processed_hansards(processed_hansards)
        
        # Summary
        logger.info("\n" + "=" * 60)
        logger.info("Daily checker summary:")
        logger.info(f"- New hansards found: {len(new_hansards)}")
        logger.info(f"- Successfully processed: {successfully_processed}")
        logger.info(f"- Failed: {failed}")
        logger.info(f"- Total processed hansards: {len(processed_hansards)}")
        logger.info("=" * 60)
        
        return 0
        
    except Exception as e:
        logger.error(f"Daily checker failed with error: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return 1

if __name__ == "__main__":
    sys.exit(main())