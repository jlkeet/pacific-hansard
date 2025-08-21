#!/usr/bin/env python3
"""
Test the improved chunking function
"""
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from rag.chunker import chunk_document

# Test with a large document that contains multiple topics with clear breaks
test_content = """This is a sample Hansard document discussing seabed mining in the Cook Islands. The government has expressed serious concerns about the environmental impact of deep sea mining operations.

The Prime Minister stated that seabed mining regulations need to be strengthened. Several committee members raised questions about the economic benefits versus environmental costs.

SPEAKER: The honorable minister will now address the concerns about seabed mining licensing procedures.

MINISTER OF ENVIRONMENT: Thank you Mr. Speaker. The government position on seabed mining is clear - we must balance economic opportunity with environmental protection. We have conducted extensive studies on the marine ecosystem impacts.

Moving to a completely different topic, the committee also discussed nuclear waste transportation laws.

Clause 13: Offence to transport nuclear waste and other radioactive matter. Any person who transports nuclear waste through Cook Islands waters shall be guilty of an offence punishable by imprisonment.

The nuclear waste legislation represents a separate issue from seabed mining, though both relate to environmental protection. The legal framework for radioactive materials requires strict enforcement.

Moving to another topic, the committee reviewed education grants and scholarships.

The Minister of Education announced new boarding school grants for outer island students. VAT increases were also discussed to fund these education initiatives.

Back to seabed mining - the committee recommended a moratorium on new mining licenses until environmental impact assessments are completed. The mining industry has opposed this recommendation.

Final recommendations include: 1) Comprehensive environmental review, 2) Public consultation process, 3) Updated regulatory framework for seabed mining operations.""" * 2  # Make it longer to test chunking

def test_chunking():
    print("Testing improved chunking function...")
    print(f"Test document length: {len(test_content)} characters")
    
    chunks = chunk_document(
        content=test_content,
        title="Test Hansard Document", 
        date="2024-01-15",
        speakers="Prime Minister, Minister of Environment",
        document_type="hansard",
        source="Cook Islands",
        doc_id=999
    )
    
    print(f"Generated {len(chunks)} chunks")
    
    for i, chunk in enumerate(chunks):
        print(f"\nCHUNK {i}:")
        print(f"   ID: {chunk['chunk_id']}")
        print(f"   Length: {len(chunk['content'])} chars")
        print(f"   Token estimate: {chunk['token_count']}")
        print(f"   Content preview: {chunk['content'][:150]}...")
        
        # Check if this chunk contains mixed topics (the problem we're solving)
        content_lower = chunk['content'].lower()
        has_seabed = 'seabed' in content_lower or 'mining' in content_lower
        has_nuclear = 'nuclear' in content_lower or 'clause 13' in content_lower
        
        if has_seabed and has_nuclear:
            print(f"   WARNING: This chunk contains BOTH seabed mining AND nuclear waste topics!")
        elif has_seabed:
            print(f"   Topic: Seabed mining")
        elif has_nuclear:
            print(f"   Topic: Nuclear waste")
        else:
            print(f"   Topic: General/Other")
    
    # Check total length coverage
    total_chunk_length = sum(len(chunk['content']) for chunk in chunks)
    print(f"\nCHUNKING STATISTICS:")
    print(f"   Original length: {len(test_content)} chars")
    print(f"   Total chunk length: {total_chunk_length} chars")
    print(f"   Coverage ratio: {total_chunk_length/len(test_content):.2f}")
    
    # Check for reasonable chunk sizes
    oversized = [c for c in chunks if len(c['content']) > 6000]  # 50% over limit
    undersized = [c for c in chunks if len(c['content']) < 500]   # Very small
    
    if oversized:
        print(f"   WARNING: {len(oversized)} chunks are oversized (>6000 chars)")
    if undersized:
        print(f"   WARNING: {len(undersized)} chunks are undersized (<500 chars)")
    
    if not oversized and not undersized:
        print(f"   SUCCESS: All chunks are reasonably sized!")

if __name__ == "__main__":
    test_chunking()