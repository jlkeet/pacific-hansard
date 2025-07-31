#!/bin/bash

echo "Re-indexing Solr with speaker data..."

# Run the reindex script in the python container
docker-compose exec python_script python /app/reindex_solr.py

echo "Re-indexing complete!"

# Test the results
echo ""
echo "Testing speaker facets..."
curl -s "http://localhost:8983/solr/hansard_core/select?q=*:*&rows=0&facet=true&facet.field=speaker&facet.mincount=1&wt=json" | python -m json.tool | grep -A 10 '"speaker"'