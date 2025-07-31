"""
Database configuration for Railway deployment
"""
import os
from urllib.parse import urlparse

def get_db_config():
    """Get database configuration from MYSQL_URL or individual env vars"""
    mysql_url = os.environ.get('MYSQL_URL')
    
    if mysql_url:
        # Parse the MySQL URL: mysql://user:password@host:port/database
        url = urlparse(mysql_url)
        
        return {
            'host': url.hostname,
            'port': url.port or 3306,
            'database': url.path.lstrip('/'),
            'user': url.username,
            'password': url.password
        }
    else:
        # Fallback to individual env vars
        return {
            'host': os.environ.get('DB_HOST', 'mysql'),
            'port': int(os.environ.get('DB_PORT', 3306)),
            'database': os.environ.get('DB_NAME', 'pacific_hansard_db'),
            'user': os.environ.get('DB_USER', 'hansard_user'),
            'password': os.environ.get('DB_PASSWORD', 'test_pass')
        }

def get_solr_url():
    """Get Solr URL from environment"""
    return os.environ.get('SOLR_URL', 'http://localhost:8983/solr/hansard_core')