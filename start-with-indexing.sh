#!/bin/bash

# Start Apache in the background
apache2ctl start

# Run smart indexing in the background
echo "Starting background indexing..."
python3 /app/pipelines_smart.py > /var/log/indexing.log 2>&1 &

# Keep Apache in the foreground
apache2-foreground