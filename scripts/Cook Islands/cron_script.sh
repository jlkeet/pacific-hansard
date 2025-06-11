#!/bin/bash
# Cron script to run the scraper in Docker

# Set up logging
LOG_FILE="/app/logs/scraper_$(date +%Y-%m-%d).log"

echo "$(date): Starting Cook Islands Hansard scraper" >> "${LOG_FILE}"

# Run the scraper
cd /app && python CI-hansard-scraper.py >> "${LOG_FILE}" 2>&1

# Check exit status
if [ $? -eq 0 ]; then
    echo "$(date): Scraper completed successfully" >> "${LOG_FILE}"
else
    echo "$(date): Scraper encountered errors" >> "${LOG_FILE}"
fi

echo "$(date): Scraper run completed" >> "${LOG_FILE}"