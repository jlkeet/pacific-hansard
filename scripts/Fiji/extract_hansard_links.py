#!/usr/bin/env python3
"""
Extract all hansard PDF links from the Fiji Parliament website
"""

import requests
from bs4 import BeautifulSoup
import json
import re
from datetime import datetime
import time

def fetch_hansard_page():
    """Fetch the main hansard page and extract all PDF links"""
    url = "https://www.parliament.gov.fj/hansard/"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    }
    
    print(f"Fetching: {url}")
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        print(f"Successfully fetched page ({len(response.content)} bytes)")
        return response.text
        
    except Exception as e:
        print(f"Error fetching page: {e}")
        return None

def extract_pdf_links(html_content):
    """Extract all PDF links from the HTML content"""
    if not html_content:
        return []
    
    soup = BeautifulSoup(html_content, 'html.parser')
    pdf_links = []
    
    # Find all links that point to PDF files
    for link in soup.find_all('a', href=True):
        href = link.get('href')
        
        if href and href.lower().endswith('.pdf'):
            # Make sure it's a full URL
            if not href.startswith('http'):
                if href.startswith('/'):
                    href = f"https://www.parliament.gov.fj{href}"
                else:
                    href = f"https://www.parliament.gov.fj/{href}"
            
            # Check if it looks like a hansard document
            filename = href.split('/')[-1]
            if any(keyword in filename.lower() for keyword in ['hansard', 'dh-', 'daily']):
                
                # Try to extract year from the URL or filename
                year_match = re.search(r'20(22|23|24)', href)
                if year_match:
                    year = f"20{year_match.group(1)}"
                    
                    # Get link text for additional context
                    link_text = link.get_text(strip=True)
                    
                    pdf_links.append({
                        'url': href,
                        'filename': filename,
                        'year': year,
                        'link_text': link_text
                    })
    
    return pdf_links

def filter_target_years(pdf_links, target_years=['2022', '2023', '2024']):
    """Filter PDF links for target years"""
    filtered = []
    for pdf in pdf_links:
        if pdf['year'] in target_years:
            filtered.append(pdf)
    
    return filtered

def main():
    """Main function"""
    print("Fiji Parliament Hansard Link Extractor")
    print("=" * 50)
    
    # Fetch the page
    html_content = fetch_hansard_page()
    if not html_content:
        print("Failed to fetch the page")
        return
    
    # Extract PDF links
    print("\nExtracting PDF links...")
    all_pdf_links = extract_pdf_links(html_content)
    print(f"Found {len(all_pdf_links)} total PDF links")
    
    # Filter for target years
    target_links = filter_target_years(all_pdf_links)
    print(f"Found {len(target_links)} PDFs from 2022-2024")
    
    # Group by year
    by_year = {}
    for pdf in target_links:
        year = pdf['year']
        if year not in by_year:
            by_year[year] = []
        by_year[year].append(pdf)
    
    # Display results
    print("\nSummary by year:")
    for year in sorted(by_year.keys()):
        pdfs = by_year[year]
        print(f"  {year}: {len(pdfs)} PDFs")
        
        # Show first few examples
        for i, pdf in enumerate(pdfs[:3]):
            print(f"    - {pdf['filename']}")
        if len(pdfs) > 3:
            print(f"    ... and {len(pdfs) - 3} more")
    
    # Save to file
    output_file = 'fiji_hansard_links_2022_2024.json'
    with open(output_file, 'w') as f:
        json.dump({
            'extraction_date': datetime.now().isoformat(),
            'total_links': len(target_links),
            'links_by_year': by_year,
            'all_links': target_links
        }, f, indent=2)
    
    print(f"\nSaved results to: {output_file}")
    print(f"\nFound {len(target_links)} hansard PDFs to download from 2022-2024")
    
    return target_links

if __name__ == "__main__":
    links = main()