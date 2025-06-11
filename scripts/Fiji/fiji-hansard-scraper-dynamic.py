#!/usr/bin/env python3
"""
Fiji Parliament Hansard Scraper - Dynamic Tab Handler
Handles the dynamic year tabs on https://www.parliament.gov.fj/hansard/
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
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException

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

def scrape_with_selenium():
    """Use Selenium to handle dynamic JavaScript content"""
    logging.info("Starting Selenium-based scraper for dynamic content...")
    
    # Setup Chrome options
    chrome_options = Options()
    chrome_options.add_argument('--headless')  # Run in headless mode
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--window-size=1920,1080')
    
    try:
        # Initialize the Chrome driver
        driver = webdriver.Chrome(options=chrome_options)
        logging.info("Chrome driver initialized successfully")
        
        # Navigate to the hansard page
        logging.info(f"Navigating to {HANSARD_PAGE}")
        driver.get(HANSARD_PAGE)
        
        # Wait for page to load
        time.sleep(5)
        
        # Find all hansard links for each year
        all_hansard_links = []
        
        for year in TARGET_YEARS:
            logging.info(f"\nSearching for {year} hansards...")
            
            try:
                # Look for year tabs or buttons
                year_elements = driver.find_elements(By.XPATH, f"//a[contains(text(), '{year}')] | //button[contains(text(), '{year}')] | //li[contains(text(), '{year}')]")
                
                if year_elements:
                    # Click on the year tab/button
                    for year_elem in year_elements:
                        try:
                            driver.execute_script("arguments[0].scrollIntoView(true);", year_elem)
                            time.sleep(1)
                            driver.execute_script("arguments[0].click();", year_elem)
                            logging.info(f"Clicked on {year} tab")
                            
                            # Wait for content to load
                            time.sleep(3)
                            
                            # Find PDF links
                            pdf_links = driver.find_elements(By.XPATH, "//a[contains(@href, '.pdf')]")
                            
                            for link in pdf_links:
                                href = link.get_attribute('href')
                                text = link.text
                                
                                # Check if it's a hansard and from the target year
                                if href and ('hansard' in href.lower() or 'hansard' in text.lower()):
                                    if year in href or year in text:
                                        absolute_url = urljoin(BASE_URL, href)
                                        all_hansard_links.append({
                                            'url': absolute_url,
                                            'text': text,
                                            'year': year
                                        })
                                        logging.info(f"Found: {text} - {absolute_url}")
                            
                            break  # Found and processed the year tab
                            
                        except Exception as e:
                            logging.warning(f"Error clicking year element: {str(e)}")
                            continue
                
                else:
                    logging.warning(f"No tab/button found for year {year}")
                    
                    # Alternative: Look for links containing the year
                    year_links = driver.find_elements(By.XPATH, f"//a[contains(@href, '{year}') and contains(@href, '.pdf')]")
                    
                    for link in year_links:
                        href = link.get_attribute('href')
                        text = link.text
                        
                        if href and ('hansard' in href.lower() or 'hansard' in text.lower()):
                            absolute_url = urljoin(BASE_URL, href)
                            all_hansard_links.append({
                                'url': absolute_url,
                                'text': text,
                                'year': year
                            })
                            logging.info(f"Found: {text} - {absolute_url}")
                            
            except Exception as e:
                logging.error(f"Error processing year {year}: {str(e)}")
                continue
        
        # Save page source for debugging
        with open('logs/hansard_page_selenium.html', 'w', encoding='utf-8') as f:
            f.write(driver.page_source)
        
        driver.quit()
        return all_hansard_links
        
    except Exception as e:
        logging.error(f"Selenium error: {str(e)}")
        logging.info("Falling back to curl-based approach...")
        return []

def scrape_with_curl_fallback():
    """Fallback method using curl to fetch the page"""
    logging.info("Using curl fallback method...")
    
    cmd = [
        'curl', '-L',
        '-H', 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        '-H', 'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        '-H', 'Accept-Language: en-US,en;q=0.5',
        '-H', 'Connection: keep-alive',
        '--compressed',
        HANSARD_PAGE
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode == 0:
        content = result.stdout
        
        # Save for debugging
        with open('logs/hansard_page_curl.html', 'w', encoding='utf-8') as f:
            f.write(content)
        
        soup = BeautifulSoup(content, 'html.parser')
        all_hansard_links = []
        
        # Look for all PDF links
        pdf_links = soup.find_all('a', href=re.compile(r'\.pdf$', re.I))
        
        for link in pdf_links:
            href = link.get('href', '')
            text = link.get_text(strip=True)
            
            # Check if it's a hansard
            if 'hansard' in href.lower() or 'hansard' in text.lower():
                # Check for target years
                for year in TARGET_YEARS:
                    if year in href or year in text:
                        absolute_url = urljoin(BASE_URL, href)
                        all_hansard_links.append({
                            'url': absolute_url,
                            'text': text,
                            'year': year
                        })
                        logging.info(f"Found: {text} - {absolute_url}")
                        break
        
        # Also check for year-specific pages
        for year in TARGET_YEARS:
            year_links = soup.find_all('a', href=re.compile(f'{year}', re.I))
            for link in year_links:
                href = link.get('href', '')
                if 'hansard' in href.lower():
                    # This might be a year-specific page, fetch it
                    year_url = urljoin(BASE_URL, href)
                    logging.info(f"Checking year-specific page: {year_url}")
                    
                    year_cmd = cmd[:-1] + [year_url]
                    year_result = subprocess.run(year_cmd, capture_output=True, text=True)
                    
                    if year_result.returncode == 0:
                        year_soup = BeautifulSoup(year_result.stdout, 'html.parser')
                        year_pdfs = year_soup.find_all('a', href=re.compile(r'\.pdf$', re.I))
                        
                        for pdf_link in year_pdfs:
                            pdf_href = pdf_link.get('href', '')
                            pdf_text = pdf_link.get_text(strip=True)
                            
                            if 'hansard' in pdf_href.lower() or 'hansard' in pdf_text.lower():
                                absolute_url = urljoin(BASE_URL, pdf_href)
                                all_hansard_links.append({
                                    'url': absolute_url,
                                    'text': pdf_text,
                                    'year': year
                                })
                                logging.info(f"Found: {pdf_text} - {absolute_url}")
        
        return all_hansard_links
    
    else:
        logging.error(f"Curl failed: {result.stderr}")
        return []

def main():
    """Main function to orchestrate the scraping"""
    logging.info("Starting Fiji Parliament Hansard Scraper for 2022-2024...")
    
    processed = load_processed_hansards()
    new_hansards = []
    
    # Try Selenium first, then fall back to curl
    all_hansard_links = scrape_with_selenium()
    
    if not all_hansard_links:
        all_hansard_links = scrape_with_curl_fallback()
    
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
        if not filename or not filename.endswith('.pdf'):
            continue
        
        # Skip if already processed
        if filename in processed:
            logging.info(f"Already processed: {filename}")
            continue
        
        logging.info(f"Downloading: {filename}")
        
        # Download
        pdf_path = os.path.join('pdf_hansards', filename)
        
        if download_with_curl(url, pdf_path):
            logging.info(f"Successfully downloaded {filename}")
            
            processed[filename] = {
                'url': url,
                'download_date': datetime.now().isoformat(),
                'text': link_info.get('text', ''),
                'year': link_info.get('year', '')
            }
            
            new_hansards.append(filename)
            save_processed_hansards(processed)
            
            # Be polite
            time.sleep(2)
        else:
            logging.error(f"Failed to download {filename}")
    
    # Summary
    logging.info(f"\nScraping complete!")
    logging.info(f"New hansards downloaded: {len(new_hansards)}")
    if new_hansards:
        logging.info("New files:")
        for file in sorted(new_hansards):
            logging.info(f"  - {file}")
    else:
        logging.info("\nNo new hansards found. The dynamic tabs might require JavaScript.")
        logging.info("Check logs/hansard_page_selenium.html or logs/hansard_page_curl.html for debugging")
        logging.info("\nManual URLs to check:")
        for year in TARGET_YEARS:
            logging.info(f"  - {HANSARD_PAGE}?year={year}")
            logging.info(f"  - {BASE_URL}/hansard/{year}/")
    
    return new_hansards

if __name__ == "__main__":
    main()