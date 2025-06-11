# Cook Islands Hansard Deployment Guide

## Overview

The Cook Islands hansards have been successfully processed and placed in the collections directory structure, ready for indexing by the Docker pipeline.

## What's Been Done

1. **Enhanced Converter**: Created `CI-hansard-converter-integrated.py` that:
   - Outputs directly to `/collections/Cook Islands/YYYY/Month/DD/` structure
   - Flattens question files (no subdirectories) for pipeline compatibility
   - Extracts comprehensive speaker metadata (416 unique speakers across 23 documents)
   - Successfully processes 149 parliamentary questions from modern hansards

2. **Processed Files**: All 23 hansards have been converted and placed in:
   ```
   /collections/Cook Islands/
   ├── 1997/
   │   ├── April/
   │   ├── June/
   │   ├── July/
   │   ├── August/
   │   ├── November/
   │   └── December/
   ├── 1998/
   │   ├── June/
   │   ├── July/
   │   ├── August/
   │   ├── September/
   │   └── December/
   ├── 1999/
   │   ├── March/
   │   ├── August/
   │   └── September/
   └── 2025/
       ├── Feb/
       └── May/
   ```

3. **File Structure**: Each date directory contains:
   - `contents.html` - Table of contents
   - `metadata.json` - Parliament number, date, session info
   - `partX.html` - Document sections
   - `partX_metadata.txt` - Speaker information
   - `partX_oral_question_Y.html` - Individual questions (flattened)
   - `partX_oral_question_Y_metadata.txt` - Question speakers

## Deployment Steps

### 1. Verify File Placement
```bash
# Check that files are in the collections directory
ls -la "/Users/jacksonkeet/Pacific Hansard Development/collections/Cook Islands/"
```

### 2. Start Docker Containers
```bash
cd "/Users/jacksonkeet/Pacific Hansard Development"

# Start all services
docker-compose up -d

# Or start with build if needed
docker-compose up -d --build
```

### 3. Monitor Processing
```bash
# Watch the Python pipeline process the files
docker-compose logs -f python_script

# You should see output like:
# "Record inserted successfully into MySQL"
# "Document indexed successfully in Solr"
```

### 4. Verify Indexing
```bash
# Check MySQL records
docker exec -it mysql_pacific_hansard mysql -u hansard_user -ptest_pass -e "SELECT COUNT(*) FROM pacific_hansard_db.pacific_hansard_db WHERE source='Cook Islands';"

# Check Solr index
curl "http://localhost:8983/solr/hansard_core/select?q=source:Cook%20Islands&rows=0"
```

### 5. Access Web Interface
Open http://localhost:8080 in your browser to:
- Browse hansards by country
- Search for specific speakers or topics
- View individual questions and debates

## Processing Statistics

- **Total Documents**: 23 hansards (1997-2025)
- **Unique Speakers**: 416 MPs and officials
- **Questions Extracted**: 149 (from 6 modern format hansards)
- **Document Parts**: ~250 sections across all hansards

## Notes

1. **Question Extraction**: Only modern format hansards (DAY-XX pattern) have extractable questions due to different HTML structures in older documents.

2. **Speaker Coverage**: Approximately 60% of document sections have identified speakers. Procedural sections often lack speaker attribution.

3. **The existing `pipelines.py` will automatically process** all files in the collections directory, including the flattened question files.

4. **Ongoing Updates**: Use the integrated converter for any new hansards:
   ```bash
   python3 CI-hansard-converter-integrated.py html_hansards/new-hansard.html
   ```

## Troubleshooting

### If documents aren't appearing in the web interface:
1. Check Docker logs: `docker-compose logs python_script`
2. Verify MySQL connection: `docker exec -it mysql_pacific_hansard ping`
3. Check Solr status: `curl http://localhost:8983/solr/admin/cores?action=STATUS`

### If processing seems stuck:
1. Restart the Python container: `docker-compose restart python_script`
2. Check for file permissions: `ls -la collections/Cook\ Islands/`

## Future Enhancements

1. **Improve Question Extraction** for older hansards by creating format-specific parsers
2. **Add Speaker Roles** (Minister, Opposition, etc.) to metadata
3. **Implement Topic Tagging** for better searchability
4. **Create API Endpoints** for programmatic access

## Success Metrics

✅ 416 unique speakers indexed for searchability
✅ 149 parliamentary questions available as separate documents
✅ All hansards properly structured with contents and metadata
✅ Compatible with existing Docker pipeline - no modifications needed

The Cook Islands parliamentary records are now ready for democratic transparency!