"""
Centralized error handling module for Pacific Hansard data pipelines.
Provides robust error logging, recovery mechanisms, and pipeline monitoring.
"""

import logging
import json
import os
import sys
import traceback
from datetime import datetime
from functools import wraps
import pysolr
import pymysql
from pymysql import OperationalError, IntegrityError, DataError

# Configure logging
LOG_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'logs')
os.makedirs(LOG_DIR, exist_ok=True)

# Create formatters
detailed_formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
)
simple_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

# File handler for errors
error_handler = logging.FileHandler(os.path.join(LOG_DIR, 'pipeline_errors.log'))
error_handler.setLevel(logging.ERROR)
error_handler.setFormatter(detailed_formatter)

# File handler for all logs
general_handler = logging.FileHandler(os.path.join(LOG_DIR, 'pipeline_general.log'))
general_handler.setLevel(logging.INFO)
general_handler.setFormatter(simple_formatter)

# Console handler
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(simple_formatter)

# Get logger
logger = logging.getLogger('hansard_pipeline')
logger.setLevel(logging.DEBUG)
logger.addHandler(error_handler)
logger.addHandler(general_handler)
logger.addHandler(console_handler)


class PipelineError(Exception):
    """Base exception for pipeline errors"""
    pass


class DataValidationError(PipelineError):
    """Raised when data validation fails"""
    pass


class DatabaseConnectionError(PipelineError):
    """Raised when database connection fails"""
    pass


class SolrConnectionError(PipelineError):
    """Raised when Solr connection fails"""
    pass


class FileProcessingError(PipelineError):
    """Raised when file processing fails"""
    pass


def log_error_context(error, context=None):
    """Log detailed error information with context"""
    error_info = {
        'timestamp': datetime.now().isoformat(),
        'error_type': type(error).__name__,
        'error_message': str(error),
        'traceback': traceback.format_exc(),
        'context': context or {}
    }
    
    # Log to error file as JSON
    error_log_path = os.path.join(LOG_DIR, f'error_{datetime.now():%Y%m%d_%H%M%S}.json')
    with open(error_log_path, 'w') as f:
        json.dump(error_info, f, indent=2)
    
    logger.error(f"Error logged to {error_log_path}: {error}")
    return error_log_path


def retry_on_failure(max_retries=3, delay=1, backoff=2, exceptions=(Exception,)):
    """Decorator to retry function on failure with exponential backoff"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            retry_delay = delay
            last_exception = None
            
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        logger.warning(
                            f"Attempt {attempt + 1} failed for {func.__name__}: {e}. "
                            f"Retrying in {retry_delay} seconds..."
                        )
                        import time
                        time.sleep(retry_delay)
                        retry_delay *= backoff
                    else:
                        logger.error(f"All {max_retries} attempts failed for {func.__name__}")
            
            raise last_exception
        return wrapper
    return decorator


def validate_document_data(document):
    """Validate document data before processing"""
    required_fields = ['title', 'date', 'source', 'content']
    errors = []
    
    for field in required_fields:
        if field not in document or not document[field]:
            errors.append(f"Missing required field: {field}")
    
    # Validate date format
    if 'date' in document and document['date']:
        try:
            datetime.strptime(str(document['date']), '%Y-%m-%d')
        except ValueError:
            errors.append(f"Invalid date format: {document['date']}. Expected YYYY-MM-DD")
    
    # Validate source
    valid_sources = ['Cook Islands', 'Fiji', 'Papua New Guinea', 'Solomon Islands']
    if 'source' in document and document['source'] not in valid_sources:
        errors.append(f"Invalid source: {document['source']}. Must be one of {valid_sources}")
    
    # Validate content length
    if 'content' in document and len(document.get('content', '')) < 10:
        errors.append("Content too short (minimum 10 characters)")
    
    if errors:
        raise DataValidationError(f"Document validation failed: {'; '.join(errors)}")
    
    return True


@retry_on_failure(max_retries=3, exceptions=(OperationalError,))
def get_mysql_connection():
    """Get MySQL connection with retry logic"""
    try:
        connection = pymysql.connect(
            host=os.getenv('DB_HOST', 'mysql'),
            user=os.getenv('DB_USER', 'root'),
            password=os.getenv('DB_PASSWORD', 'Wh1t3sh33ts'),
            database=os.getenv('DB_NAME', 'pacific_hansard_db'),
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
        logger.info("Successfully connected to MySQL")
        return connection
    except OperationalError as e:
        logger.error(f"Failed to connect to MySQL: {e}")
        raise DatabaseConnectionError(f"MySQL connection failed: {e}")


@retry_on_failure(max_retries=3, exceptions=(Exception,))
def get_solr_connection():
    """Get Solr connection with retry logic"""
    try:
        solr_url = os.getenv('SOLR_URL', 'http://solr:8983/solr/hansard_core')
        solr = pysolr.Solr(solr_url, always_commit=True, timeout=30)
        # Test connection
        solr.search('*:*', rows=1)
        logger.info("Successfully connected to Solr")
        return solr
    except Exception as e:
        logger.error(f"Failed to connect to Solr: {e}")
        raise SolrConnectionError(f"Solr connection failed: {e}")


def safe_file_processing(func):
    """Decorator for safe file processing with error recovery"""
    @wraps(func)
    def wrapper(file_path, *args, **kwargs):
        checkpoint_file = f"{file_path}.checkpoint"
        error_file = f"{file_path}.error"
        
        try:
            # Check if we have a previous error
            if os.path.exists(error_file):
                logger.warning(f"Previous error found for {file_path}, attempting recovery")
                with open(error_file, 'r') as f:
                    error_info = json.load(f)
                logger.info(f"Previous error: {error_info['error']}")
            
            # Process file
            result = func(file_path, *args, **kwargs)
            
            # Clean up on success
            if os.path.exists(checkpoint_file):
                os.remove(checkpoint_file)
            if os.path.exists(error_file):
                os.remove(error_file)
                
            return result
            
        except Exception as e:
            # Save error state
            error_info = {
                'file': file_path,
                'error': str(e),
                'timestamp': datetime.now().isoformat(),
                'traceback': traceback.format_exc()
            }
            
            with open(error_file, 'w') as f:
                json.dump(error_info, f, indent=2)
            
            log_error_context(e, {'file_path': file_path})
            raise FileProcessingError(f"Failed to process {file_path}: {e}")
    
    return wrapper


def create_pipeline_monitor():
    """Create a pipeline monitoring context manager"""
    class PipelineMonitor:
        def __init__(self, pipeline_name):
            self.pipeline_name = pipeline_name
            self.start_time = None
            self.stats = {
                'processed': 0,
                'failed': 0,
                'skipped': 0,
                'errors': []
            }
        
        def __enter__(self):
            self.start_time = datetime.now()
            logger.info(f"Starting pipeline: {self.pipeline_name}")
            return self
        
        def __exit__(self, exc_type, exc_val, exc_tb):
            duration = (datetime.now() - self.start_time).total_seconds()
            
            # Save stats
            stats_file = os.path.join(LOG_DIR, f'pipeline_stats_{self.pipeline_name}_{datetime.now():%Y%m%d_%H%M%S}.json')
            self.stats['duration_seconds'] = duration
            self.stats['completed_at'] = datetime.now().isoformat()
            
            with open(stats_file, 'w') as f:
                json.dump(self.stats, f, indent=2)
            
            logger.info(
                f"Pipeline {self.pipeline_name} completed in {duration:.2f}s. "
                f"Processed: {self.stats['processed']}, Failed: {self.stats['failed']}, "
                f"Skipped: {self.stats['skipped']}"
            )
            
            if exc_type:
                logger.error(f"Pipeline {self.pipeline_name} failed with error: {exc_val}")
                log_error_context(exc_val, {'pipeline': self.pipeline_name})
            
            return False  # Don't suppress exceptions
        
        def record_success(self):
            self.stats['processed'] += 1
        
        def record_failure(self, error):
            self.stats['failed'] += 1
            self.stats['errors'].append({
                'error': str(error),
                'timestamp': datetime.now().isoformat()
            })
        
        def record_skip(self, reason):
            self.stats['skipped'] += 1
            logger.debug(f"Skipped: {reason}")
    
    return PipelineMonitor


def safe_database_operation(operation_func):
    """Wrapper for safe database operations with rollback"""
    @wraps(operation_func)
    def wrapper(connection, *args, **kwargs):
        cursor = None
        try:
            cursor = connection.cursor()
            result = operation_func(cursor, *args, **kwargs)
            connection.commit()
            return result
        except (IntegrityError, DataError) as e:
            connection.rollback()
            logger.error(f"Database operation failed: {e}")
            raise
        except Exception as e:
            connection.rollback()
            logger.error(f"Unexpected database error: {e}")
            raise
        finally:
            if cursor:
                cursor.close()
    
    return wrapper


# Example usage functions
def example_safe_document_insert(cursor, document):
    """Example of safe document insertion"""
    sql = """
    INSERT INTO pacific_hansard_db 
    (title, date, source, speaker, speaker2, document_type, content, new_id)
    VALUES (%(title)s, %(date)s, %(source)s, %(speaker)s, %(speaker2)s, 
            %(document_type)s, %(content)s, %(new_id)s)
    """
    cursor.execute(sql, document)
    return cursor.lastrowid


def example_pipeline_usage():
    """Example of how to use the error handling in a pipeline"""
    pipeline_monitor = create_pipeline_monitor()
    
    with pipeline_monitor('example_pipeline') as monitor:
        # Get connections
        try:
            mysql_conn = get_mysql_connection()
            solr_conn = get_solr_connection()
        except (DatabaseConnectionError, SolrConnectionError) as e:
            logger.error(f"Failed to establish connections: {e}")
            return
        
        # Process documents
        documents = []  # Your documents here
        
        for doc in documents:
            try:
                # Validate document
                validate_document_data(doc)
                
                # Insert to MySQL
                safe_insert = safe_database_operation(example_safe_document_insert)
                doc_id = safe_insert(mysql_conn, doc)
                
                # Index to Solr
                solr_conn.add([doc])
                
                monitor.record_success()
                logger.info(f"Successfully processed document: {doc.get('title', 'Unknown')}")
                
            except DataValidationError as e:
                monitor.record_failure(e)
                logger.warning(f"Skipping invalid document: {e}")
                continue
                
            except Exception as e:
                monitor.record_failure(e)
                logger.error(f"Failed to process document: {e}")
                continue
        
        mysql_conn.close()


if __name__ == "__main__":
    # Test the error handling
    logger.info("Testing error handling module")
    example_pipeline_usage()