# Enhanced Error Handling for Pacific Hansard Data Pipelines

This document describes the enhanced error handling system implemented for the Pacific Hansard data processing pipelines.

## Overview

The error handling system provides:
- Robust error recovery mechanisms
- Detailed logging and monitoring
- Retry logic for transient failures
- Data validation
- Pipeline performance tracking
- Error analysis and reporting

## Components

### 1. Error Handler Module (`common/error_handler.py`)

Core error handling functionality:
- Custom exception classes for different error types
- Retry decorators with exponential backoff
- Database and Solr connection management
- File processing safety wrappers
- Pipeline monitoring context managers
- Data validation functions

### 2. Enhanced Converter Scripts

Example: `Cook Islands/CI-hansard-converter-enhanced.py`
- Implements comprehensive error handling
- Validates data at each processing step
- Provides detailed progress logging
- Recovers from partial failures
- Generates processing reports

### 3. Pipeline Monitor (`common/monitor_pipelines.py`)

Dashboard for monitoring pipeline health:
- Analyzes error logs
- Tracks pipeline performance metrics
- Generates recommendations
- Exports reports in multiple formats

## Usage

### Running Enhanced Converters

```bash
# Process single file
python scripts/Cook\ Islands/CI-hansard-converter-enhanced.py file.html

# Process directory with error continuation
python scripts/Cook\ Islands/CI-hansard-converter-enhanced.py --directory html_hansards --continue-on-error

# Monitor pipeline status
python scripts/common/monitor_pipelines.py --days 7
```

### Error Handling Features

1. **Automatic Retries**
   - Database connections retry up to 3 times
   - File operations retry with exponential backoff
   - Configurable retry policies

2. **Data Validation**
   - Required fields checking
   - Date format validation
   - Source validation against allowed values
   - Content length validation

3. **Error Recovery**
   - Checkpoint files for resuming failed operations
   - Error state persistence
   - Graceful degradation

4. **Logging Levels**
   - INFO: General progress updates
   - WARNING: Recoverable issues
   - ERROR: Failures requiring attention
   - DEBUG: Detailed diagnostic information

### Log Files

Logs are stored in `scripts/logs/`:
- `pipeline_general.log`: All pipeline activity
- `pipeline_errors.log`: Errors only with stack traces
- `error_YYYYMMDD_HHMMSS.json`: Detailed error context
- `pipeline_stats_*.json`: Performance metrics

### Monitoring Reports

Generate monitoring reports:
```bash
# Last 7 days report
python scripts/common/monitor_pipelines.py

# Last 30 days with JSON export
python scripts/common/monitor_pipelines.py --days 30 --export-json report.json
```

## Error Types

### PipelineError
Base exception for all pipeline errors

### DataValidationError
- Missing required fields
- Invalid date formats
- Invalid source values
- Content validation failures

### DatabaseConnectionError
- MySQL connection failures
- Authentication errors
- Network timeouts

### SolrConnectionError
- Solr service unavailable
- Index corruption
- Query failures

### FileProcessingError
- File not found
- Permission errors
- Corrupt file content
- I/O failures

## Best Practices

1. **Always validate data before processing**
   ```python
   validate_document_data(document)
   ```

2. **Use pipeline monitors for batch operations**
   ```python
   with create_pipeline_monitor()('my_pipeline') as monitor:
       # Process documents
       monitor.record_success()
   ```

3. **Implement retry logic for network operations**
   ```python
   @retry_on_failure(max_retries=3, exceptions=(OperationalError,))
   def database_operation():
       # Your code here
   ```

4. **Log context with errors**
   ```python
   log_error_context(error, {'document_id': doc_id, 'source': source})
   ```

## Troubleshooting

### Common Issues

1. **High failure rates**
   - Check database connectivity
   - Verify Solr is running
   - Review data quality

2. **Memory issues**
   - Process files in smaller batches
   - Enable checkpoint recovery
   - Monitor system resources

3. **Slow processing**
   - Check for retry storms
   - Review network latency
   - Optimize database queries

### Getting Help

1. Check logs in `scripts/logs/`
2. Run pipeline monitor for analysis
3. Review error JSON files for context
4. Check processing reports in output directories

## Future Enhancements

- Real-time monitoring dashboard
- Automated error recovery strategies
- Machine learning for error prediction
- Integration with alerting systems
- Performance optimization recommendations