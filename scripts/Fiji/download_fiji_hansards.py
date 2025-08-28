#!/usr/bin/env python3
"""
Download Fiji Parliament Hansards from extracted links
"""

import json
import os
import time
import logging
import subprocess
from datetime import datetime
from urllib.parse import urlparse

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create directories
os.makedirs('pdf_hansards', exist_ok=True)
os.makedirs('data', exist_ok=True)

def load_extracted_links():
    """Load the extracted PDF links"""
    try:
        with open('fiji_hansard_links_2022_2024.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error("fiji_hansard_links_2022_2024.json not found. Please run extract_hansard_links.py first.")
        return None

def load_processed_hansards():
    """Load the list of already processed hansards"""
    try:
        with open('data/fiji_processed_hansards.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_processed_hansards(processed):
    """Save the list of processed hansards"""
    with open('data/fiji_processed_hansards.json', 'w') as f:
        json.dump(processed, f, indent=2)

def download_with_curl(url, output_path):
    """Download file using curl"""
    try:
        cmd = [
            'curl', '-L', '-o', output_path,
            '-H', 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            '-H', 'Accept: application/pdf,text/html,*/*',
            '--compressed',
            '--connect-timeout', '30',
            '--max-time', '300',
            '--silent',
            '--show-error',
            url
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
            # Verify it's a PDF
            with open(output_path, 'rb') as f:
                header = f.read(4)
                if header == b'%PDF':
                    return True
                else:
                    logger.warning(f"Downloaded file is not a valid PDF: {output_path}")
                    if os.path.exists(output_path):
                        os.remove(output_path)
                    return False
        else:
            if os.path.exists(output_path):
                os.remove(output_path)
            logger.error(f"Curl failed: {result.stderr}")
            return False
            
    except Exception as e:
        logger.error(f"Error downloading {url}: {str(e)}")
        return False

def download_hansards():
    """Download all hansards from the extracted links"""
    logger.info("Starting Fiji Hansard download process...")
    
    # Load extracted links
    link_data = load_extracted_links()
    if not link_data:
        return False
    
    # Load processed files
    processed = load_processed_hansards()
    
    all_links = link_data['all_links']
    logger.info(f"Total PDFs to process: {len(all_links)}")
    
    downloaded_count = 0
    skipped_count = 0
    failed_count = 0
    
    for i, pdf_info in enumerate(all_links, 1):
        filename = pdf_info['filename']
        url = pdf_info['url']
        year = pdf_info['year']
        
        logger.info(f"[{i}/{len(all_links)}] Processing: {filename}")
        
        # Skip if already processed
        if filename in processed:
            logger.info(f"  Already processed, skipping")
            skipped_count += 1
            continue
        
        # Download
        pdf_path = os.path.join('pdf_hansards', filename)
        
        logger.info(f"  Downloading from: {url}")
        
        if download_with_curl(url, pdf_path):
            logger.info(f"  Successfully downloaded: {filename}")
            
            # Record as processed
            processed[filename] = {
                'url': url,
                'download_date': datetime.now().isoformat(),
                'year': year,
                'file_size': os.path.getsize(pdf_path)
            }
            
            downloaded_count += 1
            save_processed_hansards(processed)
            
            # Be polite to the server
            time.sleep(1)
            
        else:
            logger.error(f"  Failed to download: {filename}")
            failed_count += 1
        
        # Progress update every 10 files
        if i % 10 == 0:
            logger.info(f"Progress: {i}/{len(all_links)} processed | Downloaded: {downloaded_count} | Skipped: {skipped_count} | Failed: {failed_count}")
    
    # Final summary
    logger.info("\n" + "="*60)
    logger.info("DOWNLOAD SUMMARY")
    logger.info("="*60)
    logger.info(f"Total PDFs processed: {len(all_links)}")
    logger.info(f"Successfully downloaded: {downloaded_count}")
    logger.info(f"Already existed (skipped): {skipped_count}")
    logger.info(f"Failed downloads: {failed_count}")
    logger.info("="*60)
    
    return downloaded_count > 0

def main():
    """Main function"""
    success = download_hansards()
    
    if success:
        logger.info("Download process completed successfully!")
        return 0
    else:
        logger.error("Download process failed or no new files downloaded")
        return 1

if __name__ == "__main__":
    exit(main())