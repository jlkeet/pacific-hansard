#!/bin/bash

# Deploy Fiji with enhanced formatting

echo "Starting Fiji enhanced deployment..."

# Change to project directory
cd "/Users/jacksonkeet/Pacific Hansard Development"

# Rebuild the Docker image
echo "Building Docker image with enhanced pipeline..."
docker compose build python_script

# Clear existing Fiji data from MySQL
echo "Clearing existing Fiji data from MySQL..."
mysql -h 127.0.0.1 -P 3307 -u hansard_user -ptest_pass pacific_hansard_db -e "DELETE FROM pacific_hansard_db WHERE source='Fiji';"

# Clear existing Fiji data from Solr
echo "Clearing existing Fiji data from Solr..."
curl -X POST "http://localhost:8983/solr/hansard_core/update?commit=true" -H "Content-Type: text/xml" -d "<delete><query>source:Fiji</query></delete>"

# Run the enhanced pipeline
echo "Running enhanced pipeline to index Fiji with HTML content..."
docker compose run --rm python_script

# Check results
echo "Checking results..."
echo "MySQL count:"
mysql -h 127.0.0.1 -P 3307 -u hansard_user -ptest_pass pacific_hansard_db -e "SELECT source, COUNT(*) as count FROM pacific_hansard_db GROUP BY source;"

echo "Solr count:"
curl -s "http://localhost:8983/solr/hansard_core/select?q=source:Fiji&rows=0" | grep -o '"numFound":[0-9]*'

echo "Deployment complete!"