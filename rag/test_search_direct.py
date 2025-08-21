#!/usr/bin/env python3
"""Test search service directly"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from rag.api.services.search_service import SearchService
from rag.api.models.schemas import SearchRequest

# Create search service
search_service = SearchService()

# Create request
request = SearchRequest(query="Minister", top_k=1, filters={})

# Test the search
import asyncio

async def test_search():
    try:
        results = await search_service.hybrid_search(request)
        print(f"Found {len(results)} results")
        
        for i, result in enumerate(results):
            print(f"\nResult {i}:")
            print(f"  ID: {result.id}")
            print(f"  Doc ID: {result.doc_id}")
            print(f"  Text: {result.text[:100]}...")
            print(f"  Speaker: {result.speaker}")
            print(f"  Date: {result.date}")
            print(f"  Country: {result.country}")
            print(f"  Score: {result.score}")
            print(f"  Chunk Index: {result.chunk_index}")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_search())