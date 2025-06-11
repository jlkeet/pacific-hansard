#!/usr/bin/env python3
"""
Fiji Parliament Hansard Scraper - Enhanced for 2022-2024
Searches for and downloads hansards from specific years
"""

import requests
from bs4 import BeautifulSoup
import os
import re
import json
from datetime import datetime
import time
import logging
import subprocess
from urllib.parse import urljoin, urlparse

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Create directories
os.makedirs('pdf_hansards', exist_ok=True)
os.makedirs('html_hansards', exist_ok=True)
os.makedirs('logs', exist_ok=True)
os.makedirs('data', exist_ok=True)

# URLs to try
BASE_URLS = [
    "https://www.parliament.gov.fj",
    "http://www.parliament.gov.fj"
]

SEARCH_URLS = [
    "/parliament-debates/",
    "/hansard/",
    "/parliamentary-debates/",
    "/documents/hansard/",
    "/publications/hansard/",
    "/resources/hansard/",
    "/wp-content/uploads/"  # WordPress common upload path
]

# Years to search for
TARGET_YEARS = ['2022', '2023', '2024']

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
            url
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
            return True
        else:
            if os.path.exists(output_path):
                os.remove(output_path)
            return False
            
    except Exception as e:
        logging.error(f"Error downloading {url}: {str(e)}")
        return False

def fetch_page_with_curl(url):
    """Fetch page content using curl"""
    try:
        cmd = [
            'curl', '-L',
            '-H', 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            '-H', 'Accept: text/html,application/xhtml+xml',
            '--compressed',
            '--connect-timeout', '30',
            url
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            return result.stdout
        else:
            logging.error(f"Curl failed for {url}: {result.stderr}")
            return None
            
    except Exception as e:
        logging.error(f"Error fetching {url}: {str(e)}")
        return None

def search_year_specific_pages(base_url, year):
    """Search for year-specific pages"""
    year_urls = []
    
    # Common year-based URL patterns
    year_patterns = [
        f"/{year}/",
        f"/hansard/{year}/",
        f"/hansard-{year}/",
        f"/parliament-debates-{year}/",
        f"/documents/{year}/",
        f"/wp-content/uploads/{year}/"
    ]
    
    for pattern in year_patterns:
        test_url = urljoin(base_url, pattern)
        logging.info(f"Checking year URL: {test_url}")
        
        content = fetch_page_with_curl(test_url)
        if content and 'hansard' in content.lower():
            year_urls.append(test_url)
    
    return year_urls

def extract_hansard_links(content, base_url, year_filter=None):
    """Extract hansard links from page content"""
    if not content:
        return []
    
    soup = BeautifulSoup(content, 'html.parser')
    hansard_links = []
    
    # Find all links
    all_links = soup.find_all('a', href=True)
    
    for link in all_links:
        href = link.get('href', '')
        text = link.get_text(strip=True).lower()
        
        # Check if it's a hansard link
        if any(keyword in href.lower() or keyword in text for keyword in ['hansard', 'daily-hansard', 'dh-']):
            # Check for PDF files
            if href.lower().endswith('.pdf'):
                # Apply year filter if specified
                if year_filter:
                    if year_filter not in href and year_filter not in text:
                        continue
                
                absolute_url = urljoin(base_url, href)
                hansard_links.append({
                    'url': absolute_url,
                    'text': link.get_text(strip=True),
                    'type': 'pdf'
                })
    
    return hansard_links

def search_wordpress_uploads(base_url, years):
    """Search WordPress uploads directory structure"""
    hansard_links = []
    
    for year in years:
        # WordPress typically organizes uploads by year/month
        for month in range(1, 13):
            month_str = f"{month:02d}"
            upload_url = urljoin(base_url, f"/wp-content/uploads/{year}/{month_str}/")
            
            logging.info(f"Checking WordPress uploads: {upload_url}")
            content = fetch_page_with_curl(upload_url)
            
            if content:
                links = extract_hansard_links(content, base_url, year)
                hansard_links.extend(links)
    
    return hansard_links

def scrape_fiji_parliament_years():
    """Scrape Fiji Parliament for hansards from 2022-2024"""
    logging.info("Starting enhanced Fiji Parliament scraper for 2022-2024...")
    
    processed = load_processed_hansards()
    all_hansard_links = []
    new_hansards = []
    
    # Try each base URL
    for base_url in BASE_URLS:
        logging.info(f"\nTrying base URL: {base_url}")
        
        # Try each search path
        for search_path in SEARCH_URLS:
            url = urljoin(base_url, search_path)
            logging.info(f"Checking: {url}")
            
            content = fetch_page_with_curl(url)
            if content:
                # Extract hansard links
                for year in TARGET_YEARS:
                    links = extract_hansard_links(content, base_url, year)
                    all_hansard_links.extend(links)
        
        # Try year-specific pages
        for year in TARGET_YEARS:
            year_urls = search_year_specific_pages(base_url, year)
            for year_url in year_urls:
                content = fetch_page_with_curl(year_url)
                if content:
                    links = extract_hansard_links(content, base_url, year)
                    all_hansard_links.extend(links)
        
        # Try WordPress uploads structure
        wp_links = search_wordpress_uploads(base_url, TARGET_YEARS)
        all_hansard_links.extend(wp_links)
    
    # Remove duplicates
    unique_links = {}
    for link in all_hansard_links:
        url = link['url']
        if url not in unique_links:
            unique_links[url] = link
    
    logging.info(f"\nFound {len(unique_links)} unique hansard links")
    
    # Download new hansards
    for url, link_info in unique_links.items():
        filename = os.path.basename(urlparse(url).path)
        
        # Skip if no filename
        if not filename:
            continue
        
        # Skip if already processed
        if filename in processed:
            logging.info(f"Already processed: {filename}")
            continue
        
        # Check if it's from target years
        year_found = False
        for year in TARGET_YEARS:
            if year in filename or year in link_info['text']:
                year_found = True
                break
        
        if not year_found:
            # Try to extract date from filename
            date_match = re.search(r'(\d{4})', filename)
            if date_match and date_match.group(1) in TARGET_YEARS:
                year_found = True
        
        if not year_found:
            logging.info(f"Skipping {filename} - not from target years")
            continue
        
        logging.info(f"Found new hansard: {filename}")
        
        # Download
        pdf_path = os.path.join('pdf_hansards', filename)
        logging.info(f"Downloading {url}")
        
        if download_with_curl(url, pdf_path):
            logging.info(f"Successfully downloaded {filename}")
            
            processed[filename] = {
                'url': url,
                'download_date': datetime.now().isoformat(),
                'text': link_info['text']
            }
            
            new_hansards.append(filename)
            save_processed_hansards(processed)
            
            # Be polite
            time.sleep(2)
        else:
            logging.error(f"Failed to download {filename}")
    
    # If no hansards found, try alternative search
    if len(new_hansards) == 0:
        logging.info("\nNo new hansards found with standard search. Trying Google search...")
        google_search_fiji_hansards()
    
    # Summary
    logging.info(f"\nScraping complete!")
    logging.info(f"New hansards downloaded: {len(new_hansards)}")
    if new_hansards:
        logging.info("New files:")
        for file in sorted(new_hansards):
            logging.info(f"  - {file}")
    
    return new_hansards

def google_search_fiji_hansards():
    """Use Google to find Fiji hansards"""
    logging.info("Searching via Google for Fiji hansards 2022-2024...")
    
    search_queries = [
        'site:parliament.gov.fj hansard 2022 filetype:pdf',
        'site:parliament.gov.fj hansard 2023 filetype:pdf', 
        'site:parliament.gov.fj hansard 2024 filetype:pdf',
        'site:parliament.gov.fj "daily hansard" 2022',
        'site:parliament.gov.fj "daily hansard" 2023',
        'site:parliament.gov.fj "daily hansard" 2024'
    ]
    
    for query in search_queries:
        logging.info(f"Google search: {query}")
        # Note: This would require implementing Google search API
        # For now, we'll log the searches that should be done manually

if __name__ == "__main__":
    scrape_fiji_parliament_years()