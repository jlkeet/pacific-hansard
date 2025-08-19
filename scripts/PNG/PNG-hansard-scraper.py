#!/usr/bin/env python3
"""
Papua New Guinea Parliament Hansard Scraper
Automated scraper to collect PNG Parliament hansard documents
Based on Fiji and Cook Islands scraper patterns
"""

import requests
import re
import os
import logging
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import time
import json
from urllib.parse import urljoin, urlparse

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/png_hansard_scraper.log'),
        logging.StreamHandler()
    ]
)

# Configuration
PNG_PARLIAMENT_BASE_URL = "https://www.parliament.gov.pg"
PNG_HANSARD_URL = "https://www.parliament.gov.pg/hansard"
DOWNLOAD_DIR = "pdf_hansards"
HTML_DIR = "html_hansards" 
PROCESSED_DIR = "processed_hansards"
DATA_FILE = "data/png_processed_hansards.json"

# Create directories
for directory in [DOWNLOAD_DIR, HTML_DIR, PROCESSED_DIR, "logs", "data"]:
    os.makedirs(directory, exist_ok=True)

class PNGHansardScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        self.processed_hansards = self.load_processed_hansards()
    
    def load_processed_hansards(self):
        """Load list of already processed hansards"""
        try:
            with open(DATA_FILE, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}
    
    def save_processed_hansards(self):
        """Save list of processed hansards"""
        with open(DATA_FILE, 'w') as f:
            json.dump(self.processed_hansards, f, indent=2)
    
    def fetch_hansard_links(self):
        """Fetch hansard document links from PNG Parliament website"""
        try:
            logging.info(f"Fetching hansard links from {PNG_HANSARD_URL}")
            response = self.session.get(PNG_HANSARD_URL, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Look for PDF links - adjust selectors based on actual PNG Parliament website structure
            pdf_links = []
            
            # Common patterns for hansard links
            selectors = [
                'a[href*=".pdf"]',
                'a[href*="hansard"]',
                'a[href*="daily"]',
                'a[href*="proceedings"]'
            ]
            
            for selector in selectors:
                links = soup.select(selector)
                for link in links:
                    href = link.get('href')
                    if href and self.is_hansard_link(href, link.get_text()):
                        full_url = urljoin(PNG_PARLIAMENT_BASE_URL, href)
                        link_text = link.get_text(strip=True)
                        
                        pdf_links.append({
                            'url': full_url,
                            'text': link_text,
                            'filename': self.generate_filename(href, link_text)
                        })
            
            logging.info(f"Found {len(pdf_links)} potential hansard links")
            return pdf_links
            
        except Exception as e:
            logging.error(f"Error fetching hansard links: {e}")
            return []
    
    def is_hansard_link(self, href, link_text):
        """Check if a link is likely a hansard document"""
        href_lower = href.lower()
        text_lower = link_text.lower()
        
        # PNG-specific patterns
        hansard_indicators = [
            'hansard', 'daily', 'proceedings', 'sitting',
            'parliament', 'debate', 'session'
        ]
        
        # Must be PDF and contain hansard indicators
        is_pdf = href_lower.endswith('.pdf')
        has_indicator = any(indicator in href_lower or indicator in text_lower 
                           for indicator in hansard_indicators)
        
        # Exclude certain types
        excludes = ['annual', 'budget', 'committee', 'notice']
        has_exclude = any(exclude in href_lower or exclude in text_lower 
                         for exclude in excludes)
        
        return is_pdf and has_indicator and not has_exclude
    
    def generate_filename(self, href, link_text):
        """Generate a standardized filename for PNG hansards"""
        # Extract date if possible
        date_match = re.search(r'(\d{4})-?(\d{2})-?(\d{2})', href + link_text)
        if date_match:
            year, month, day = date_match.groups()
            date_str = f"{year}{month}{day}"
        else:
            # Fallback to current date
            date_str = datetime.now().strftime('%Y%m%d')
        
        # Create filename
        base_name = re.sub(r'[^\w\-_.]', '-', link_text.strip())
        if not base_name.endswith('.pdf'):
            base_name += '.pdf'
        
        return f"PNG-Hansard-{date_str}-{base_name}"
    
    def download_pdf(self, pdf_info):
        """Download a PDF hansard document"""
        url = pdf_info['url']
        filename = pdf_info['filename']
        filepath = os.path.join(DOWNLOAD_DIR, filename)
        
        # Skip if already downloaded
        if os.path.exists(filepath):
            logging.info(f"File already exists: {filename}")
            return filepath
        
        if filename in self.processed_hansards:
            logging.info(f"File already processed: {filename}")
            return None
        
        try:
            logging.info(f"Downloading: {filename}")
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            with open(filepath, 'wb') as f:
                f.write(response.content)
            
            logging.info(f"Downloaded: {filename} ({len(response.content)} bytes)")
            return filepath
            
        except Exception as e:
            logging.error(f"Error downloading {filename}: {e}")
            return None
    
    def convert_pdf_to_html(self, pdf_path):
        """Convert PDF to HTML using OCR"""
        try:
            # Use the existing PNG OCR scripts
            import sys
            sys.path.append('.')
            
            # Import OCR conversion functions
            from png_pdf_converter import convert_from_path
            import pytesseract
            import html
            
            # Convert PDF pages to images
            pages = convert_from_path(pdf_path)
            
            # Use pytesseract to do OCR on each page
            text_pages = [pytesseract.image_to_string(page) for page in pages]
            
            # Combine text from all pages into a single HTML document
            html_content = "<html>\n<head>\n<title>PNG Hansard</title>\n</head>\n<body>\n"
            for page_number, text in enumerate(text_pages, start=1):
                escaped_text = html.escape(text).replace('\n', '<br>')
                html_content += f"<h2>Page {page_number}</h2>\n<p>{escaped_text}</p>\n"
            
            html_content += "</body>\n</html>"
            
            # Save HTML file
            base_name = os.path.splitext(os.path.basename(pdf_path))[0]
            html_path = os.path.join(HTML_DIR, f"{base_name}.html")
            
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            logging.info(f"Converted PDF to HTML: {html_path}")
            return html_path
            
        except Exception as e:
            logging.error(f"Error converting PDF to HTML: {e}")
            return None
    
    def process_hansard(self, html_path):
        """Process hansard using the integrated converter"""
        try:
            # Import and use the integrated PNG converter
            import sys
            sys.path.append('.')
            
            from PNG_hansard_converter_integrated import process_png_hansard
            
            output_dir, metadata = process_png_hansard(html_path)
            
            # Move processed file
            base_name = os.path.basename(html_path)
            processed_path = os.path.join(PROCESSED_DIR, base_name)
            os.rename(html_path, processed_path)
            
            # Record as processed
            self.processed_hansards[base_name] = {
                'processed_date': datetime.now().isoformat(),
                'output_directory': output_dir,
                'metadata': metadata
            }
            
            logging.info(f"Processed hansard: {base_name} -> {output_dir}")
            return output_dir
            
        except Exception as e:
            logging.error(f"Error processing hansard {html_path}: {e}")
            return None
    
    def scrape_recent_hansards(self, days_back=30):
        """Scrape hansards from recent days"""
        logging.info(f"Starting PNG hansard scraping for last {days_back} days")
        
        try:
            # Fetch available hansard links
            pdf_links = self.fetch_hansard_links()
            
            if not pdf_links:
                logging.warning("No hansard links found")
                return
            
            processed_count = 0
            
            for pdf_info in pdf_links:
                try:
                    # Download PDF
                    pdf_path = self.download_pdf(pdf_info)
                    if not pdf_path:
                        continue
                    
                    # Convert to HTML
                    html_path = self.convert_pdf_to_html(pdf_path)
                    if not html_path:
                        continue
                    
                    # Process hansard
                    output_dir = self.process_hansard(html_path)
                    if output_dir:
                        processed_count += 1
                    
                    # Save progress
                    self.save_processed_hansards()
                    
                    # Rate limiting
                    time.sleep(2)
                    
                except Exception as e:
                    logging.error(f"Error processing {pdf_info.get('filename', 'unknown')}: {e}")
                    continue
            
            logging.info(f"PNG scraping completed. Processed {processed_count} new hansards.")
            
        except Exception as e:
            logging.error(f"Error in scrape_recent_hansards: {e}")
    
    def daily_check(self):
        """Daily check for new hansards"""
        logging.info("Running daily PNG hansard check")
        self.scrape_recent_hansards(days_back=7)

def main():
    """Main function"""
    scraper = PNGHansardScraper()
    
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == '--daily':
        scraper.daily_check()
    else:
        scraper.scrape_recent_hansards()

if __name__ == "__main__":
    main()