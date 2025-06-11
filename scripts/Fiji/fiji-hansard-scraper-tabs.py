#!/usr/bin/env python3
"""
Fiji Parliament Hansard Scraper - Tab-based navigation
Handles the year tabs on https://www.parliament.gov.fj/hansard/
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
from urllib.parse import urljoin, urlparse, parse_qs

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

# Base URL
BASE_URL = "https://www.parliament.gov.fj"
HANSARD_PAGE = "https://www.parliament.gov.fj/hansard/"

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
            '-H', 'Referer: https://www.parliament.gov.fj/hansard/',
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

def fetch_page_with_curl(url, extra_headers=None):
    """Fetch page content using curl with JavaScript support"""
    headers = [
        '-H', 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        '-H', 'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        '-H', 'Accept-Language: en-US,en;q=0.5',
        '-H', 'Accept-Encoding: gzip, deflate, br',
        '-H', 'Connection: keep-alive',
        '-H', 'Upgrade-Insecure-Requests: 1',
        '-H', 'Sec-Fetch-Dest: document',
        '-H', 'Sec-Fetch-Mode: navigate',
        '-H', 'Sec-Fetch-Site: none',
        '-H', 'Sec-Fetch-User: ?1',
        '-H', 'Cache-Control: max-age=0'
    ]
    
    if extra_headers:
        headers.extend(extra_headers)
    
    cmd = ['curl', '-L'] + headers + ['--compressed', url]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            return result.stdout
        else:
            logging.error(f"Curl failed for {url}: {result.stderr}")
            return None
    except Exception as e:
        logging.error(f"Error fetching {url}: {str(e)}")
        return None

def extract_tab_structure(content):
    """Extract tab structure and data attributes from the page"""
    soup = BeautifulSoup(content, 'html.parser')
    tab_info = {}
    
    # Look for common tab patterns
    # Pattern 1: Bootstrap tabs
    tabs = soup.find_all(['a', 'button'], {'data-toggle': 'tab'})
    for tab in tabs:
        text = tab.get_text(strip=True)
        for year in TARGET_YEARS:
            if year in text:
                href = tab.get('href', '')
                data_target = tab.get('data-target', '')
                tab_info[year] = {
                    'href': href,
                    'data_target': data_target,
                    'text': text
                }
    
    # Pattern 2: Links with year in href
    year_links = soup.find_all('a', href=True)
    for link in year_links:
        href = link.get('href', '')
        text = link.get_text(strip=True)
        for year in TARGET_YEARS:
            if year in href or year in text:
                if 'hansard' in href.lower() or 'hansard' in text.lower():
                    if year not in tab_info:
                        tab_info[year] = {
                            'href': href,
                            'text': text,
                            'type': 'link'
                        }
    
    # Pattern 3: Divs with year classes or ids
    for year in TARGET_YEARS:
        year_divs = soup.find_all(['div', 'section'], id=re.compile(f'{year}', re.I))
        year_divs.extend(soup.find_all(['div', 'section'], class_=re.compile(f'{year}', re.I)))
        
        for div in year_divs:
            if year not in tab_info:
                tab_info[year] = {
                    'element': 'div',
                    'id': div.get('id', ''),
                    'class': div.get('class', [])
                }
    
    return tab_info

def search_direct_urls():
    """Try direct URL patterns for each year"""
    all_hansard_links = []
    
    url_patterns = [
        "{base}/hansard/?year={year}",
        "{base}/hansard/{year}/",
        "{base}/hansard#{year}",
        "{base}/wp-content/uploads/{year}/",
        "{base}/parliament-debates/{year}/",
        "{base}/documents/hansard/{year}/"
    ]
    
    for year in TARGET_YEARS:
        logging.info(f"\nTrying direct URLs for {year}...")
        
        for pattern in url_patterns:
            url = pattern.format(base=BASE_URL, year=year)
            logging.info(f"Checking: {url}")
            
            content = fetch_page_with_curl(url)
            if content:
                soup = BeautifulSoup(content, 'html.parser')
                
                # Find PDF links
                pdf_links = soup.find_all('a', href=re.compile(r'\.pdf$', re.I))
                
                for link in pdf_links:
                    href = link.get('href', '')
                    text = link.get_text(strip=True)
                    
                    if 'hansard' in href.lower() or 'hansard' in text.lower():
                        absolute_url = urljoin(BASE_URL, href)
                        all_hansard_links.append({
                            'url': absolute_url,
                            'text': text,
                            'year': year,
                            'source': url
                        })
                        logging.info(f"Found: {text}")
                
                # Also check for month folders (WordPress pattern)
                month_links = soup.find_all('a', href=re.compile(r'/\d{2}/$'))
                for month_link in month_links:
                    month_href = month_link.get('href', '')
                    month_url = urljoin(url, month_href)
                    
                    logging.info(f"Checking month folder: {month_url}")
                    month_content = fetch_page_with_curl(month_url)
                    
                    if month_content:
                        month_soup = BeautifulSoup(month_content, 'html.parser')
                        month_pdfs = month_soup.find_all('a', href=re.compile(r'\.pdf$', re.I))
                        
                        for pdf in month_pdfs:
                            pdf_href = pdf.get('href', '')
                            pdf_text = pdf.get_text(strip=True)
                            
                            if 'hansard' in pdf_href.lower() or 'hansard' in pdf_text.lower():
                                absolute_url = urljoin(BASE_URL, pdf_href)
                                all_hansard_links.append({
                                    'url': absolute_url,
                                    'text': pdf_text,
                                    'year': year,
                                    'source': month_url
                                })
                                logging.info(f"Found in month folder: {pdf_text}")
    
    return all_hansard_links

def search_main_hansard_page():
    """Search the main hansard page for all PDFs"""
    logging.info(f"\nFetching main hansard page: {HANSARD_PAGE}")
    
    content = fetch_page_with_curl(HANSARD_PAGE)
    all_hansard_links = []
    
    if content:
        # Save for debugging
        with open('logs/hansard_main_page.html', 'w', encoding='utf-8') as f:
            f.write(content)
        
        soup = BeautifulSoup(content, 'html.parser')
        
        # Extract tab structure
        tab_info = extract_tab_structure(content)
        logging.info(f"Found tab structure: {tab_info}")
        
        # Find all PDF links on the page
        pdf_links = soup.find_all('a', href=re.compile(r'\.pdf$', re.I))
        logging.info(f"Found {len(pdf_links)} PDF links on main page")
        
        for link in pdf_links:
            href = link.get('href', '')
            text = link.get_text(strip=True)
            
            # Check if it's a hansard
            if 'hansard' in href.lower() or 'hansard' in text.lower():
                # Check which year it belongs to
                for year in TARGET_YEARS:
                    if year in href or year in text:
                        absolute_url = urljoin(BASE_URL, href)
                        all_hansard_links.append({
                            'url': absolute_url,
                            'text': text,
                            'year': year,
                            'source': 'main_page'
                        })
                        logging.info(f"Found: {text} ({year})")
                        break
        
        # Look for tab content divs
        for year in TARGET_YEARS:
            # Common patterns for tab content
            year_patterns = [
                f'tab-{year}',
                f'year-{year}',
                f'content-{year}',
                f'hansard-{year}',
                year
            ]
            
            for pattern in year_patterns:
                year_divs = soup.find_all('div', id=re.compile(pattern, re.I))
                year_divs.extend(soup.find_all('div', class_=re.compile(pattern, re.I)))
                
                for div in year_divs:
                    div_pdfs = div.find_all('a', href=re.compile(r'\.pdf$', re.I))
                    
                    for pdf in div_pdfs:
                        pdf_href = pdf.get('href', '')
                        pdf_text = pdf.get_text(strip=True)
                        
                        if 'hansard' in pdf_href.lower() or 'hansard' in pdf_text.lower():
                            absolute_url = urljoin(BASE_URL, pdf_href)
                            all_hansard_links.append({
                                'url': absolute_url,
                                'text': pdf_text,
                                'year': year,
                                'source': f'tab_{pattern}'
                            })
                            logging.info(f"Found in {pattern} tab: {pdf_text}")
    
    return all_hansard_links

def main():
    """Main function to orchestrate the scraping"""
    logging.info("Starting Fiji Parliament Hansard Scraper for 2022-2024...")
    logging.info("This version handles dynamic tabs on the hansard page")
    
    processed = load_processed_hansards()
    all_hansard_links = []
    new_hansards = []
    
    # Strategy 1: Search main hansard page
    main_page_links = search_main_hansard_page()
    all_hansard_links.extend(main_page_links)
    
    # Strategy 2: Try direct URL patterns
    direct_links = search_direct_urls()
    all_hansard_links.extend(direct_links)
    
    # Remove duplicates
    unique_links = {}
    for link in all_hansard_links:
        url = link['url']
        if url not in unique_links:
            unique_links[url] = link
    
    logging.info(f"\nFound {len(unique_links)} unique hansard links total")
    
    # Group by year for summary
    by_year = {}
    for url, info in unique_links.items():
        year = info.get('year', 'unknown')
        if year not in by_year:
            by_year[year] = []
        by_year[year].append(info)
    
    for year, links in by_year.items():
        logging.info(f"{year}: {len(links)} hansards found")
    
    # Download new hansards
    for url, link_info in unique_links.items():
        filename = os.path.basename(urlparse(url).path)
        
        # Skip if no filename or not PDF
        if not filename or not filename.endswith('.pdf'):
            continue
        
        # Skip if already processed
        if filename in processed:
            logging.info(f"Already processed: {filename}")
            continue
        
        logging.info(f"\nDownloading: {filename}")
        logging.info(f"From: {link_info.get('source', 'unknown')}")
        
        # Download
        pdf_path = os.path.join('pdf_hansards', filename)
        
        if download_with_curl(url, pdf_path):
            logging.info(f"Successfully downloaded {filename}")
            
            processed[filename] = {
                'url': url,
                'download_date': datetime.now().isoformat(),
                'text': link_info.get('text', ''),
                'year': link_info.get('year', ''),
                'source': link_info.get('source', '')
            }
            
            new_hansards.append(filename)
            save_processed_hansards(processed)
            
            # Be polite
            time.sleep(2)
        else:
            logging.error(f"Failed to download {filename}")
    
    # Summary
    logging.info(f"\n{'='*60}")
    logging.info("SCRAPING COMPLETE")
    logging.info(f"{'='*60}")
    logging.info(f"New hansards downloaded: {len(new_hansards)}")
    
    if new_hansards:
        logging.info("\nNew files:")
        for file in sorted(new_hansards):
            logging.info(f"  ✓ {file}")
    else:
        logging.info("\nNo new hansards found.")
        logging.info("\nDebugging suggestions:")
        logging.info("1. Check logs/hansard_main_page.html to see the page structure")
        logging.info("2. The year tabs might use JavaScript to load content dynamically")
        logging.info("3. Try manually visiting these URLs in a browser:")
        for year in TARGET_YEARS:
            logging.info(f"   - {HANSARD_PAGE}#{year}")
            logging.info(f"   - {BASE_URL}/hansard/{year}/")
        logging.info("\n4. If you find the correct URL pattern, we can update the scraper")
    
    return new_hansards

if __name__ == "__main__":
    main()