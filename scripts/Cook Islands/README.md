# Cook Islands Hansard Scraper

This tool automatically downloads Hansard PDFs from the Cook Islands Parliament website, 
converts them to HTML, processes them into structured parts, and indexes them in Solr and MySQL.

## Features

- Scrapes the Cook Islands Parliament website for new Hansard PDFs
- Avoids re-downloading and re-processing previously handled documents
- Converts PDFs to HTML using pdfminer.six
- Processes HTML into structured parts with speaker information
- Can be scheduled to run daily using cron
- Available as a Docker container for reliable execution

## Setup and Usage

### Method 1: Direct Execution

1. Install required packages:
   ```bash
   pip install -r ../../requirements.txt
   pip install requests beautifulsoup4 pdfminer.six
   ```

2. Make the runner script executable:
   ```bash
   chmod +x run_daily_scraper.sh
   ```

3. Run the scraper manually:
   ```bash
   ./run_daily_scraper.sh
   ```

4. Set up a cron job to run daily (optional):
   ```bash
   crontab -e
   # Add the line from crontab_entry.txt
   ```

### Method 2: Docker Container

1. Build and start the Docker container:
   ```bash
   docker-compose -f docker-compose.scraper.yml up -d
   ```

2. The container will run the scraper daily at 1:00 AM.

3. To run the scraper manually in the container:
   ```bash
   docker exec hansard_scraper python /app/CI-hansard-scraper.py
   ```

4. Check logs:
   ```bash
   docker exec hansard_scraper cat /app/logs/scraper_$(date +%Y-%m-%d).log
   ```

## Directory Structure

- `pdf_hansards/`: Downloaded PDF files
- `html_hansards/`: PDF files converted to HTML
- `processed_hansards/`: Split HTML files organized by structure
- `data/`: Metadata and tracking information
- `logs/`: Execution logs

## Files

- `CI-hansard-scraper.py`: Main scraper script
- `CI_gpt_hansard.py`: PDF to HTML converter
- `CI_hansard_converter.py`: HTML processor for splitting into parts
- `run_daily_scraper.sh`: Shell script for running the scraper
- `crontab_entry.txt`: Example crontab entry for scheduling
- `Dockerfile.scraper`: Docker configuration for the scraper
- `docker-compose.scraper.yml`: Docker Compose configuration
- `cron_script.sh`: Script run by cron in the Docker container

## Customization

If the structure of the Cook Islands Parliament website changes, you may need to update the 
`get_hansard_pdfs()` function in `CI-hansard-scraper.py` to match the new HTML structure.

## Integration with Indexing Pipeline

To fully integrate with the Solr and MySQL indexing pipeline, uncomment and modify the 
`run_indexing_pipeline()` function in `CI-hansard-scraper.py` to call your existing indexing code.