# Pacific Hansard Enhanced Search Deployment Guide

## Overview
This guide covers the deployment of the enhanced search functionality for the Pacific Hansard system.

## New Files Created

1. **`site/index-enhanced.html`** - Enhanced search interface with:
   - Speaker search with autocomplete
   - Advanced filters (date range, source, document type)
   - Search templates (Recent Questions, Ministerial Statements, etc.)
   - Export functionality (CSV, JSON, Citations)
   - Mobile-responsive design

2. **`site/tkb-search-enhanced.js`** - JavaScript functionality for:
   - Speaker autocomplete
   - Advanced search filters
   - Export functionality
   - Search templates
   - Mobile optimization

3. **`site/api/speakers.php`** - API endpoint for speaker autocomplete:
   - Queries both speaker and speaker2 fields
   - Returns unique speaker names for autocomplete
   - Supports search filtering

4. **Updated `site/article.php`** - Enhanced article display:
   - Prominently displays speaker information
   - Better formatting for parliamentary debates
   - Speaker badges

## Deployment Steps

### 1. Copy New Files
```bash
# Copy the enhanced search files to your web server
cp site/index-enhanced.html site/
cp site/tkb-search-enhanced.js site/
cp site/api/speakers.php site/api/
```

### 2. Update Web Container
Since new files have been added, restart the web container:
```bash
docker-compose restart web php
```

### 3. Test Speaker API
Test the speaker API endpoint:
```bash
curl http://localhost:8080/api/speakers.php?q=HON
```

### 4. Access Enhanced Search
Navigate to: http://localhost:8080/index-enhanced.html

### 5. Update Default Search Page (Optional)
To make the enhanced search the default:
```bash
# Backup original
mv site/index.html site/index-original.html
# Use enhanced as default
cp site/index-enhanced.html site/index.html
```

## Testing Checklist

### Speaker Search
- [ ] Type "HON" in speaker search - should show autocomplete suggestions
- [ ] Select a speaker - should filter results to that speaker
- [ ] Clear speaker search - should show all results

### Search Templates
- [ ] Click "Recent Questions" - should show recent oral questions
- [ ] Click "Ministerial Statements" - should filter for ministerial content
- [ ] Click "Find My MP" - should focus on speaker search

### Export Functionality
- [ ] Search for any term
- [ ] Click "Export CSV" - should download results as CSV
- [ ] Click "Export JSON" - should download results as JSON
- [ ] Click "Export Citations" - should download academic citations

### Mobile Testing
- [ ] Open on mobile device or use browser developer tools
- [ ] Check that filters collapse on mobile
- [ ] Verify touch targets are appropriately sized
- [ ] Test search and export on mobile

### Advanced Filters
- [ ] Test date range filters (Past day, week, month, year)
- [ ] Test source filter (Cook Islands, Fiji, PNG)
- [ ] Test document type filter
- [ ] Test "Questions Only" checkbox
- [ ] Test combination of filters

## Troubleshooting

### Speaker Autocomplete Not Working
1. Check that speaker API is accessible:
   ```bash
   curl http://localhost:8080/api/speakers.php
   ```
2. Verify PHP container has database access
3. Check browser console for JavaScript errors

### Export Not Working
1. Ensure JavaScript file is loaded (check browser console)
2. Verify search results are loaded before trying to export
3. Check browser's download permissions

### Search Not Returning Results
1. Verify Solr is running:
   ```bash
   curl http://localhost:8983/solr/hansard_core/select?q=*:*&rows=1
   ```
2. Check that data has been indexed with speaker fields
3. Verify JavaScript is constructing correct Solr queries (check Network tab)

## Performance Optimization

1. **Speaker API Caching**: Consider adding Redis/Memcached for speaker list caching
2. **Search Result Caching**: Implement client-side caching for repeated searches
3. **Lazy Loading**: Results already implement infinite scroll for performance

## Security Considerations

1. **SQL Injection**: The speaker API uses prepared statements
2. **XSS Protection**: All user input is properly escaped
3. **CORS**: Currently allows all origins - restrict in production

## Future Enhancements

1. **Full-text Search in Speaker Names**: Currently uses LIKE queries
2. **Speaker Photos**: Add MP photos to search results
3. **Related Documents**: Show related debates/questions
4. **Search Analytics**: Track popular searches and speakers

## Monitoring

Monitor these metrics:
- Speaker API response time
- Search query performance
- Export usage statistics
- Mobile vs desktop usage
- Most searched speakers

## Support

For issues or questions about the enhanced search functionality:
1. Check browser console for JavaScript errors
2. Verify all files are properly deployed
3. Ensure Docker containers are running
4. Check that Solr has indexed speaker data