#!/usr/bin/env python3
"""
Hansard Document Chunker for RAG Pipeline

Reads documents from MySQL pacific_hansard_db table and creates 
speaker-aware chunks suitable for embedding and retrieval.

Based on spec: speaker-aware chunking, ~1000 tokens per chunk, 
~120 token overlap, carry metadata forward.
"""

import re
import json
import hashlib
import uuid
from datetime import datetime
from typing import List, Dict, Optional
import argparse
import os

# Optional MySQL import
try:
    import mysql.connector
    MYSQL_AVAILABLE = True
except ImportError:
    MYSQL_AVAILABLE = False
    print("Warning: mysql.connector not available. Database operations will be disabled.")

class HansardChunker:
    def __init__(self, db_config: Dict, max_tokens: int = 1000, overlap_tokens: int = 120):
        self.db_config = db_config
        self.max_tokens = max_tokens
        self.overlap_tokens = overlap_tokens
        
    def connect_db(self):
        """Connect to MySQL database"""
        if not MYSQL_AVAILABLE:
            raise ImportError("mysql.connector not available")
        return mysql.connector.connect(**self.db_config)
    
    def estimate_tokens(self, text: str) -> int:
        """Rough token estimation (1 token ≈ 4 characters for English)"""
        return len(text) // 4
    
    def extract_speakers_from_content(self, content: str) -> List[Dict]:
        """
        Extract speaker segments from Hansard content.
        Looks for patterns like:
        - MR. SPEAKER: Content
        - HON. NAME: Content
        - Speaker Name: Content
        """
        speakers = []
        
        # Split by speaker patterns and process
        # Pattern matches: MR./MS./HON./DR./MADAM/SIR followed by name and colon
        speaker_pattern = r'((?:MR\.|MS\.|HON\.|DR\.|MADAM|SIR)\s+[A-Z\s\-\.]+?):'
        
        # Split content by speaker patterns
        parts = re.split(speaker_pattern, content, flags=re.IGNORECASE)
        
        if len(parts) > 1:
            # First part before any speaker (often empty or general content)
            if parts[0].strip():
                speakers.append({
                    'speaker': 'Document Header',
                    'text': parts[0].strip(),
                    'start_pos': 0,
                    'end_pos': len(parts[0])
                })
            
            # Process speaker segments
            for i in range(1, len(parts), 2):
                if i + 1 < len(parts):
                    speaker_name = parts[i].strip()
                    speaker_text = parts[i + 1].strip()
                    
                    if speaker_text and len(speaker_text) > 10:
                        speakers.append({
                            'speaker': speaker_name,
                            'text': speaker_text,
                            'start_pos': len(''.join(parts[:i+1])),
                            'end_pos': len(''.join(parts[:i+2]))
                        })
        
        # If no speakers found, treat whole content as single segment  
        if not speakers:
            speakers.append({
                'speaker': 'Unknown Speaker',
                'text': content.strip(),
                'start_pos': 0,
                'end_pos': len(content)
            })
            
        return speakers
    
    def chunk_speaker_segment(self, speaker: str, text: str, base_metadata: Dict, start_index: int = 0) -> List[Dict]:
        """
        Chunk a single speaker's text into token-sized pieces with overlap.
        """
        chunks = []
        words = text.split()
        
        if not words:
            return chunks
            
        current_chunk = []
        current_tokens = 0
        
        for word in words:
            word_tokens = self.estimate_tokens(word + " ")
            
            # If adding this word exceeds max tokens, finalize current chunk
            if current_tokens + word_tokens > self.max_tokens and current_chunk:
                chunk_text = " ".join(current_chunk)
                chunks.append(self.create_chunk(speaker, chunk_text, base_metadata, start_index + len(chunks)))
                
                # Start new chunk with overlap
                overlap_words = self.get_overlap_words(current_chunk)
                current_chunk = overlap_words + [word]
                current_tokens = sum(self.estimate_tokens(w + " ") for w in current_chunk)
            else:
                current_chunk.append(word)
                current_tokens += word_tokens
        
        # Add final chunk if we have content
        if current_chunk:
            chunk_text = " ".join(current_chunk)
            chunks.append(self.create_chunk(speaker, chunk_text, base_metadata, start_index + len(chunks)))
            
        return chunks
    
    def get_overlap_words(self, words: List[str]) -> List[str]:
        """Get the last N words for overlap based on token estimate"""
        overlap_words = []
        tokens_count = 0
        
        for word in reversed(words):
            word_tokens = self.estimate_tokens(word + " ")
            if tokens_count + word_tokens > self.overlap_tokens:
                break
            overlap_words.insert(0, word)
            tokens_count += word_tokens
            
        return overlap_words
    
    def create_chunk(self, speaker: str, text: str, base_metadata: Dict, chunk_index: int) -> Dict:
        """Create a standardized chunk following the spec"""
        chunk_id = f"{base_metadata['doc_id']}_chunk_{chunk_index}"
        
        return {
            "id": chunk_id,
            "doc_id": base_metadata['doc_id'],
            "text": text.strip(),
            "date": base_metadata['date'],
            "country": base_metadata['country'],
            "chamber": base_metadata.get('chamber', 'Parliament'),
            "speaker": speaker,
            "url": base_metadata.get('url', ''),
            "page_from": base_metadata.get('page_from', 1),
            "page_to": base_metadata.get('page_to', 1),
            "para_ids": [f"{base_metadata['doc_id']}_p{chunk_index}"],
            "chunk_index": chunk_index,
            "tokens": self.estimate_tokens(text),
            "document_type": base_metadata.get('document_type', 'Hansard Document'),
            "source": base_metadata.get('source', ''),
            "hash": hashlib.md5(text.encode()).hexdigest()
        }
    
    def clean_content(self, content: str) -> str:
        """Clean and normalize document content"""
        if not content:
            return ""
            
        # Remove HTML tags if present
        content = re.sub(r'<[^>]+>', ' ', content)
        
        # Normalize whitespace
        content = re.sub(r'\s+', ' ', content)
        
        # Remove common OCR artifacts
        content = re.sub(r'[^\w\s\.\,\;\:\!\?\-\(\)\"\'\/]', ' ', content)
        
        # Fix hyphenated words at line breaks
        content = re.sub(r'(\w+)-\s+(\w+)', r'\1\2', content)
        
        return content.strip()
    
    def process_document(self, doc: Dict) -> List[Dict]:
        """Process a single document from the database into chunks"""
        
        # Create base metadata
        base_metadata = {
            'doc_id': doc['new_id'] or str(uuid.uuid4()),
            'date': doc['date'].strftime('%Y-%m-%d') if doc['date'] else None,
            'country': self.normalize_country(doc['source']),
            'document_type': doc['document_type'],
            'source': doc['source'],
            'url': f"/article.php?id={doc['id']}" if doc.get('id') else ''
        }
        
        # Clean content
        content = self.clean_content(doc['content'])
        if not content:
            return []
        
        # Extract speaker segments
        speaker_segments = self.extract_speakers_from_content(content)
        
        # Create chunks for each speaker segment
        all_chunks = []
        chunk_counter = 0
        for segment in speaker_segments:
            speaker_chunks = self.chunk_speaker_segment(
                segment['speaker'], 
                segment['text'], 
                base_metadata,
                chunk_counter
            )
            all_chunks.extend(speaker_chunks)
            chunk_counter += len(speaker_chunks)
        
        return all_chunks
    
    def normalize_country(self, source: str) -> str:
        """Normalize country/source names"""
        country_map = {
            'Cook Islands': 'Cook Islands',
            'Fiji': 'Fiji', 
            'Papua New Guinea': 'Papua New Guinea',
            'Solomon Islands': 'Solomon Islands'
        }
        return country_map.get(source, source)
    
    def chunk_all_documents(self, output_file: str, limit: Optional[int] = None):
        """Process all documents and write chunks to JSONL file"""
        
        print(f"Starting document chunking process...")
        print(f"Max tokens per chunk: {self.max_tokens}")
        print(f"Overlap tokens: {self.overlap_tokens}")
        
        connection = self.connect_db()
        cursor = connection.cursor(dictionary=True)
        
        # Get total document count
        cursor.execute("SELECT COUNT(*) as total FROM pacific_hansard_db")
        total_docs = cursor.fetchone()['total']
        print(f"Total documents in database: {total_docs}")
        
        # Query documents
        query = "SELECT * FROM pacific_hansard_db ORDER BY date DESC, id"
        if limit:
            query += f" LIMIT {limit}"
            
        cursor.execute(query)
        
        total_chunks = 0
        processed_docs = 0
        
        with open(output_file, 'w', encoding='utf-8') as f:
            for doc in cursor:
                try:
                    chunks = self.process_document(doc)
                    
                    for chunk in chunks:
                        f.write(json.dumps(chunk) + '\n')
                        total_chunks += 1
                    
                    processed_docs += 1
                    
                    if processed_docs % 10 == 0:
                        print(f"Processed {processed_docs}/{total_docs if not limit else limit} documents, {total_chunks} chunks created")
                        
                except Exception as e:
                    print(f"Error processing document {doc.get('id', 'unknown')}: {str(e)}")
                    continue
        
        cursor.close()
        connection.close()
        
        print(f"\nChunking complete!")
        print(f"Processed {processed_docs} documents")
        print(f"Created {total_chunks} chunks")
        print(f"Output saved to: {output_file}")
        
        return total_chunks

def chunk_document(content: str, title: str, date: str, speakers: str = "", 
                   document_type: str = "hansard", source: str = "", doc_id: int = None) -> List[Dict]:
    """
    Robust document chunking with proper overlap and fallback strategies.
    Returns list of chunks with metadata.
    """
    # Create base metadata
    base_metadata = {
        'title': title,
        'date': date,
        'speakers': speakers,
        'document_type': document_type,
        'source': source,
        'document_id': doc_id
    }
    
    # Chunking parameters
    chunks = []
    max_chars = 4000  # ~1000 tokens
    overlap_chars = 480  # ~120 tokens
    chunk_index = 0
    
    # Clean content and normalize whitespace
    content = content.strip()
    content = re.sub(r'\s+', ' ', content)  # Normalize whitespace
    
    if not content:
        return chunks
    
    # Strategy 1: Look for topic transitions and natural break points
    paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
    
    # If we have multiple paragraphs, use intelligent paragraph-based chunking
    if len(paragraphs) > 1:
        current_chunk = ""
        
        for i, paragraph in enumerate(paragraphs):
            # Check for topic transition signals
            is_topic_break = _is_topic_transition(paragraph, paragraphs[i-1] if i > 0 else "")
            
            # Check if adding this paragraph exceeds max size
            test_chunk = current_chunk + ('\n\n' if current_chunk else '') + paragraph
            
            # Split if: size exceeded OR we detect a clear topic transition with reasonable content
            size_exceeded = len(test_chunk) > max_chars and current_chunk
            topic_split = is_topic_break and len(current_chunk) > 500  # Minimum 500 chars for topic splits
            
            should_split = size_exceeded or topic_split
            
            if should_split:
                # Create chunk from current content
                chunk = {
                    'chunk_id': f"{doc_id}_{chunk_index}" if doc_id else f"chunk_{chunk_index}",
                    'content': current_chunk.strip(),
                    'chunk_index': chunk_index,
                    'token_count': len(current_chunk) // 4,
                    'metadata': base_metadata.copy()
                }
                chunks.append(chunk)
                chunk_index += 1
                
                # For topic transitions, start fresh; otherwise use overlap
                if is_topic_break:
                    current_chunk = paragraph  # Fresh start for new topic
                else:
                    # Start new chunk with overlap from previous chunk
                    overlap_text = _get_text_overlap(current_chunk, overlap_chars)
                    current_chunk = overlap_text + ('\n\n' if overlap_text else '') + paragraph
            else:
                # Add paragraph to current chunk
                current_chunk = test_chunk
        
        # Add final chunk
        if current_chunk.strip():
            chunk = {
                'chunk_id': f"{doc_id}_{chunk_index}" if doc_id else f"chunk_{chunk_index}",
                'content': current_chunk.strip(),
                'chunk_index': chunk_index,
                'token_count': len(current_chunk) // 4,
                'metadata': base_metadata.copy()
            }
            chunks.append(chunk)
    
    else:
        # Strategy 2: Sentence-based chunking for single paragraph or no paragraph breaks
        # Split by sentence endings while preserving the punctuation
        sentences = re.split(r'(?<=[.!?])\s+', content)
        current_chunk = ""
        
        for sentence in sentences:
            test_chunk = current_chunk + (' ' if current_chunk else '') + sentence
            
            if len(test_chunk) > max_chars and current_chunk:
                # Create chunk
                chunk = {
                    'chunk_id': f"{doc_id}_{chunk_index}" if doc_id else f"chunk_{chunk_index}",
                    'content': current_chunk.strip(),
                    'chunk_index': chunk_index,
                    'token_count': len(current_chunk) // 4,
                    'metadata': base_metadata.copy()
                }
                chunks.append(chunk)
                chunk_index += 1
                
                # Start new chunk with overlap
                overlap_text = _get_text_overlap(current_chunk, overlap_chars)
                current_chunk = overlap_text + (' ' if overlap_text else '') + sentence
            else:
                current_chunk = test_chunk
        
        # Add final chunk
        if current_chunk.strip():
            chunk = {
                'chunk_id': f"{doc_id}_{chunk_index}" if doc_id else f"chunk_{chunk_index}",
                'content': current_chunk.strip(),
                'chunk_index': chunk_index,
                'token_count': len(current_chunk) // 4,
                'metadata': base_metadata.copy()
            }
            chunks.append(chunk)
    
    # Strategy 3: Force split if we still have chunks that are too large
    final_chunks = []
    for chunk in chunks:
        if len(chunk['content']) > max_chars * 1.5:  # 50% tolerance
            # Force split this oversized chunk
            force_split_chunks = _force_split_chunk(chunk, max_chars, overlap_chars, base_metadata)
            final_chunks.extend(force_split_chunks)
        else:
            final_chunks.append(chunk)
    
    # Re-index final chunks
    for i, chunk in enumerate(final_chunks):
        chunk['chunk_index'] = i
        chunk['chunk_id'] = f"{doc_id}_{i}" if doc_id else f"chunk_{i}"
    
    return final_chunks


def _is_topic_transition(current_paragraph: str, previous_paragraph: str) -> bool:
    """
    Detect if current paragraph represents a topic transition.
    Returns True if we should consider starting a new chunk here.
    """
    if not previous_paragraph:
        return False
    
    current_lower = current_paragraph.lower()
    
    # Strong topic transition signals
    topic_signals = [
        'moving to a completely different topic',
        'moving to another topic',
        'turning to a different matter',
        'in other business',
        'moving on to',
        'next item on the agenda',
        'another matter',
        'different subject',
        'separate issue',
        'unrelated matter',
        'clause',  # Legislative clause changes
        'section',  # Document section changes
        'part',    # Document part changes
        'schedule'  # Legislative schedule changes
    ]
    
    # Check for explicit topic transition phrases
    for signal in topic_signals:
        if signal in current_lower:
            return True
    
    # Check for speaker changes (often indicate topic shifts)
    speaker_patterns = [
        r'^(mr\.|ms\.|mrs\.|dr\.|hon\.|the\s+speaker|minister)',
        r'^[A-Z][A-Z\s]+:',  # All caps speaker names
    ]
    
    for pattern in speaker_patterns:
        if re.match(pattern, current_paragraph, re.IGNORECASE):
            return True
    
    # Check for dramatic topic keyword differences
    # Extract key topics from both paragraphs
    current_topics = _extract_topic_keywords(current_paragraph)
    previous_topics = _extract_topic_keywords(previous_paragraph)
    
    # If current paragraph has completely different keywords, it's likely a new topic
    if current_topics and previous_topics:
        overlap = current_topics.intersection(previous_topics)
        if len(overlap) == 0 and len(current_topics) >= 2:  # No overlap and substantial content
            return True
    
    return False


def _extract_topic_keywords(text: str) -> set:
    """Extract key topic words from text for topic detection."""
    text_lower = text.lower()
    
    # Important topic categories for Pacific Hansard
    topic_keywords = {
        # Environmental
        'environment', 'environmental', 'climate', 'conservation', 'pollution',
        'seabed', 'mining', 'ocean', 'marine', 'fishing', 'coral', 'reef',
        
        # Legal/Legislative
        'law', 'legal', 'regulation', 'clause', 'section', 'act', 'bill',
        'nuclear', 'waste', 'radioactive', 'transport', 'offence',
        
        # Economic
        'economy', 'economic', 'trade', 'business', 'industry', 'development',
        'budget', 'finance', 'revenue', 'tax', 'vat',
        
        # Social
        'education', 'health', 'housing', 'employment', 'social', 'community',
        'grant', 'scholarship', 'boarding', 'school',
        
        # Political
        'government', 'parliament', 'minister', 'committee', 'vote', 'policy'
    }
    
    found_keywords = set()
    for keyword in topic_keywords:
        if keyword in text_lower:
            found_keywords.add(keyword)
    
    return found_keywords


def _get_text_overlap(text: str, overlap_chars: int) -> str:
    """Get overlap text from the end of current chunk."""
    if len(text) <= overlap_chars:
        return text
    
    # Try to break at word boundaries
    words = text.split()
    overlap_text = ""
    
    for word in reversed(words):
        test_overlap = word + (' ' + overlap_text if overlap_text else '')
        if len(test_overlap) > overlap_chars:
            break
        overlap_text = test_overlap
    
    return overlap_text


def _force_split_chunk(chunk: Dict, max_chars: int, overlap_chars: int, base_metadata: Dict) -> List[Dict]:
    """Force split an oversized chunk by character count."""
    content = chunk['content']
    sub_chunks = []
    start_idx = 0
    chunk_idx = 0
    
    while start_idx < len(content):
        end_idx = start_idx + max_chars
        
        # If not the last chunk, try to break at word boundary
        if end_idx < len(content):
            # Look backwards for a space to break at
            for i in range(end_idx, max(start_idx, end_idx - 100), -1):
                if content[i] == ' ':
                    end_idx = i
                    break
        
        chunk_content = content[start_idx:end_idx].strip()
        
        if chunk_content:
            sub_chunk = {
                'chunk_id': f"{chunk['chunk_id']}_split_{chunk_idx}",
                'content': chunk_content,
                'chunk_index': chunk_idx,
                'token_count': len(chunk_content) // 4,
                'metadata': base_metadata.copy()
            }
            sub_chunks.append(sub_chunk)
            chunk_idx += 1
        
        # Move start index with overlap
        start_idx = max(end_idx - overlap_chars, start_idx + 1)
    
    return sub_chunks

def get_db_config():
    """Get database configuration from environment or config file"""
    try:
        # Try to import from existing config
        from db_config import get_db_config as get_config
        return get_config()
    except ImportError:
        # Fallback to environment variables
        return {
            'host': os.getenv('DB_HOST', 'localhost'),
            'database': os.getenv('DB_NAME', 'pacific_hansard_db'),
            'user': os.getenv('DB_USER', 'hansard_user'),
            'password': os.getenv('DB_PASSWORD', 'test_pass'),
            'port': int(os.getenv('DB_PORT', '3307'))
        }

def main():
    parser = argparse.ArgumentParser(description='Chunk Hansard documents for RAG pipeline')
    parser.add_argument('--output', '-o', default='data/hansard_chunks.jsonl', 
                       help='Output JSONL file path')
    parser.add_argument('--max-tokens', type=int, default=1000,
                       help='Maximum tokens per chunk')
    parser.add_argument('--overlap', type=int, default=120,
                       help='Overlap tokens between chunks')
    parser.add_argument('--limit', type=int, help='Limit number of documents to process')
    
    args = parser.parse_args()
    
    # Ensure output directory exists
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    
    # Get database config
    db_config = get_db_config()
    
    # Initialize chunker
    chunker = HansardChunker(
        db_config=db_config,
        max_tokens=args.max_tokens,
        overlap_tokens=args.overlap
    )
    
    # Process documents
    total_chunks = chunker.chunk_all_documents(args.output, args.limit)
    
    print(f"\nReady for embedding generation with {total_chunks} chunks!")

if __name__ == "__main__":
    main()