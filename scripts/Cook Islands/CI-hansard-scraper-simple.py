#!/usr/bin/env python3
"""
Cook Islands Parliament Hansard Scraper - Simple Version
Downloads hansards from Cook Islands Parliament website for specific years
Based on successful Fiji scraper pattern
"""

import requests
from bs4 import BeautifulSoup
import os
import re
import json
from datetime import datetime
import time
import logging
import argparse
from urllib.parse import urljoin, urlparse

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Create directories
os.makedirs('pdf_hansards', exist_ok=True)
os.makedirs('logs', exist_ok=True)
os.makedirs('data', exist_ok=True)

# Cook Islands Parliament Hansard URLs
BASE_URL = "https://parliament.gov.ck"
HANSARD_URL = "https://parliament.gov.ck/hansard-library/"

def load_processed_hansards():
    """Load the list of already processed hansards"""
    processed_file = 'data/processed_hansards.json'
    if os.path.exists(processed_file):
        with open(processed_file, 'r') as f:
            return json.load(f)
    return []

def save_processed_hansards(processed_list):
    """Save the list of processed hansards"""
    processed_file = 'data/processed_hansards.json'
    with open(processed_file, 'w') as f:
        json.dump(processed_list, f, indent=2)

def download_pdf(session, url, filename, referer_url):
    """Download PDF file using session"""
    try:
        output_path = os.path.join('pdf_hansards', filename)
        
        if os.path.exists(output_path):
            logging.info(f"PDF already exists: {filename}")
            return True
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/pdf,application/octet-stream,*/*;q=0.9',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Referer': referer_url,
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'same-origin',
        }
        response = session.get(url, stream=True, timeout=60, headers=headers)
        response.raise_for_status()
        
        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        
        if os.path.getsize(output_path) > 1000:  # Valid PDF should be > 1KB
            logging.info(f"Downloaded: {filename}")
            return True
        else:
            os.remove(output_path)
            return False
            
    except Exception as e:
        logging.error(f"Error downloading {url}: {e}")
        if os.path.exists(output_path):
            os.remove(output_path)
        return False

def scrape_hansards(start_year=None, end_year=None):
    """Scrape hansards from Cook Islands Parliament website"""
    processed = load_processed_hansards()
    newly_processed = []
    
    # Create a session to maintain cookies
    session = requests.Session()
    session.verify = False
    
    try:
        logging.info(f"Fetching hansard page: {HANSARD_URL}")
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
        }
        
        # First visit the main parliament site to establish session
        logging.info("Establishing session with main site...")
        session.get(BASE_URL, timeout=30, headers=headers)
        
        # Then visit the hansard page
        response = session.get(HANSARD_URL, timeout=30, headers=headers)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find all links that might be PDFs or point to hansards
        links = soup.find_all('a', href=True)
        pdf_links = []
        
        for link in links:
            href = link['href']
            text = link.get_text().strip()
            
            # Look for PDF links or hansard-related links
            if (href.lower().endswith('.pdf') or 
                'hansard' in text.lower() or 
                'parliament' in text.lower()):
                
                # Make absolute URL
                if href.startswith('/'):
                    full_url = urljoin(BASE_URL, href)
                elif href.startswith('http'):
                    full_url = href
                else:
                    full_url = urljoin(HANSARD_URL, href)
                
                # Extract date/year from link text or URL - prioritize recent years
                year_matches = re.findall(r'20(\d{2})', text + ' ' + href)
                if year_matches:
                    # Take the most recent year found (in case of multiple years)
                    years = ['20' + match for match in year_matches]
                    # Filter to only years we care about (2020-2030 range)
                    valid_years = [y for y in years if 2020 <= int(y) <= 2030]
                    
                    if not valid_years:
                        continue  # Skip if no valid years found
                    
                    year = valid_years[-1]  # Take the latest valid year
                    
                    # Filter by year range if specified
                    if start_year and int(year) < int(start_year):
                        continue
                    if end_year and int(year) > int(end_year):
                        continue
                    
                    pdf_links.append({
                        'url': full_url,
                        'text': text,
                        'year': year
                    })
        
        # Remove duplicates
        unique_links = {}
        for link in pdf_links:
            key = link['url']
            if key not in unique_links:
                unique_links[key] = link
        
        pdf_links = list(unique_links.values())
        logging.info(f"Found {len(pdf_links)} potential hansard links")
        
        # Download PDFs
        for link in pdf_links:
            url = link['url']
            year = link['year']
            text = link['text']
            
            if url in processed:
                logging.info(f"Already processed: {text}")
                continue
            
            # Create filename based on text and year
            safe_filename = re.sub(r'[^\w\-_\.]', '_', text)
            safe_filename = safe_filename.strip('_')
            if not safe_filename.lower().endswith('.pdf'):
                safe_filename += '.pdf'
            
            # Add year prefix if not already there
            if not safe_filename.startswith(year):
                safe_filename = f"{year}_{safe_filename}"
            
            logging.info(f"Processing: {text} ({year})")
            
            if download_pdf(session, url, safe_filename, HANSARD_URL):
                newly_processed.append(url)
                processed.append(url)
                logging.info(f"✅ Downloaded: {safe_filename}")
            else:
                logging.error(f"❌ Failed to download: {safe_filename}")
            
            # Be respectful to the server
            time.sleep(3)
        
        # Save progress
        if newly_processed:
            save_processed_hansards(processed)
            logging.info(f"Processing complete. Downloaded {len(newly_processed)} new files.")
        else:
            logging.info("No new files to download.")
            
    except Exception as e:
        logging.error(f"Error scraping hansards: {e}")
        # Save progress even if there was an error
        if newly_processed:
            save_processed_hansards(processed)

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Cook Islands Hansard Scraper')
    parser.add_argument('--start-year', type=int, help='Start year for filtering')
    parser.add_argument('--end-year', type=int, help='End year for filtering')
    
    args = parser.parse_args()
    
    logging.info("Starting Cook Islands Hansard scraping...")
    scrape_hansards(args.start_year, args.end_year)
    logging.info("Scraping completed.")

if __name__ == "__main__":
    main()