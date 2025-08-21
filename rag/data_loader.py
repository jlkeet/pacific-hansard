#!/usr/bin/env python3
"""
Data loader for Pacific Hansard RAG system.
Processes HTML documents from collections directory, loads into MySQL, chunks them, and indexes in Solr.
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
import uuid
from bs4 import BeautifulSoup
import re

# Add project root to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from rag.chunker import chunk_document

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class HansardDataLoader:
    def __init__(self):
        self.db_config = {
            'host': 'localhost',
            'port': 3307,
            'database': 'pacific_hansard_db',
            'user': 'hansard_user',
            'password': 'test_pass'
        }
        self.solr_url = 'http://localhost:8983/solr/hansard_core'
        self.solr = pysolr.Solr(self.solr_url)
        
    def get_db_connection(self):
        """Get MySQL database connection."""
        return mysql.connector.connect(**self.db_config)
    
    def extract_text_from_html(self, html_content: str) -> str:
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
    
    def parse_date_from_path(self, file_path: Path) -> str:
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
    
    def extract_title_from_html(self, html_content: str, file_path: Path) -> str:
        """Extract title from HTML content."""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Try title tag first
        title_tag = soup.find('title')
        if title_tag and title_tag.text.strip():
            title = title_tag.text.strip()
            # Clean up common prefixes
            if 'PNG Hansard Part' in title:
                parts = title.split(' - ', 1)
                if len(parts) > 1:
                    title = parts[1].strip()
            return title
        
        # Try h1, h2, h3 tags
        for tag in ['h1', 'h2', 'h3']:
            header = soup.find(tag)
            if header and header.text.strip():
                return header.text.strip()
        
        # Extract from file path
        file_name = file_path.stem
        if file_name.startswith('part'):
            return f"Hansard {file_name.title()}"
        elif 'oral_question' in file_name:
            return f"Oral Question {file_name.split('_')[-1].title()}"
        elif 'written_question' in file_name:
            return f"Written Question {file_name.split('_')[-1].title()}"
        
        return file_name.replace('_', ' ').title()
    
    def extract_speakers_from_content(self, content: str) -> str:
        """Extract speaker names from content."""
        speakers = set()
        
        # Look for patterns like "MR SPEAKER:", "HON. NAME:", etc.
        patterns = [
            r'((?:MR|MS|MRS|DR|HON\.?)\s+[A-Z][A-Z\s\.]+?)[:;]',
            r'(THE\s+(?:SPEAKER|PRIME MINISTER|MINISTER)[A-Z\s]*?)[:;]',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches[:10]:  # Limit to avoid too many matches
                speaker = match.strip().title()
                if len(speaker) > 3 and len(speaker) < 50:
                    speakers.add(speaker)
        
        return '; '.join(sorted(speakers)[:5])  # Limit to top 5 speakers
    
    def get_source_from_path(self, file_path: Path) -> str:
        """Extract source country from file path."""
        parts = file_path.parts
        for part in parts:
            if part in ['Fiji', 'Cook Islands', 'Papua New Guinea', 'PNG']:
                return 'Papua New Guinea' if part == 'PNG' else part
        return 'Unknown'
    
    def process_document(self, html_file: Path, metadata_file: Path = None) -> Dict[str, Any]:
        """Process a single HTML document and its metadata."""
        try:
            # Read HTML content
            with open(html_file, 'r', encoding='utf-8', errors='ignore') as f:
                html_content = f.read()
            
            # Read metadata if available
            metadata = {}
            if metadata_file and metadata_file.exists():
                try:
                    if metadata_file.suffix == '.json':
                        with open(metadata_file, 'r', encoding='utf-8') as f:
                            metadata = json.load(f)
                    else:
                        with open(metadata_file, 'r', encoding='utf-8', errors='ignore') as f:
                            metadata_content = f.read()
                            # Parse simple key:value metadata
                            for line in metadata_content.split('\n'):
                                if ':' in line:
                                    key, value = line.split(':', 1)
                                    metadata[key.strip()] = value.strip()
                except:
                    pass
            
            # Extract content
            content = self.extract_text_from_html(html_content)
            if not content or len(content.strip()) < 50:
                return None
            
            # Extract document information
            title = self.extract_title_from_html(html_content, html_file)
            date = self.parse_date_from_path(html_file)
            speakers = self.extract_speakers_from_content(content)
            source = self.get_source_from_path(html_file)
            
            # Determine document type
            doc_type = 'hansard'
            if 'oral_question' in html_file.name:
                doc_type = 'oral_question'
            elif 'written_question' in html_file.name:
                doc_type = 'written_question'
            
            return {
                'title': title,
                'date': date,
                'speaker': speakers,
                'speaker2': metadata.get('speaker2', ''),
                'document_type': doc_type,
                'content': content,
                'source': source,
                'file_path': str(html_file)
            }
                
        except Exception as e:
            logger.error(f"Error processing {html_file}: {e}")
            
        return None
    
    def save_to_database(self, doc_data: Dict[str, Any]) -> int:
        """Save document to MySQL database."""
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            # Check if document already exists
            cursor.execute(
                "SELECT id FROM documents WHERE title = %s AND date = %s AND SUBSTRING(content, 1, 100) = SUBSTRING(%s, 1, 100)",
                (doc_data['title'], doc_data['date'], doc_data['content'])
            )
            
            existing = cursor.fetchone()
            if existing:
                logger.debug(f"Document already exists: {doc_data['title']}")
                return existing[0]
            
            # Insert new document
            insert_query = """
                INSERT INTO documents (title, date, speaker, speaker2, document_type, content)
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            
            cursor.execute(insert_query, (
                doc_data['title'],
                doc_data['date'],
                doc_data['speaker'][:255] if doc_data['speaker'] else '',
                doc_data['speaker2'][:255] if doc_data['speaker2'] else '',
                doc_data['document_type'],
                doc_data['content']
            ))
            
            doc_id = cursor.lastrowid
            conn.commit()
            
            logger.info(f"Saved document {doc_id}: {doc_data['title']} ({doc_data['source']})")
            return doc_id
            
        except Exception as e:
            logger.error(f"Error saving to database: {e}")
            return None
        finally:
            if 'conn' in locals():
                conn.close()
    
    def chunk_and_index_document(self, doc_id: int, doc_data: Dict[str, Any]):
        """Chunk document and index chunks in Solr."""
        try:
            # Create chunks using our chunker
            chunks = chunk_document(
                content=doc_data['content'],
                title=doc_data['title'],
                date=doc_data['date'],
                speakers=doc_data.get('speaker', ''),
                document_type=doc_data.get('document_type', 'hansard'),
                source=doc_data.get('source', ''),
                doc_id=doc_id
            )
            
            # Prepare chunks for Solr indexing
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
            
            # Index in Solr
            if solr_docs:
                self.solr.add(solr_docs)
                logger.debug(f"Indexed {len(solr_docs)} chunks for document {doc_id}")
                return len(solr_docs)
                
        except Exception as e:
            logger.error(f"Error chunking/indexing document {doc_id}: {e}")
            
        return 0
    
    def find_document_files(self, base_path: Path) -> List[tuple]:
        """Find all HTML documents and their metadata files."""
        documents = []
        
        # Search for HTML files
        for html_file in base_path.rglob("*.html"):
            # Skip certain files
            if html_file.name in ['contents.html']:
                continue
                
            # Find corresponding metadata file
            metadata_file = html_file.with_suffix('.html').parent / f"{html_file.stem}_metadata.txt"
            if not metadata_file.exists():
                # Try JSON metadata
                metadata_file = html_file.parent / 'metadata.json'
                if not metadata_file.exists():
                    metadata_file = None
            
            documents.append((html_file, metadata_file))
        
        return documents
    
    def load_country_data(self, country_path: Path):
        """Load all documents for a specific country."""
        logger.info(f"Loading data from: {country_path}")
        
        documents = self.find_document_files(country_path)
        logger.info(f"Found {len(documents)} documents to process")
        
        processed = 0
        skipped = 0
        total_chunks = 0
        
        for html_file, metadata_file in documents:
            try:
                # Process document
                doc_data = self.process_document(html_file, metadata_file)
                
                if doc_data:
                    # Save to database
                    doc_id = self.save_to_database(doc_data)
                    
                    if doc_id:
                        # Chunk and index
                        chunk_count = self.chunk_and_index_document(doc_id, doc_data)
                        total_chunks += chunk_count
                        processed += 1
                    else:
                        skipped += 1
                else:
                    skipped += 1
                    
            except Exception as e:
                logger.error(f"Error processing {html_file}: {e}")
                skipped += 1
        
        # Commit Solr changes for this country
        try:
            self.solr.commit()
        except:
            pass
            
        logger.info(f"Country {country_path.name}: Processed {processed}, Skipped {skipped}, Chunks {total_chunks}")
        return processed, skipped, total_chunks
    
    def clear_existing_data(self):
        """Clear existing data from database and Solr."""
        try:
            # Clear Solr
            self.solr.delete(q='*:*')
            self.solr.commit()
            logger.info("Cleared Solr index")
            
            # Clear MySQL
            conn = self.get_db_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM documents")
            conn.commit()
            conn.close()
            logger.info("Cleared MySQL documents table")
            
        except Exception as e:
            logger.error(f"Error clearing data: {e}")
    
    def load_all_data(self, clear_first: bool = True):
        """Load all Pacific Hansard data from collections directory."""
        if clear_first:
            self.clear_existing_data()
        
        # Define collections path
        collections_path = Path(__file__).parent.parent / "collections"
        
        if not collections_path.exists():
            logger.error(f"Collections directory not found: {collections_path}")
            return
        
        total_start = datetime.now()
        total_processed = 0
        total_skipped = 0
        total_chunks = 0
        
        # Process each country
        for country_path in collections_path.iterdir():
            if country_path.is_dir():
                country_start = datetime.now()
                processed, skipped, chunks = self.load_country_data(country_path)
                country_duration = datetime.now() - country_start
                
                total_processed += processed
                total_skipped += skipped
                total_chunks += chunks
                
                logger.info(f"Completed {country_path.name} in {country_duration}")
        
        total_duration = datetime.now() - total_start
        
        # Final statistics
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM documents")
            db_docs = cursor.fetchone()[0]
            conn.close()
            
            # Check Solr chunks
            solr_results = self.solr.search('*:*', rows=0)
            solr_chunks = solr_results.hits
            
            logger.info(f"🎉 Data loading complete!")
            logger.info(f"⏱️  Total time: {total_duration}")
            logger.info(f"📊 Documents processed: {total_processed}")
            logger.info(f"⚠️  Documents skipped: {total_skipped}")
            logger.info(f"🗄️  Documents in database: {db_docs}")
            logger.info(f"🔍 Chunks in Solr: {solr_chunks}")
            
        except Exception as e:
            logger.error(f"Error getting final statistics: {e}")

def main():
    """Main entry point."""
    loader = HansardDataLoader()
    
    # Load all data
    logger.info("Starting Pacific Hansard data loading from collections directory...")
    loader.load_all_data(clear_first=True)

if __name__ == "__main__":
    main()