# Fiji Parliament Hansard Scraper and Processor

This system automatically scrapes, downloads, and processes hansard documents from the Fiji Parliament website.

## Components

### 1. **fiji-hansard-scraper.py**
- Main scraper that downloads hansards from the Fiji Parliament website
- Uses curl to bypass any anti-bot measures
- Tracks processed files to avoid duplicates
- Downloads both PDF and HTML formats

### 2. **fiji-hansard-converter-integrated.py**
- Converts hansard HTML files to structured format
- Outputs directly to collections directory structure
- Extracts speakers and metadata
- Handles questions (oral and written) separately

### 3. **fiji-daily-checker.py**
- Runs daily to check for new hansards
- Automatically converts PDFs to HTML
- Processes new files through the converter pipeline

### 4. **process_all_fiji_hansards.py**
- Batch processes all existing Fiji hansards
- Converts PDFs to HTML
- Runs the integrated converter on all files

## Setup

1. Install required Python packages:
```bash
pip install requests beautifulsoup4 pdfminer.six
```

2. Create required directories:
```bash
mkdir -p pdf_hansards html_hansards logs data
```

3. Make scripts executable:
```bash
chmod +x fiji-hansard-scraper.py
chmod +x fiji-daily-checker.py
chmod +x fiji_cron_script.sh
```

## Usage

### Manual Scraping
```bash
python fiji-hansard-scraper.py
```

### Process All Existing Hansards
```bash
python process_all_fiji_hansards.py
```

### Process Single File
```bash
python fiji-hansard-converter-integrated.py path/to/hansard.html
```

### Set Up Daily Automation
Add to crontab:
```bash
# Run daily at 2 AM
0 2 * * * /Users/jacksonkeet/Pacific\ Hansard\ Development/scripts/Fiji/fiji_cron_script.sh
```

## File Structure

```
scripts/Fiji/
├── fiji-hansard-scraper.py          # Main scraper
├── fiji-hansard-converter.py        # Original converter
├── fiji-hansard-converter-integrated.py  # Integrated converter
├── fiji-daily-checker.py            # Daily automation script
├── process_all_fiji_hansards.py     # Batch processor
├── fiji_cron_script.sh              # Cron job script
├── pdf_hansards/                    # Downloaded PDFs
├── html_hansards/                   # Converted HTML files
├── logs/                            # Log files
└── data/                            # Tracking data
    └── fiji_processed_hansards.json # Processed files tracker
```

## Output Structure

Processed hansards are saved to:
```
collections/Fiji/
└── YYYY/
    └── Month/
        └── DD/
            ├── contents.html
            ├── part0.html
            ├── part0_metadata.txt
            ├── part1.html
            ├── part1_metadata.txt
            ├── oral_question_1.html
            ├── oral_question_1_metadata.txt
            └── ...
```

## Speaker Extraction

The system extracts speakers using patterns like:
- HON. [NAME]
- MR/MRS/MS/DR [NAME]
- DEPUTY SPEAKER
- MR/MADAM SPEAKER
- SECRETARY-GENERAL

## Question Detection

Automatically detects and separates:
- Oral Questions
- Written Questions
- Question numbers and titles

## Logging

Logs are saved to the `logs/` directory:
- `fiji_hansard_scraper.log` - Main scraper logs
- `fiji_daily_checker_YYYY-MM-DD.log` - Daily check logs
- `fiji_processing_YYYYMMDD_HHMMSS.log` - Processing logs

## Troubleshooting

1. **No files downloading**: Check if the Fiji Parliament website structure has changed
2. **PDF conversion errors**: Ensure pdfminer.six is installed correctly
3. **Speaker extraction issues**: Review the patterns in extract_and_clean_speakers()
4. **Date parsing errors**: Check filename patterns in extract_date_from_filename()

## Notes

- The Fiji Parliament website URL is: https://www.parliament.gov.fj/parliament-debates/
- Hansards are typically in PDF format
- Naming convention: Daily-Hansard-{Day}-{Date}-{Month}-{Year}.pdf
- The system handles various naming variations