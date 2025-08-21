#!/usr/bin/env python3
"""
Debug the topic transition detection
"""
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from rag.chunker import _is_topic_transition, _extract_topic_keywords

test_paragraphs = [
    "The Prime Minister stated that seabed mining regulations need to be strengthened. Several committee members raised questions about the economic benefits versus environmental costs.",
    "Moving to a completely different topic, the committee also discussed nuclear waste transportation laws.",
    "Clause 13: Offence to transport nuclear waste and other radioactive matter. Any person who transports nuclear waste through Cook Islands waters shall be guilty of an offence punishable by imprisonment.",
    "Moving to another topic, the committee reviewed education grants and scholarships."
]

def debug_transitions():
    print("Debugging topic transition detection...")
    
    for i in range(1, len(test_paragraphs)):
        prev_para = test_paragraphs[i-1]
        curr_para = test_paragraphs[i]
        
        print(f"\n--- TRANSITION {i} ---")
        print(f"PREVIOUS: {prev_para[:100]}...")
        print(f"CURRENT:  {curr_para[:100]}...")
        
        # Check topic keywords
        prev_topics = _extract_topic_keywords(prev_para)
        curr_topics = _extract_topic_keywords(curr_para)
        
        print(f"PREV TOPICS: {prev_topics}")
        print(f"CURR TOPICS: {curr_topics}")
        
        # Check transition detection
        is_transition = _is_topic_transition(curr_para, prev_para)
        print(f"TOPIC TRANSITION: {is_transition}")

if __name__ == "__main__":
    debug_transitions()