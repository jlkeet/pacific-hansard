#!/usr/bin/env python3
"""
Load all documents from collections directory with proper batch processing.
"""

import os
import sys
import json
import logging
from pathlib import Path
import pymysql
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

def load_all_documents():
    """Load all documents from collections directory."""
    
    # Database configuration
    db_config = {
        'host': 'localhost',
        'port': 3307,
        'database': 'pacific_hansard_db',
        'user': 'hansard_user',
        'password': 'test_pass',
        'charset': 'utf8mb4'
    }
    
    # Solr configuration
    solr_url = 'http://localhost:8983/solr/hansard_core'
    solr = pysolr.Solr(solr_url)
    
    # Clear existing data
    logger.info("Clearing existing data...")
    try:
        solr.delete(q='*:*')
        solr.commit()
        
        conn = pymysql.connect(**db_config)
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM documents")
        conn.commit()
        conn.close()
        logger.info("Cleared existing data")
    except Exception as e:
        logger.error(f"Error clearing data: {e}")
        return
    
    # Find all documents
    collections_path = Path(__file__).parent.parent / "collections"
    all_files = []
    
    logger.info("Scanning collections directory...")
    for country_path in collections_path.iterdir():
        if country_path.is_dir():
            country_files = list(country_path.rglob("*.html"))
            # Filter out contents.html files
            country_files = [f for f in country_files if f.name != 'contents.html']
            all_files.extend(country_files)
            logger.info(f"Found {len(country_files)} documents in {country_path.name}")
    
    logger.info(f"Total documents to process: {len(all_files)}")
    
    if len(all_files) == 0:
        logger.error("No documents found!")
        return
    
    # Process in batches
    processed = 0
    skipped = 0
    total_chunks = 0
    batch_size = 25
    
    for i in range(0, len(all_files), batch_size):
        batch = all_files[i:i + batch_size]
        batch_num = i // batch_size + 1
        total_batches = (len(all_files) - 1) // batch_size + 1
        
        logger.info(f"Processing batch {batch_num}/{total_batches} ({len(batch)} files)")
        
        batch_processed = 0
        batch_chunks = 0
        
        for html_file in batch:
            try:
                # Read HTML content
                with open(html_file, 'r', encoding='utf-8', errors='ignore') as f:
                    html_content = f.read()
                
                # Extract content
                content = extract_text_from_html(html_content)
                if not content or len(content.strip()) < 100:
                    logger.debug(f"Skipping file with insufficient content: {html_file.name}")
                    skipped += 1
                    continue
                
                # Extract document information
                soup = BeautifulSoup(html_content, 'html.parser')
                title_tag = soup.find('title')
                title = title_tag.text.strip() if title_tag else html_file.stem.replace('_', ' ').title()
                
                date = parse_date_from_path(html_file)
                
                # Determine source country
                if 'Cook Islands' in str(html_file):
                    source = 'Cook Islands'
                elif 'Fiji' in str(html_file):
                    source = 'Fiji'
                elif 'Papua New Guinea' in str(html_file) or 'PNG' in str(html_file):
                    source = 'Papua New Guinea'
                else:
                    source = 'Unknown'
                
                # Determine document type
                if 'oral_question' in html_file.name:
                    doc_type = 'oral_question'
                elif 'written_question' in html_file.name:
                    doc_type = 'written_question'
                else:
                    doc_type = 'hansard'
                
                # Save to database
                conn = pymysql.connect(**db_config)
                with conn.cursor() as cursor:
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
                    batch_chunks += len(solr_docs)
                    logger.debug(f"Indexed {len(solr_docs)} chunks for {html_file.name}")
                
                batch_processed += 1
                
            except Exception as e:
                logger.error(f"Error processing {html_file.name}: {e}")
                skipped += 1
                continue
        
        # Commit batch to Solr
        try:
            solr.commit()
        except Exception as e:
            logger.error(f"Error committing batch {batch_num}: {e}")
        
        # Update totals
        processed += batch_processed
        total_chunks += batch_chunks
        
        logger.info(f"Batch {batch_num} complete: {batch_processed}/{len(batch)} processed, {batch_chunks} chunks created")
        logger.info(f"Overall progress: {processed}/{len(all_files)} documents, {skipped} skipped, {total_chunks} total chunks")
    
    # Final commit
    try:
        solr.commit()
        logger.info("Final commit to Solr completed")
    except Exception as e:
        logger.error(f"Error with final commit: {e}")
    
    # Generate embeddings for all new documents
    logger.info("Generating embeddings for all documents...")
    try:
        from rag.generate_embeddings import generate_and_update_embeddings
        generate_and_update_embeddings()
    except Exception as e:
        logger.error(f"Error generating embeddings: {e}")
        logger.info("You can run embeddings separately with: python rag/generate_embeddings.py")
    
    logger.info(f"[SUCCESS] Data loading complete!")
    logger.info(f"Total documents processed: {processed}")
    logger.info(f"Total documents skipped: {skipped}")
    logger.info(f"Total chunks created: {total_chunks}")

def main():
    """Main entry point."""
    print("Loading all documents from collections directory...")
    load_all_documents()
    print("Done!")

if __name__ == "__main__":
    main()