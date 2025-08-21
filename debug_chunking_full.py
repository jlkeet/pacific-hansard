#!/usr/bin/env python3
"""
Debug the complete chunking process
"""
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from rag.chunker import _is_topic_transition
import re

# Test content - same as in test_chunking.py 
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

Final recommendations include: 1) Comprehensive environmental review, 2) Public consultation process, 3) Updated regulatory framework for seabed mining operations.""" * 2  # Same as test file

def debug_chunking_process():
    print("Debugging complete chunking process...")
    print(f"Total content length: {len(test_content)} characters")
    
    max_chars = 4000
    paragraphs = [p.strip() for p in test_content.split('\n\n') if p.strip()]
    
    print(f"Found {len(paragraphs)} paragraphs")
    
    current_chunk = ""
    chunk_index = 0
    
    for i, paragraph in enumerate(paragraphs):
        print(f"\n--- PARAGRAPH {i} ---")
        print(f"Content: {paragraph[:100]}...")
        print(f"Length: {len(paragraph)} chars")
        
        # Check for topic transition
        is_topic_break = _is_topic_transition(paragraph, paragraphs[i-1] if i > 0 else "") if i > 0 else False
        print(f"Topic transition: {is_topic_break}")
        
        # Check size if we add this paragraph
        test_chunk = current_chunk + ('\n\n' if current_chunk else '') + paragraph
        print(f"Current chunk length: {len(current_chunk)}")
        print(f"Test chunk length: {len(test_chunk)}")
        
        # Calculate thresholds
        size_threshold = max_chars
        topic_threshold = 500  # Fixed 500 chars
        
        print(f"Size threshold: {size_threshold}")
        print(f"Topic threshold: {topic_threshold}")
        
        # Determine if we should split
        size_exceeded = len(test_chunk) > max_chars and current_chunk
        topic_split = is_topic_break and len(current_chunk) > topic_threshold
        
        should_split = size_exceeded or topic_split
        
        print(f"Size exceeded: {size_exceeded}")
        print(f"Topic split: {topic_split}")
        print(f"Should split: {should_split}")
        
        if should_split:
            print(f"CREATING CHUNK {chunk_index}: {len(current_chunk)} chars")
            chunk_index += 1
            
            if is_topic_break:
                current_chunk = paragraph  # Fresh start
                print("Starting fresh (topic break)")
            else:
                # Would use overlap here
                current_chunk = paragraph  # Simplified for debug
                print("Using overlap (size break)")
        else:
            current_chunk = test_chunk
            print("Adding to current chunk")
    
    # Final chunk
    if current_chunk.strip():
        print(f"\nFINAL CHUNK {chunk_index}: {len(current_chunk)} chars")
        chunk_index += 1
    
    print(f"\nTotal chunks would be created: {chunk_index}")

if __name__ == "__main__":
    debug_chunking_process()