# Cook Islands Hansard Scraper Setup Instructions

## Overview
The Cook Islands Hansard scraper has been updated to:
1. Find ALL hansard PDFs (445+ documents from 1999 to present)
2. Handle both old and new naming patterns (DAY-XX and Mon-DD-Month-YYYY formats)
3. Use curl for downloads to bypass anti-bot protection
4. Include a daily checker for efficient updates

## Initial Setup

### 1. Install Dependencies
```bash
pip install requests beautifulsoup4 pdfminer.six
```

### 2. Initial Full Scrape
To download all historical hansards (445+ PDFs), run:
```bash
cd "/Users/jacksonkeet/Pacific Hansard Development/scripts/Cook Islands"
python3 CI-hansard-scraper.py
```

**Note:** This will take several hours as it processes 445+ PDFs with delays to be respectful to the server.

### 3. Set Up Daily Checking

The daily checker only processes new hansards, making it efficient for regular updates.

#### Option A: Using cron (Recommended)
```bash
# Open crontab editor
crontab -e

# Add this line to run daily at 1:00 AM
0 1 * * * cd "/Users/jacksonkeet/Pacific Hansard Development/scripts/Cook Islands" && bash run_daily_scraper.sh

# Or use the pre-configured entry:
(crontab -l 2>/dev/null; echo '0 1 * * * cd "/Users/jacksonkeet/Pacific Hansard Development/scripts/Cook Islands" && bash run_daily_scraper.sh') | crontab -
```

#### Option B: Manual Daily Check
```bash
cd "/Users/jacksonkeet/Pacific Hansard Development/scripts/Cook Islands"
python3 daily_checker.py
```

## File Structure

### Scripts
- `CI-hansard-scraper.py` - Main scraper (processes all hansards)
- `daily_checker.py` - Efficient daily checker (only new hansards)
- `run_daily_scraper.sh` - Shell wrapper for cron
- `CI_gpt_hansard.py` - PDF to HTML converter
- `CI_hansard_converter.py` - HTML splitter/processor

### Directories
- `pdf_hansards/` - Downloaded PDF files
- `html_hansards/` - Converted HTML files
- `processed_hansards/` - Split and processed hansard parts
- `data/` - Tracking data (processed_hansards.json)
- `logs/` - Log files

## Monitoring

Check logs for daily runs:
```bash
# View today's log
cat logs/daily_scraper_$(date +%Y-%m-%d).log

# View scraper log
tail -f logs/hansard_scraper.log
```

## Troubleshooting

1. **"No module named 'requests'"**
   - Install dependencies: `pip install requests beautifulsoup4 pdfminer.six`

2. **"403 Forbidden" errors**
   - The scraper now uses curl which should bypass this
   - If it persists, the website may have changed its protection

3. **Timeout errors**
   - The scraper includes delays to be respectful
   - Timeouts are normal for large batches
   - The daily checker will resume where it left off

4. **No new hansards found**
   - This is normal if running frequently
   - Check the website manually to verify

## Manual Testing

Test PDF extraction:
```bash
python3 -c "
import requests
from bs4 import BeautifulSoup
url = 'https://parliament.gov.ck/hansard-library/'
r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
soup = BeautifulSoup(r.text, 'html.parser')
pdfs = [a['href'] for a in soup.find_all('a', href=True) if a['href'].endswith('.pdf')]
print(f'Total PDFs: {len(pdfs)}')
print(f'Hansard PDFs: {len([p for p in pdfs if \"DAY-\" in p or any(d in p for d in [\"Mon\",\"Tue\",\"Wed\",\"Thu\",\"Fri\"])])}')"
```