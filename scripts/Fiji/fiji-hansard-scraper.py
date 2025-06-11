#!/usr/bin/env python3
"""
Fiji Parliament Hansard Scraper
Scrapes and downloads hansard documents from the Fiji Parliament website
"""

import requests
from bs4 import BeautifulSoup
import os
import re
import json
from datetime import datetime, timedelta
import time
import logging
import subprocess
from urllib.parse import urljoin, urlparse

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/fiji_hansard_scraper.log'),
        logging.StreamHandler()
    ]
)

# Create directories if they don't exist
os.makedirs('pdf_hansards', exist_ok=True)
os.makedirs('html_hansards', exist_ok=True)
os.makedirs('logs', exist_ok=True)
os.makedirs('data', exist_ok=True)

# Base URL for Fiji Parliament
BASE_URL = "https://www.parliament.gov.fj"
HANSARD_URL = "https://www.parliament.gov.fj/parliament-debates/"

# Headers to mimic a browser
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1'
}

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
    """Download file using curl to bypass anti-bot measures"""
    try:
        # Use curl with browser-like headers
        cmd = [
            'curl', '-L', '-o', output_path,
            '-H', f'User-Agent: {HEADERS["User-Agent"]}',
            '-H', 'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            '-H', 'Accept-Language: en-US,en;q=0.5',
            '--compressed',
            url
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            # Check if file was actually downloaded and has content
            if os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
                return True
            else:
                if os.path.exists(output_path):
                    os.remove(output_path)
                return False
        else:
            logging.error(f"Curl download failed: {result.stderr}")
            return False
            
    except Exception as e:
        logging.error(f"Error downloading {url}: {str(e)}")
        return False

def fetch_page_with_curl(url):
    """Fetch page content using curl"""
    try:
        cmd = [
            'curl', '-L',
            '-H', f'User-Agent: {HEADERS["User-Agent"]}',
            '-H', 'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            '-H', 'Accept-Language: en-US,en;q=0.5',
            '--compressed',
            url
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            return result.stdout
        else:
            logging.error(f"Curl fetch failed: {result.stderr}")
            return None
            
    except Exception as e:
        logging.error(f"Error fetching {url}: {str(e)}")
        return None

def normalize_hansard_filename(filename):
    """Normalize hansard filename to a consistent format"""
    # Remove extra spaces and special characters
    filename = re.sub(r'\s+', '-', filename)
    filename = re.sub(r'[^\w\-.]', '', filename)
    
    # Ensure it ends with .pdf or .html
    if not filename.endswith(('.pdf', '.html')):
        filename += '.pdf'
    
    return filename

def extract_date_from_filename(filename):
    """Extract date from Fiji hansard filename"""
    # Pattern: Daily-Hansard-{Day}-{Date}-{Month}-{Year}
    # Example: Daily-Hansard-Friday-12th-February-2021
    
    # First try the standard pattern
    pattern = r'(\w+)-(\d+)\w*-(\w+)-(\d{4})'
    match = re.search(pattern, filename)
    
    if match:
        day_name = match.group(1)
        day_num = match.group(2)
        month = match.group(3)
        year = match.group(4)
        
        try:
            # Convert month name to number
            month_num = datetime.strptime(month, '%B').month
            date = datetime(int(year), month_num, int(day_num))
            return date.strftime('%Y-%m-%d')
        except:
            pass
    
    # Try alternate patterns
    # Pattern for DH-Wednesday-26th-May-2020
    pattern2 = r'DH-\w+-(\d+)\w*-(\w+)-(\d{4})'
    match = re.search(pattern2, filename)
    
    if match:
        day_num = match.group(1)
        month = match.group(2)
        year = match.group(3)
        
        try:
            month_num = datetime.strptime(month, '%B').month
            date = datetime(int(year), month_num, int(day_num))
            return date.strftime('%Y-%m-%d')
        except:
            pass
    
    return None

def scrape_fiji_parliament():
    """Scrape the Fiji Parliament website for hansard documents"""
    logging.info("Starting Fiji Parliament hansard scraper...")
    
    processed = load_processed_hansards()
    new_hansards = []
    
    try:
        # Fetch the main hansard page
        logging.info(f"Fetching {HANSARD_URL}")
        page_content = fetch_page_with_curl(HANSARD_URL)
        
        if not page_content:
            logging.error("Failed to fetch hansard page")
            return
        
        soup = BeautifulSoup(page_content, 'html.parser')
        
        # Look for hansard links
        # Fiji Parliament might have different structure, let's find all PDF links
        pdf_links = soup.find_all('a', href=re.compile(r'\.pdf$', re.I))
        
        logging.info(f"Found {len(pdf_links)} PDF links")
        
        for link in pdf_links:
            href = link.get('href', '')
            text = link.get_text(strip=True)
            
            # Skip if not a hansard link
            if 'hansard' not in text.lower() and 'hansard' not in href.lower():
                continue
            
            # Get absolute URL
            pdf_url = urljoin(BASE_URL, href)
            
            # Extract filename
            filename = os.path.basename(urlparse(pdf_url).path)
            if not filename:
                # Try to create filename from link text
                filename = normalize_hansard_filename(text)
            
            # Skip if already processed
            if filename in processed:
                logging.info(f"Already processed: {filename}")
                continue
            
            logging.info(f"Found new hansard: {filename}")
            
            # Download PDF
            pdf_path = os.path.join('pdf_hansards', filename)
            logging.info(f"Downloading {pdf_url} to {pdf_path}")
            
            if download_with_curl(pdf_url, pdf_path):
                logging.info(f"Successfully downloaded {filename}")
                
                # Extract date
                date = extract_date_from_filename(filename)
                
                # Record as processed
                processed[filename] = {
                    'url': pdf_url,
                    'download_date': datetime.now().isoformat(),
                    'date': date,
                    'type': 'Daily Hansard'
                }
                
                new_hansards.append(filename)
                
                # Save progress after each download
                save_processed_hansards(processed)
                
                # Be polite - wait between downloads
                time.sleep(2)
            else:
                logging.error(f"Failed to download {filename}")
        
        # Also check for any HTML hansard links
        html_links = soup.find_all('a', href=re.compile(r'hansard.*\.html', re.I))
        
        for link in html_links:
            href = link.get('href', '')
            html_url = urljoin(BASE_URL, href)
            filename = os.path.basename(urlparse(html_url).path)
            
            if filename in processed:
                continue
            
            html_path = os.path.join('html_hansards', filename)
            
            if download_with_curl(html_url, html_path):
                logging.info(f"Downloaded HTML: {filename}")
                processed[filename] = {
                    'url': html_url,
                    'download_date': datetime.now().isoformat(),
                    'type': 'HTML'
                }
                new_hansards.append(filename)
                save_processed_hansards(processed)
                time.sleep(2)
        
    except Exception as e:
        logging.error(f"Error during scraping: {str(e)}")
    
    # Summary
    logging.info(f"\nScraping complete!")
    logging.info(f"New hansards found: {len(new_hansards)}")
    if new_hansards:
        logging.info("New files:")
        for file in new_hansards:
            logging.info(f"  - {file}")
    
    return new_hansards

def check_for_updates():
    """Check for new hansards (daily check function)"""
    logging.info("Checking for new Fiji hansards...")
    
    new_files = scrape_fiji_parliament()
    
    if new_files:
        logging.info(f"Found {len(new_files)} new hansards")
        # Could trigger conversion pipeline here
        return new_files
    else:
        logging.info("No new hansards found")
        return []

if __name__ == "__main__":
    # Run the scraper
    scrape_fiji_parliament()