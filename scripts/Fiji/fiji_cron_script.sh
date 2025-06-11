#!/bin/bash

# Fiji Hansard Daily Cron Script
# Run daily to check for new hansards

# Set working directory
cd /Users/jacksonkeet/Pacific\ Hansard\ Development/scripts/Fiji

# Activate Python environment if needed
# source /path/to/venv/bin/activate

# Create log directory if it doesn't exist
mkdir -p logs

# Run the daily checker
echo "Starting Fiji hansard daily check at $(date)" >> logs/cron.log
python fiji-daily-checker.py >> logs/cron.log 2>&1

# Check if any new files were downloaded
if [ $? -eq 0 ]; then
    echo "Daily check completed successfully at $(date)" >> logs/cron.log
else
    echo "Daily check failed at $(date)" >> logs/cron.log
fi

# Optional: Send email notification if new hansards found
# You can add email notification here