#!/usr/bin/env python3
"""
Sample data loader for testing the RAG system.
Loads a small subset of documents first to verify the pipeline works.
"""

import os
import sys
import json
import logging
from pathlib import Path
from typing import List, Dict, Any
import mysql.connector
import pysolr
from datetime import datetime
from bs4 import BeautifulSoup
import re

# Add project root to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from rag.chunker import chunk_document

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def extract_text_from_html(html_content: str) -> str:
    """Extract clean text from HTML content."""
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Remove script and style elements
    for script in soup(["script", "style"]):
        script.decompose()
    
    # Get text and clean it up
    text = soup.get_text()
    
    # Clean up whitespace
    lines = (line.strip() for line in text.splitlines())
    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
    text = ' '.join(chunk for chunk in chunks if chunk)
    
    return text

def parse_date_from_path(file_path: Path) -> str:
    """Extract date from file path structure."""
    parts = file_path.parts
    
    # Look for year/month/day pattern
    try:
        if len(parts) >= 3:
            # Check if we have year/month/day structure
            year_idx = None
            for i, part in enumerate(parts):
                if part.isdigit() and len(part) == 4 and 1990 <= int(part) <= 2030:
                    year_idx = i
                    break
            
            if year_idx and year_idx + 2 < len(parts):
                year = parts[year_idx]
                month = parts[year_idx + 1]
                day = parts[year_idx + 2]
                
                # Convert month name to number if needed
                month_map = {
                    'January': '01', 'February': '02', 'March': '03',
                    'April': '04', 'May': '05', 'June': '06',
                    'July': '07', 'August': '08', 'September': '09',
                    'October': '10', 'November': '11', 'December': '12'
                }
                
                month_num = month_map.get(month, month)
                if month_num.isdigit() and len(month_num) <= 2:
                    month_num = month_num.zfill(2)
                
                day_num = day.zfill(2) if day.isdigit() else day
                
                return f"{year}-{month_num}-{day_num}"
    except:
        pass
    
    return "1900-01-01"  # Default date

def load_sample_documents():
    """Load a few sample documents to test the system."""
    
    # Database configuration
    db_config = {
        'host': 'localhost',
        'port': 3307,
        'database': 'pacific_hansard_db',
        'user': 'hansard_user',
        'password': 'test_pass'
    }
    
    # Solr configuration
    solr_url = 'http://localhost:8983/solr/hansard_core'
    solr = pysolr.Solr(solr_url)
    
    # Clear existing data
    logger.info("Clearing existing data...")
    try:
        solr.delete(q='*:*')
        solr.commit()
        
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM documents")
        conn.commit()
        conn.close()
        logger.info("Cleared existing data")
    except Exception as e:
        logger.error(f"Error clearing data: {e}")
        return
    
    # Find sample documents
    collections_path = Path(__file__).parent.parent / "collections"
    sample_files = []
    
    # Get a few files from each country
    for country_path in collections_path.iterdir():
        if country_path.is_dir():
            count = 0
            for html_file in country_path.rglob("*.html"):
                if html_file.name not in ['contents.html'] and count < 3:
                    sample_files.append(html_file)
                    count += 1
    
    logger.info(f"Processing {len(sample_files)} sample documents...")
    
    processed = 0
    total_chunks = 0
    
    for html_file in sample_files:
        try:
            logger.info(f"Processing: {html_file}")
            
            # Read HTML content
            with open(html_file, 'r', encoding='utf-8', errors='ignore') as f:
                html_content = f.read()
            
            # Extract content
            content = extract_text_from_html(html_content)
            if not content or len(content.strip()) < 50:
                logger.warning(f"Skipping file with insufficient content: {html_file}")
                continue
            
            # Extract document information
            soup = BeautifulSoup(html_content, 'html.parser')
            title_tag = soup.find('title')
            title = title_tag.text.strip() if title_tag else html_file.stem.replace('_', ' ').title()
            
            date = parse_date_from_path(html_file)
            source = 'Cook Islands' if 'Cook Islands' in str(html_file) else \
                    'Fiji' if 'Fiji' in str(html_file) else \
                    'Papua New Guinea' if 'Papua New Guinea' in str(html_file) else 'Unknown'
            
            doc_type = 'oral_question' if 'oral_question' in html_file.name else \
                      'written_question' if 'written_question' in html_file.name else 'hansard'
            
            # Save to database
            conn = mysql.connector.connect(**db_config)
            cursor = conn.cursor()
            
            insert_query = """
                INSERT INTO documents (title, date, speaker, speaker2, document_type, content)
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            
            cursor.execute(insert_query, (
                title[:255],
                date,
                '',  # speakers
                '',  # speaker2
                doc_type,
                content
            ))
            
            doc_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            logger.info(f"Saved document {doc_id}: {title}")
            
            # Create chunks
            chunks = chunk_document(
                content=content,
                title=title,
                date=date,
                speakers='',
                document_type=doc_type,
                source=source,
                doc_id=doc_id
            )
            
            # Index chunks in Solr
            solr_docs = []
            for chunk in chunks:
                solr_doc = {
                    'id': chunk['chunk_id'],
                    'document_id': doc_id,
                    'title': chunk['metadata']['title'],
                    'content': chunk['content'],
                    'source': chunk['metadata']['source'],
                    'date': chunk['metadata']['date'],
                    'speakers': chunk['metadata']['speakers'],
                    'document_type': chunk['metadata']['document_type'],
                    'chunk_index': chunk['chunk_index'],
                    'token_count': chunk['token_count']
                }
                solr_docs.append(solr_doc)
            
            if solr_docs:
                solr.add(solr_docs)
                total_chunks += len(solr_docs)
                logger.info(f"Indexed {len(solr_docs)} chunks for document {doc_id}")
            
            processed += 1
            
        except Exception as e:
            logger.error(f"Error processing {html_file}: {e}")
            continue
    
    # Commit Solr changes
    try:
        solr.commit()
        logger.info("Committed Solr changes")
    except Exception as e:
        logger.error(f"Error committing to Solr: {e}")
    
    # Final statistics
    logger.info(f"🎉 Sample data loading complete!")
    logger.info(f"📊 Documents processed: {processed}")
    logger.info(f"🔍 Chunks indexed: {total_chunks}")

if __name__ == "__main__":
    load_sample_documents()