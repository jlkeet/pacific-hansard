#!/usr/bin/env python3
"""
Test script for the Hansard chunker - can run without database connection
"""

from chunker import HansardChunker
import json
from datetime import datetime

def test_chunker_logic():
    """Test chunking logic with sample data"""
    
    # Mock database config (won't be used in this test)
    mock_db_config = {
        'host': 'localhost',
        'database': 'test',
        'user': 'test',
        'password': 'test'
    }
    
    chunker = HansardChunker(mock_db_config, max_tokens=200, overlap_tokens=50)
    
    # Sample Hansard content with speakers
    sample_content = """
    MR. SPEAKER: Order, order. The House will come to order. We now move to Question Time.
    
    HON. JANE SMITH: Mr. Speaker, I rise to ask the Minister of Health about the tobacco excise policy. What measures is the government taking to reduce smoking rates in our community? This is a critical public health issue that affects all our citizens.
    
    HON. MINISTER OF HEALTH: Thank you, Mr. Speaker. I thank the honourable member for her question. The government has implemented a comprehensive tobacco control strategy. We have increased excise taxes by 10% annually for the past four years. Additionally, we have expanded smoking cessation programs in all health districts. These measures have resulted in a 15% reduction in smoking rates since 2020.
    
    HON. JANE SMITH: Mr. Speaker, I thank the Minister for that response. Can the Minister provide more details about the funding for these cessation programs? How much has been allocated, and are these programs reaching rural communities effectively?
    """
    
    # Create mock document
    mock_document = {
        'id': 1,
        'new_id': 'test-doc-001',
        'content': sample_content,
        'date': datetime(2023, 6, 15),
        'source': 'Cook Islands',
        'document_type': 'Parliamentary Questions'
    }
    
    print("Testing chunker with sample Hansard content...")
    print("=" * 60)
    
    # Process the document
    chunks = chunker.process_document(mock_document)
    
    print(f"Created {len(chunks)} chunks from sample content")
    print("\nChunk Details:")
    print("-" * 60)
    
    for i, chunk in enumerate(chunks):
        print(f"\nChunk {i+1}:")
        print(f"ID: {chunk['id']}")
        print(f"Speaker: {chunk['speaker']}")
        print(f"Tokens: {chunk['tokens']}")
        print(f"Text preview: {chunk['text'][:100]}...")
        print(f"Country: {chunk['country']}")
        print(f"Date: {chunk['date']}")
    
    # Test chunk format
    print("\n" + "=" * 60)
    print("Sample chunk JSON structure:")
    print(json.dumps(chunks[0], indent=2) if chunks else "No chunks created")
    
    # Test speaker extraction
    print("\n" + "=" * 60)
    print("Testing speaker extraction...")
    speakers = chunker.extract_speakers_from_content(sample_content)
    print(f"Extracted {len(speakers)} speaker segments:")
    for i, speaker in enumerate(speakers):
        print(f"{i+1}. {speaker['speaker']}: {len(speaker['text'])} characters")

if __name__ == "__main__":
    test_chunker_logic()