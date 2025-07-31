#!/bin/bash
# Cleanup script for Pacific Hansard Development

echo "Starting cleanup..."

# Remove backup/old files
echo "Removing backup and old files..."
rm -f site/article_backup.php
rm -f site/get_article.php
rm -f site/index_sidebar.html
rm -f site/index-basic.html

# Remove test/debug files
echo "Removing test and debug files..."
rm -f site/test-db-connection.php
rm -f site/test-search.html
rm -f site/test-solr.php
rm -f site/test-speaker-api.html
rm -f site/debug-speaker-search.html
rm -f site/debug-speakers.html
rm -f site/debug.php
rm -f site/check-indexing.php

# Remove duplicate files
echo "Removing duplicate files..."
rm -f reindex-solr.php
rm -f reindex_solr.py
rm -f Dockerfile.php
rm -f site/js/jquery-3.4.1.slim.js
rm -f site/js/jquery-3.4.1.slim.min.js

# Remove log files
echo "Removing log files..."
rm -f scripts/Cook\ Islands/logs/*.log

# Remove unused files
echo "Removing unused files..."
rm -f railway.json
rm -f run_reindex.sh
rm -f cleanup_log.txt

echo "Cleanup complete!"
echo ""
echo "Files removed:"
echo "- 4 backup/old files"
echo "- 8 test/debug files"
echo "- 5 duplicate files"
echo "- All Cook Islands log files"
echo "- 3 unused files"