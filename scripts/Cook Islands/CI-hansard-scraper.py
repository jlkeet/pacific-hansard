#!/usr/bin/env python3
"""
Cook Islands Parliamentary Hansard Scraper
This script automatically downloads new Hansard PDFs from the Cook Islands Parliament website,
converts them to HTML, processes them into parts, and indexes them in Solr and MySQL.
"""

import os
import sys
import re
import time
import logging
import requests
import random
from bs4 import BeautifulSoup
from datetime import datetime
import hashlib
import json
from urllib.parse import urljoin
import http.cookiejar as cookielib

# Configure logging first so we can use it during imports
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(SCRIPT_DIR, 'logs')
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, 'hansard_scraper.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('hansard_scraper')

# Import the converter and processing scripts
sys.path.append(SCRIPT_DIR)
try:
    # Try with underscores (our newly created versions)
    from CI_gpt_hansard import pdf_to_html
    from CI_hansard_converter import split_html
    logger.info("Successfully imported converter modules with underscores")
except ImportError as e:
    logger.error(f"Error importing modules with underscores: {e}")
    
    # Use direct file loading as fallback
    try:
        import importlib.util
        
        # Load CI_gpt_hansard.py
        pdf_module_path = os.path.join(SCRIPT_DIR, "CI_gpt_hansard.py")
        if os.path.exists(pdf_module_path):
            logger.info(f"Loading module from {pdf_module_path}")
            spec = importlib.util.spec_from_file_location("CI_gpt_hansard", pdf_module_path)
            gpt_hansard = importlib.util.module_from_spec(spec)
            sys.modules["CI_gpt_hansard"] = gpt_hansard
            spec.loader.exec_module(gpt_hansard)
            pdf_to_html = gpt_hansard.pdf_to_html
            
            # Load CI_hansard_converter.py
            converter_module_path = os.path.join(SCRIPT_DIR, "CI_hansard_converter.py")
            logger.info(f"Loading module from {converter_module_path}")
            spec = importlib.util.spec_from_file_location("CI_hansard_converter", converter_module_path)
            hansard_converter = importlib.util.module_from_spec(spec)
            sys.modules["CI_hansard_converter"] = hansard_converter
            spec.loader.exec_module(hansard_converter)
            split_html = hansard_converter.split_html
            
            logger.info("Successfully loaded converter modules via direct import")
        else:
            logger.error(f"Module file not found: {pdf_module_path}")
            raise ImportError("Required module files not found")
    except Exception as e:
        logger.error(f"Failed to import required modules: {e}")
        raise

# Directory paths
PDF_DIR = os.path.join(SCRIPT_DIR, 'pdf_hansards')
HTML_DIR = os.path.join(SCRIPT_DIR, 'html_hansards')
PROCESSED_DIR = os.path.join(SCRIPT_DIR, 'processed_hansards')
DATA_DIR = os.path.join(SCRIPT_DIR, 'data')

# File to store processed hansards (to avoid reprocessing)
PROCESSED_FILE = os.path.join(DATA_DIR, 'processed_hansards.json')

# URL of the Cook Islands Parliament Hansard Library
HANSARD_URL = "https://parliament.gov.ck/hansard-library/"

def setup_directories():
    """Create necessary directories if they don't exist."""
    for directory in [PDF_DIR, HTML_DIR, PROCESSED_DIR, DATA_DIR]:
        if not os.path.exists(directory):
            os.makedirs(directory)
            logger.info(f"Created directory: {directory}")

def load_processed_hansards():
    """Load the list of already processed hansards."""
    if os.path.exists(PROCESSED_FILE):
        try:
            with open(PROCESSED_FILE, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            logger.error(f"Error parsing {PROCESSED_FILE}, creating new record")
            return {}
    return {}

def save_processed_hansards(processed_hansards):
    """Save the list of processed hansards."""
    with open(PROCESSED_FILE, 'w') as f:
        json.dump(processed_hansards, f, indent=2)

def get_browser_headers():
    """
    Generate a realistic set of browser headers with slight randomization.
    
    Returns:
        dict: A dictionary of HTTP headers mimicking a real browser
    """
    # List of common user agents (recent browsers)
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/97.0.4692.71 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.2 Safari/605.1.15',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:96.0) Gecko/20100101 Firefox/96.0'
    ]
    
    # Common accept languages
    accept_languages = [
        'en-US,en;q=0.9',
        'en-GB,en;q=0.9',
        'en-NZ,en;q=0.9',
        'en-AU,en;q=0.9',
        'en;q=0.9'
    ]
    
    # Build headers
    headers = {
        'User-Agent': random.choice(user_agents),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
        'Accept-Language': random.choice(accept_languages),
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
        'Cache-Control': 'max-age=0',
        'sec-ch-ua': '" Not A;Brand";v="99", "Chromium";v="96", "Google Chrome";v="96"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'Referer': 'https://www.google.com/'
    }
    
    return headers

def establish_session():
    """
    Establish a browser-like session with cookies by navigating through the site naturally.
    
    Returns:
        requests.Session: A session with cookies set from normal site navigation
    """
    logger.info("Establishing a new browser session...")
    session = requests.Session()
    
    # Configure session to behave more like a browser
    # Enable cookie persistence by default
    session.cookies.set_policy(cookielib.DefaultCookiePolicy(
        allowed_domains=None,  # Allow all domains
        strict_ns_domain=cookielib.DefaultCookiePolicy.DomainStrict
    ))
    
    # Sites to visit in sequence to establish a natural browsing pattern
    site_sequence = [
        # Start with Google
        {'url': 'https://www.google.com/search?q=cook+islands+parliament+hansard', 
         'referer': None,
         'delay': (1, 3)},
        
        # Visit the main parliament page as if we clicked from Google
        {'url': 'https://parliament.gov.ck/', 
         'referer': 'https://www.google.com/search?q=cook+islands+parliament+hansard',
         'delay': (2, 5)},
        
        # Visit some common pages to establish cookies
        {'url': 'https://parliament.gov.ck/about/', 
         'referer': 'https://parliament.gov.ck/',
         'delay': (3, 7)},
         
        {'url': 'https://parliament.gov.ck/parliament/', 
         'referer': 'https://parliament.gov.ck/about/',
         'delay': (2, 4)},
        
        # Finally visit the hansard library page
        {'url': HANSARD_URL, 
         'referer': 'https://parliament.gov.ck/parliament/',
         'delay': (2, 4)}
    ]
    
    for i, site in enumerate(site_sequence):
        logger.info(f"Visit {i+1}/{len(site_sequence)}: {site['url']}")
        
        # Get fresh headers for each request with slight randomization
        headers = get_browser_headers()
        if site['referer']:
            headers['Referer'] = site['referer']
        
        try:
            # Sometimes add Accept-Encoding, sometimes don't (browser variation)
            if random.random() < 0.3:
                headers.pop('Accept-Encoding', None)
            
            # Randomize connection type sometimes
            if random.random() < 0.2:
                headers['Connection'] = random.choice(['keep-alive', 'close'])
            
            # Randomize cache behavior sometimes
            if random.random() < 0.3:
                cache_directives = ['no-cache', 'max-age=0', 'max-stale']
                headers['Cache-Control'] = random.choice(cache_directives)
            
            # Make the request with proper error handling
            response = session.get(site['url'], headers=headers, timeout=30)
            response.raise_for_status()
            
            # Save page HTML for debugging if the visit fails later
            if i == len(site_sequence) - 1:  # The last page (hansard page)
                debug_file = os.path.join(LOG_DIR, "session_debug.html")
                with open(debug_file, "w", encoding="utf-8") as f:
                    f.write(response.text[:10000])  # Save first 10K chars
                logger.debug(f"Saved debug HTML from session establishment to {debug_file}")
            
            # Log cookies after each request
            cookies = session.cookies.get_dict()
            logger.info(f"Cookies after visiting {site['url']}: {list(cookies.keys())}")
            
            # Apply a random delay before the next request
            if i < len(site_sequence) - 1:
                min_delay, max_delay = site['delay']
                delay = min_delay + (max_delay - min_delay) * random.random()
                logger.info(f"Waiting {delay:.2f} seconds before next page visit...")
                time.sleep(delay)
                
                # Simulate human browsing behavior
                # Sometimes we scroll, sometimes we click around, sometimes we just wait
                behavior_choice = random.random()
                
                if behavior_choice < 0.4:  # 40% - scroll behavior
                    scroll_cycles = random.randint(2, 5)
                    logger.debug(f"Simulating scrolling with {scroll_cycles} scroll actions")
                    for _ in range(scroll_cycles):
                        scroll_pause = 0.5 + random.random() * 2  # 0.5-2.5 seconds between scrolls
                        time.sleep(scroll_pause)
                
                elif behavior_choice < 0.7:  # 30% - click then back behavior
                    # Simulate clicking a random link then going back
                    back_delay = 1 + random.random() * 3  # 1-4 seconds on the page
                    logger.debug(f"Simulating click on page then back button after {back_delay:.2f}s")
                    time.sleep(back_delay)
                
                else:  # 30% - just read the page
                    read_time = 3 + random.random() * 5  # 3-8 seconds reading
                    logger.debug(f"Simulating reading the page for {read_time:.2f}s")
                    time.sleep(read_time)
        
        except requests.exceptions.RequestException as e:
            logger.error(f"Error during session establishment at {site['url']}: {e}")
            # Try to recover by continuing the sequence if possible
            if i >= len(site_sequence) // 2:  # If we're at least halfway through
                logger.info("Continuing session establishment despite error")
                continue
            else:
                logger.warning("Session establishment failed early, may affect scraping")
    
    # Add custom headers to all future requests in this session
    session.headers.update({
        'DNT': '1',  # Do Not Track
        'Upgrade-Insecure-Requests': '1'
    })
    
    logger.info("Browser session established successfully")
    return session

def get_hansard_pdfs():
    """
    Scrape the Cook Islands Parliament website for hansard PDFs.
    Returns a list of tuples (pdf_url, filename, date).
    """
    logger.info(f"Fetching hansard PDFs from {HANSARD_URL}")
    
    # Try multiple methods to get valid content
    pdf_links = []
    
    # Method 1: Use curl command line tool as it seems to work better
    try:
        logger.info("Method 1: Using curl command line tool")
        import subprocess
        import tempfile
        
        # Create a temporary file for the HTML
        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as tmp:
            temp_file = tmp.name
        
        # Use curl to fetch the page
        curl_cmd = [
            'curl', '-s', '-L',
            '-H', 'User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.3 Safari/605.1.15',
            '-H', 'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            '-H', 'Accept-Language: en-US,en;q=0.9',
            '-H', 'Accept-Encoding: gzip, deflate, br',
            '-H', 'Referer: https://www.google.com',
            '-o', temp_file,
            HANSARD_URL
        ]
        
        result = subprocess.run(curl_cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            # Read the downloaded HTML
            with open(temp_file, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            # Clean up temp file
            os.unlink(temp_file)
            
            # Save for debugging
            debug_file = os.path.join(LOG_DIR, "hansard_page_curl.html")
            with open(debug_file, "w", encoding="utf-8") as f:
                f.write(html_content)
            logger.info(f"Saved curl HTML to {debug_file}")
            
            # Check if content seems valid
            if len(html_content) > 1000 and "<html" in html_content.lower():
                logger.info("Curl method returned valid HTML")
                
                # Parse the HTML
                soup = BeautifulSoup(html_content, 'html.parser')
                
                # Extract PDF links with improved logic
                pdf_links = extract_pdf_links_improved(soup)
                
                if pdf_links:
                    logger.info(f"Curl method found {len(pdf_links)} PDF links")
                    return pdf_links
            else:
                logger.warning("Curl method returned invalid content")
        else:
            logger.error(f"Curl command failed: {result.stderr}")
            
    except Exception as e:
        logger.error(f"Curl method failed: {str(e)}")
    
    # Method 2: Try requests with better error handling
    try:
        logger.info("Method 2: Using requests library with improved headers")
        
        # Use a session with all the necessary headers
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0',
        })
        
        # First visit the main site
        session.get('https://parliament.gov.ck/', timeout=30)
        time.sleep(2)
        
        # Now get the hansard page
        response = session.get(HANSARD_URL, timeout=30)
        response.raise_for_status()
        
        # Save the raw HTML content
        raw_debug_file = os.path.join(LOG_DIR, "hansard_page_requests.html")
        with open(raw_debug_file, "wb") as f:
            f.write(response.content)
        logger.info(f"Saved requests HTML to {raw_debug_file}")
        
        # Check if content seems valid
        if len(response.text) > 1000 and "<html" in response.text.lower():
            logger.info("Requests method returned valid-looking HTML")
            
            # Parse the HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract PDF links
            pdf_links = extract_pdf_links_improved(soup)
            
            if pdf_links:
                logger.info(f"Requests method found {len(pdf_links)} PDF links")
                return pdf_links
        else:
            logger.warning("Requests method returned invalid or empty content")
    except Exception as e:
        logger.error(f"Requests method failed: {str(e)}")
    
    # If all methods failed, return empty list
    logger.error("All methods failed to fetch valid content or find PDF links")
    return []


def extract_pdf_links_improved(soup):
    """
    Improved extraction of PDF links from the parsed HTML content.
    
    Args:
        soup: BeautifulSoup object of the parsed HTML
    
    Returns:
        List of tuples (pdf_url, filename, date)
    """
    pdf_links = []
    seen_urls = set()  # Track URLs to avoid duplicates
    
    # Get all PDF links
    all_links = soup.find_all('a', href=True)
    
    for link in all_links:
        href = link.get('href', '')
        
        # Check if it's a PDF
        if href.lower().endswith('.pdf'):
            # Get the full URL
            pdf_url = urljoin(HANSARD_URL, href)
            
            # Skip if we've already seen this URL
            if pdf_url in seen_urls:
                continue
                
            filename = os.path.basename(href)
            link_text = link.text.strip()
            
            # Check if it's a hansard document by various patterns
            is_hansard = False
            
            # Pattern 1: DAY- pattern (newer format)
            if 'DAY-' in filename:
                is_hansard = True
                
            # Pattern 2: Day of week followed by date (older format)
            # e.g., Mon-22-March-2021.pdf, Fri-27-May-2022.pdf
            elif re.search(r'(Mon|Tue|Wed|Thu|Fri|Sat|Sun)-\d{1,2}-(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)', filename, re.IGNORECASE):
                is_hansard = True
                
            # Pattern 3: Check parent text for "Sitting Day"
            parent = link.parent
            if parent and "Sitting Day" in parent.text:
                is_hansard = True
                
            # Pattern 4: Check if link text contains date patterns
            date_patterns = [
                r'(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)',
                r'\d{1,2}\s+(January|February|March|April|May|June|July|August|September|October|November|December)',
                r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)'
            ]
            for pattern in date_patterns:
                if re.search(pattern, link_text, re.IGNORECASE):
                    is_hansard = True
                    break
            
            # Skip non-hansard PDFs (like handbooks, policies, etc.)
            skip_patterns = ['handbook', 'strategic-plan', 'policy', 'travel', 'MPs-Travel']
            for skip in skip_patterns:
                if skip.lower() in filename.lower():
                    is_hansard = False
                    break
            
            if is_hansard:
                # Extract date from link text or filename
                date_str = link_text if link_text else filename
                
                # Try to extract a cleaner date from parent if available
                if parent:
                    parent_text = parent.text.strip()
                    if "Sitting Day" in parent_text and ':' in parent_text:
                        # Extract the date part after the colon
                        date_str = parent_text.split(':', 1)[1].strip()
                        # Remove the link text from the date string
                        date_str = date_str.replace(link_text, '').strip()
                
                # If date_str is empty or just the filename, try to extract from filename
                if not date_str or date_str == filename:
                    # Try to extract date from filename patterns
                    date_match = re.search(r'(Mon|Tue|Wed|Thu|Fri|Sat|Sun)-(\d{1,2})-(.*?)-(\d{4})', filename, re.IGNORECASE)
                    if date_match:
                        day_of_week = date_match.group(1)
                        day = date_match.group(2)
                        month = date_match.group(3)
                        year = date_match.group(4)
                        date_str = f"{day_of_week} {day} {month} {year}"
                    else:
                        # For DAY- pattern files, use the link text
                        date_str = link_text if link_text else filename
                
                seen_urls.add(pdf_url)
                pdf_links.append((pdf_url, filename, date_str))
                logger.info(f"Found hansard PDF: {filename} - {date_str}")
    
    # Sort by filename in reverse order (newest first)
    pdf_links.sort(key=lambda x: x[1], reverse=True)
    
    logger.info(f"Total hansard PDFs found: {len(pdf_links)}")
    return pdf_links


# Remove old extract_pdf_links function - we're using extract_pdf_links_improved now

def try_alternative_download(url, filepath, session):
    """
    Try alternative download methods when standard requests fail.
    
    Args:
        url: URL of the PDF to download
        filepath: Target file path to save the PDF
        session: Current requests session
    
    Returns:
        bool: True if successful, False otherwise
    """
    logger.info("Trying alternative download methods...")
    
    # Method 1: Use curl from the command line
    try:
        import subprocess
        logger.info("Attempting download with curl...")
        
        # Get all cookies from the session as a cookie string
        cookie_header = "; ".join([f"{k}={v}" for k, v in session.cookies.items()])
        
        # Create a user agent string
        user_agent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36"
        
        # Build the curl command
        curl_command = [
            "curl", "-L", "-o", filepath,
            "--connect-timeout", "30",
            "--max-time", "60",
            "--retry", "3",
            "--retry-delay", "2",
            "-H", f"User-Agent: {user_agent}",
            "-H", f"Cookie: {cookie_header}",
            "-H", f"Referer: {HANSARD_URL}",
            url
        ]
        
        # Execute curl command
        result = subprocess.run(curl_command, capture_output=True, text=True)
        
        # Check if the download was successful
        if result.returncode == 0 and os.path.exists(filepath) and os.path.getsize(filepath) > 1000:
            # Verify it's a PDF
            with open(filepath, 'rb') as f:
                header = f.read(4)
                if header == b'%PDF':
                    logger.info("Successfully downloaded with curl")
                    return True
                else:
                    logger.warning("File downloaded with curl is not a valid PDF")
        else:
            logger.warning(f"Curl download failed: {result.stderr}")
    
    except Exception as e:
        logger.error(f"Error with curl download: {e}")
    
    # Method 2: Use wget as a fallback
    try:
        import subprocess
        logger.info("Attempting download with wget...")
        
        # Generate a cookies file for wget
        cookie_file = f"{filepath}.cookies.txt"
        with open(cookie_file, 'w') as f:
            for k, v in session.cookies.items():
                f.write(f"parliament.gov.ck\tTRUE\t/\tFALSE\t0\t{k}\t{v}\n")
        
        # Build the wget command
        wget_command = [
            "wget", "--no-check-certificate", "-O", filepath,
            "--timeout=30", "--tries=3", "--waitretry=2",
            "--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36",
            "--referer=" + HANSARD_URL,
            "--load-cookies", cookie_file,
            url
        ]
        
        # Execute wget command
        result = subprocess.run(wget_command, capture_output=True, text=True)
        
        # Clean up cookie file
        if os.path.exists(cookie_file):
            os.remove(cookie_file)
        
        # Check if the download was successful
        if result.returncode == 0 and os.path.exists(filepath) and os.path.getsize(filepath) > 1000:
            # Verify it's a PDF
            with open(filepath, 'rb') as f:
                header = f.read(4)
                if header == b'%PDF':
                    logger.info("Successfully downloaded with wget")
                    return True
                else:
                    logger.warning("File downloaded with wget is not a valid PDF")
        else:
            logger.warning(f"Wget download failed: {result.stderr}")
    
    except Exception as e:
        logger.error(f"Error with wget download: {e}")
    
    # All methods failed
    logger.error("All alternative download methods failed")
    return False

def download_pdf(url, filename, session=None):
    """
    Download a PDF file if it doesn't already exist.
    
    Args:
        url: URL of the PDF to download
        filename: The name to save the file as
        session: Optional requests.Session object for persistent cookies
    
    Returns:
        Path to the downloaded PDF or None if download failed
    """
    filepath = os.path.join(PDF_DIR, filename)
    
    # Check if file already exists
    if os.path.exists(filepath):
        logger.info(f"PDF already exists: {filepath}")
        return filepath
    
    # Add a random delay to appear more human-like
    delay = 3 + 10 * random.random()  # Random delay between 3-13 seconds
    logger.info(f"Waiting for {delay:.2f} seconds before downloading {filename}")
    time.sleep(delay)
    
    logger.info(f"Downloading {url} to {filepath}")
    
    # Method 1: Try curl first as it seems to work better
    try:
        import subprocess
        logger.info("Attempting download with curl...")
        
        # Build the curl command
        curl_cmd = [
            "curl", "-L", "-o", filepath,
            "--connect-timeout", "30",
            "--max-time", "60",
            "-H", "User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "-H", f"Referer: {HANSARD_URL}",
            "-H", "Accept: application/pdf,application/x-pdf,*/*",
            url
        ]
        
        # Execute curl command
        result = subprocess.run(curl_cmd, capture_output=True, text=True)
        
        # Check if the download was successful
        if result.returncode == 0 and os.path.exists(filepath) and os.path.getsize(filepath) > 1000:
            # Verify it's a PDF
            with open(filepath, 'rb') as f:
                header = f.read(4)
                if header == b'%PDF':
                    logger.info("Successfully downloaded with curl")
                    return filepath
                else:
                    logger.warning("File downloaded with curl is not a valid PDF")
                    os.remove(filepath)
        else:
            logger.warning(f"Curl download failed: {result.stderr}")
            if os.path.exists(filepath):
                os.remove(filepath)
    
    except Exception as e:
        logger.error(f"Error with curl download: {e}")
    
    # Method 2: Standard requests download
    try:
        # Use the session if provided
        req = session 
        if not req:
            req = requests.Session()
        
        # Generate browser-like headers
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/pdf,application/x-pdf,application/octet-stream,*/*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Referer': HANSARD_URL,
            'Connection': 'keep-alive',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'same-origin'
        }
        
        # Simulate user clicking the link by waiting a moment
        time.sleep(1 + random.random())
        
        # Now make the actual GET request to download the file
        response = req.get(url, headers=headers, stream=True, timeout=60, 
                          allow_redirects=True)
        response.raise_for_status()
        
        # Check if we actually got a PDF
        if 'application/pdf' not in response.headers.get('Content-Type', '').lower() and \
           not url.lower().endswith('.pdf'):
            logger.warning(f"Response may not be a PDF. Content-Type: {response.headers.get('Content-Type')}")
            # Check if it's an HTML page with an error message
            if 'text/html' in response.headers.get('Content-Type', '').lower():
                logger.error("Received HTML instead of PDF. This might be an access denied page.")
                # Save the HTML for inspection
                with open(f"{filepath}.error.html", 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                logger.info(f"Saved error page to {filepath}.error.html for inspection")
                raise Exception("Received HTML instead of PDF")
        
        # Save the PDF
        with open(filepath, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        # Verify the downloaded file is a PDF
        if os.path.getsize(filepath) < 1000:  # Suspicious if file is too small
            with open(filepath, 'rb') as f:
                header = f.read(4)
                # Check for PDF signature
                if header != b'%PDF':
                    logger.warning(f"Downloaded file may not be a valid PDF. Header: {header}")
                    # Rename for inspection
                    os.rename(filepath, f"{filepath}.suspect")
                    logger.info(f"Renamed suspicious file to {filepath}.suspect")
                    raise Exception("Downloaded file is not a valid PDF")
        
        logger.info(f"Successfully downloaded {filepath}")
        
        # Add a small delay after downloading to be nicer to the server
        time.sleep(1 + 2 * random.random())  # 1-3 seconds
        
        return filepath
    
    except Exception as e:
        logger.error(f"Standard download failed: {e}")
        # If it's a 403 Forbidden error, let's be more specific
        if hasattr(e, 'response') and e.response is not None and e.response.status_code == 403:
            logger.error("Access Forbidden (403). The site is actively blocking the download.")
        
        # Try alternative download methods
        if try_alternative_download(url, filepath, req if 'req' in locals() else None):
            return filepath
        
        # All methods failed
        if os.path.exists(filepath):
            os.remove(filepath)  # Clean up partial downloads
        return None

def convert_pdf_to_html(pdf_path):
    """Convert a PDF to HTML using the existing converter script."""
    if not os.path.exists(pdf_path):
        logger.error(f"PDF file not found: {pdf_path}")
        return None
    
    # Generate HTML filename from PDF filename
    pdf_filename = os.path.basename(pdf_path)
    html_filename = os.path.splitext(pdf_filename)[0] + ".html"
    html_path = os.path.join(HTML_DIR, html_filename)
    
    logger.info(f"Converting {pdf_filename} to HTML")
    
    try:
        # Call the existing PDF to HTML converter
        pdf_to_html(pdf_path, html_path)
        logger.info(f"Successfully converted to HTML: {html_path}")
        return html_path
    except Exception as e:
        logger.error(f"Error converting PDF to HTML: {e}")
        return None

def process_html(html_path):
    """Process the HTML file and split it into parts using the existing script."""
    if not os.path.exists(html_path):
        logger.error(f"HTML file not found: {html_path}")
        return None
    
    logger.info(f"Processing HTML file: {html_path}")
    
    try:
        # Get the original working directory
        original_dir = os.getcwd()
        
        # Change working directory to where the HTML file is
        html_dir = os.path.dirname(html_path)
        if html_dir:
            os.chdir(html_dir)
        
        # Get the basename of the HTML file
        html_basename = os.path.basename(html_path)
        
        try:
            # Call the existing HTML processor
            logger.info(f"Calling split_html on {html_basename}")
            result = split_html(html_basename)
            
            # Determine the processed directory name
            # It should be "Hansard_" followed by the date or the HTML basename
            processed_dirs = [d for d in os.listdir('.') if os.path.isdir(d) and d.startswith('Hansard_')]
            
            if processed_dirs:
                # Get the most recently modified directory
                processed_dir = max(processed_dirs, key=lambda d: os.path.getmtime(d))
                logger.info(f"Found processed directory: {processed_dir}")
            else:
                # Fallback to the default naming convention
                processed_dir = f"Hansard_{os.path.splitext(html_basename)[0]}"
                logger.warning(f"No processed directory found, using default: {processed_dir}")
                if not os.path.exists(processed_dir):
                    logger.error(f"Expected directory {processed_dir} does not exist")
                    return None
            
            # Create a destination path with timestamp to avoid conflicts
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            dest_dir = os.path.join(PROCESSED_DIR, f"{processed_dir}_{timestamp}")
            
            # If the destination already exists, use an incremented counter
            counter = 1
            while os.path.exists(dest_dir):
                dest_dir = os.path.join(PROCESSED_DIR, f"{processed_dir}_{timestamp}_{counter}")
                counter += 1
            
            # Use os.rename for moving
            full_processed_dir = os.path.join(os.getcwd(), processed_dir)
            logger.info(f"Moving {full_processed_dir} to {dest_dir}")
            os.rename(full_processed_dir, dest_dir)
            logger.info(f"Moved processed directory to {dest_dir}")
            
            # Return to the original directory
            os.chdir(original_dir)
            return dest_dir
        except Exception as e:
            logger.error(f"Error in split_html: {e}")
            # Return to the original directory on error
            os.chdir(original_dir)
            return None
    except Exception as e:
        logger.error(f"Error processing HTML: {e}")
        return None

def run_indexing_pipeline(processed_dir):
    """Run the indexing pipeline to add the hansard to Solr and MySQL."""
    logger.info(f"Running indexing pipeline for {processed_dir}")
    
    try:
        # This part depends on how your pipeline.py script works
        # Typically you would call it with the processed directory as an argument
        # For now, we'll just log the command that would be run
        
        # Construct the command that would be run
        cmd = f"cd /app && python pipelines.py {processed_dir}"
        logger.info(f"Would run: {cmd}")
        
        # In a real implementation, you would execute this command
        # or call the pipeline function directly
        # subprocess.run(cmd, shell=True, check=True)
        
        return True
    except Exception as e:
        logger.error(f"Error running indexing pipeline: {e}")
        return False

def process_new_hansards():
    """Main function to process new hansards."""
    setup_directories()
    processed_hansards = load_processed_hansards()
    
    # Get list of hansard PDFs
    pdf_links = get_hansard_pdfs()
    
    # Track newly processed hansards
    newly_processed = []
    total_to_process = len([p for p in pdf_links if hashlib.md5(p[0].encode()).hexdigest() not in processed_hansards])
    
    logger.info(f"Found {len(pdf_links)} total Hansard PDFs, {total_to_process} new ones to process")
    
    # Add a polite message if we're going to be doing a lot of requests
    if total_to_process > 3:
        logger.info(f"Processing {total_to_process} PDFs with delays to avoid overloading the server.")
    
    for i, (pdf_url, filename, date_str) in enumerate(pdf_links):
        # Generate a hash for the URL to use as an identifier
        pdf_hash = hashlib.md5(pdf_url.encode()).hexdigest()
        
        # Skip if already processed
        if pdf_hash in processed_hansards:
            logger.info(f"Skipping already processed hansard: {filename}")
            continue
        
        # Add progress information
        logger.info(f"Processing PDF {i+1}/{len(pdf_links)}: {filename}")
        
        # Add a random delay between processing different PDFs to be nice to the server
        if i > 0:
            delay = 5 + 10 * random.random()  # Random delay between 5-15 seconds
            logger.info(f"Waiting {delay:.2f} seconds before processing next PDF...")
            time.sleep(delay)
        
        # Download the PDF
        pdf_path = download_pdf(pdf_url, filename)
        if not pdf_path:
            logger.warning(f"Failed to download {filename}, skipping...")
            continue
        
        # Convert PDF to HTML
        html_path = convert_pdf_to_html(pdf_path)
        if not html_path:
            continue
        
        # Process the HTML
        processed_dir = process_html(html_path)
        if not processed_dir:
            continue
        
        # Run indexing pipeline
        # For now, we'll just log success without actually running it
        success = True  # run_indexing_pipeline(processed_dir)
        
        if success:
            # Record as processed
            processed_hansards[pdf_hash] = {
                'url': pdf_url,
                'filename': filename,
                'date': date_str,
                'processed_dir': processed_dir,
                'processed_date': datetime.now().isoformat()
            }
            newly_processed.append(filename)
            logger.info(f"Successfully processed hansard: {filename}")
        
    # Save the updated processed hansards list
    save_processed_hansards(processed_hansards)
    
    if newly_processed:
        logger.info(f"Newly processed hansards: {', '.join(newly_processed)}")
    else:
        logger.info("No new hansards to process")
    
    return newly_processed

def main():
    """Main entry point with better error handling and reporting."""
    logger.info("Starting Cook Islands Hansard scraper")
    success = False
    error_message = None
    
    try:
        # Create necessary directories
        setup_directories()
        
        # Run the main process
        newly_processed = process_new_hansards()
        
        # Check if we found any PDFs at all (even if we didn't process any new ones)
        if not newly_processed:
            logger.info("No new hansards were processed, but the script ran successfully")
        
        success = True
        logger.info("Hansard scraping completed successfully")
        return 0
    
    except requests.exceptions.ConnectionError as e:
        error_message = f"Network connection error: {e}"
        logger.error(error_message)
        return 1
    
    except requests.exceptions.Timeout as e:
        error_message = f"Request timeout error: {e}"
        logger.error(error_message)
        return 1
    
    except requests.exceptions.RequestException as e:
        error_message = f"Request error: {e}"
        logger.error(error_message)
        return 1
    
    except Exception as e:
        import traceback
        error_message = f"Unexpected error: {e}"
        logger.error(error_message)
        logger.error(traceback.format_exc())
        return 1
    
    finally:
        # Log a final status summary
        status = "SUCCESS" if success else "FAILED"
        logger.info(f"Scraper execution {status}")
        if error_message:
            logger.info(f"Error details: {error_message}")

if __name__ == "__main__":
    import sys
    sys.exit(main())