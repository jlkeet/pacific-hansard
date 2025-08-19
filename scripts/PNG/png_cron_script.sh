#!/bin/bash

# PNG Hansard Scraper Cron Script
# This script should be run daily via cron to check for new PNG hansards

# Set the working directory to the PNG scripts directory
cd "$(dirname "$0")"

# Set up Python path
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Log file for cron execution
LOG_FILE="logs/png_cron_$(date +%Y%m%d).log"

# Create logs directory if it doesn't exist
mkdir -p logs

echo "$(date): Starting PNG hansard daily check" >> "$LOG_FILE"

# Activate virtual environment if needed (uncomment and adjust path as needed)
# source /path/to/venv/bin/activate

# Run the PNG scraper in daily mode
python3 PNG-hansard-scraper.py --daily >> "$LOG_FILE" 2>&1

# Check exit status
if [ $? -eq 0 ]; then
    echo "$(date): PNG hansard scraper completed successfully" >> "$LOG_FILE"
else
    echo "$(date): PNG hansard scraper failed with exit code $?" >> "$LOG_FILE"
fi

# Optional: Clean up old log files (keep last 30 days)
find logs/ -name "png_cron_*.log" -mtime +30 -delete 2>/dev/null

echo "$(date): PNG cron script finished" >> "$LOG_FILE"