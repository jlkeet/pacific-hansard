#!/usr/bin/env python3
"""
Re-ranker service for improving search result relevance.
Provides a simple query-document relevance scoring mechanism.
"""

import logging
from typing import List, Dict, Any
import re
from rag.api.models.schemas import SearchResult

logger = logging.getLogger(__name__)

class RerankerService:
    """Service for re-ranking search results based on query relevance."""
    
    def __init__(self, enabled: bool = True):
        """
        Initialize re-ranker service.
        
        Args:
            enabled: Whether re-ranking is enabled (can be toggled)
        """
        self.enabled = enabled
        logger.info(f"Re-ranker service initialized (enabled: {enabled})")
    
    def set_enabled(self, enabled: bool):
        """Toggle re-ranker on/off."""
        self.enabled = enabled
        logger.info(f"Re-ranker {'enabled' if enabled else 'disabled'}")
    
    def rerank(self, query: str, results: List[SearchResult], 
               boost_factor: float = 0.1) -> List[SearchResult]:
        """
        Re-rank search results based on query-document relevance.
        
        Args:
            query: Original search query
            results: List of search results to re-rank
            boost_factor: How much to boost relevance scores (0.0 to 1.0)
            
        Returns:
            Re-ranked list of search results
        """
        if not self.enabled or not results:
            return results
        
        try:
            logger.info(f"Re-ranking {len(results)} results for query: '{query}'")
            
            # Calculate relevance scores for each result
            scored_results = []
            query_terms = self._extract_query_terms(query)
            
            for result in results:
                # Calculate content relevance
                relevance_score = self._calculate_relevance(query_terms, result)
                
                # Boost original score with relevance
                new_score = result.score + (boost_factor * relevance_score)
                
                # Create new result with updated score
                reranked_result = SearchResult(
                    id=result.id,
                    doc_id=result.doc_id,
                    text=result.text,
                    speaker=result.speaker,
                    date=result.date,
                    country=result.country,
                    chamber=result.chamber,
                    url=result.url,
                    score=new_score,
                    chunk_index=result.chunk_index
                )
                
                scored_results.append(reranked_result)
            
            # Sort by new scores
            reranked_results = sorted(scored_results, key=lambda x: x.score, reverse=True)
            
            logger.info(f"Re-ranking complete: top score {reranked_results[0].score:.3f}")
            return reranked_results
            
        except Exception as e:
            logger.error(f"Re-ranking failed: {e}")
            return results  # Return original results on error
    
    def _extract_query_terms(self, query: str) -> List[str]:
        """Extract meaningful terms from query."""
        # Convert to lowercase and remove punctuation
        clean_query = re.sub(r'[^\w\s]', ' ', query.lower())
        
        # Split into words and remove stopwords
        stopwords = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with',
            'by', 'about', 'what', 'when', 'where', 'why', 'how', 'who', 'which', 'that',
            'this', 'these', 'those', 'is', 'are', 'was', 'were', 'be', 'been', 'have', 'has',
            'had', 'do', 'does', 'did', 'can', 'could', 'should', 'would', 'will'
        }
        
        terms = [word for word in clean_query.split() 
                if len(word) > 2 and word not in stopwords]
        
        return terms
    
    def _calculate_relevance(self, query_terms: List[str], result: SearchResult) -> float:
        """Calculate relevance score between query terms and document."""
        if not query_terms:
            return 0.0
        
        # Combine title and content for scoring
        content = f"{result.text}".lower()
        
        # Count term matches and calculate features
        term_matches = 0
        total_matches = 0
        phrase_matches = 0
        
        for term in query_terms:
            # Count occurrences of this term
            matches = content.count(term.lower())
            if matches > 0:
                term_matches += 1
                total_matches += matches
        
        # Check for phrase matches (consecutive terms)
        if len(query_terms) > 1:
            query_phrase = ' '.join(query_terms)
            if query_phrase in content:
                phrase_matches = 1
        
        # Calculate relevance features
        term_coverage = term_matches / len(query_terms) if query_terms else 0
        term_frequency = total_matches / max(1, len(content.split()))
        has_phrase = phrase_matches
        
        # Weight the features
        relevance_score = (
            0.5 * term_coverage +      # How many query terms appear
            0.3 * term_frequency +     # How frequently terms appear  
            0.2 * has_phrase           # Bonus for phrase matches
        )
        
        return relevance_score
    
    def get_stats(self) -> Dict[str, Any]:
        """Get re-ranker statistics."""
        return {
            'enabled': self.enabled,
            'service': 'SimpleReranker',
            'features': ['term_coverage', 'term_frequency', 'phrase_matching']
        }


# Global re-ranker service instance
_reranker_service = None

def get_reranker_service(enabled: bool = True) -> RerankerService:
    """Get the global re-ranker service instance."""
    global _reranker_service
    if _reranker_service is None:
        _reranker_service = RerankerService(enabled=enabled)
    return _reranker_service


def main():
    """Test the re-ranker service."""
    from rag.api.models.schemas import SearchResult
    
    print("Testing Re-ranker Service...")
    
    # Create test results
    test_results = [
        SearchResult(
            id="1", doc_id="1", text="The Minister discussed price gouging policies",
            speaker="Minister", date="2021-02-10", country="Fiji", 
            chamber="Parliament", url="", score=0.8, chunk_index=0
        ),
        SearchResult(
            id="2", doc_id="2", text="Parliamentary procedures and Speaker guidelines", 
            speaker="Speaker", date="2021-02-10", country="Fiji",
            chamber="Parliament", url="", score=0.6, chunk_index=0
        )
    ]
    
    # Test re-ranking
    reranker = RerankerService(enabled=True)
    
    query = "Minister price gouging"
    reranked = reranker.rerank(query, test_results)
    
    print(f"Original scores: {[r.score for r in test_results]}")
    print(f"Re-ranked scores: {[r.score for r in reranked]}")
    print(f"Stats: {reranker.get_stats()}")
    print("[SUCCESS] Re-ranker test completed!")


if __name__ == "__main__":
    main()