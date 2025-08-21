"""
Enhanced Search Service with Multi-Pass Retrieval and Query Analysis
"""

import logging
import re
from typing import List, Dict, Set, Any, Optional
from dataclasses import dataclass
from rag.api.models.schemas import SearchRequest, SearchResult
from .search_service import SearchService

logger = logging.getLogger(__name__)

@dataclass
class QueryAnalysis:
    """Analysis of user query to guide retrieval strategy"""
    intent: str  # 'position', 'factual', 'timeline', 'comparison', 'general'
    entities: List[str]  # Key entities like "seabed mining", "Prime Minister"
    topics: List[str]  # Broader topics
    time_indicators: List[str]  # "recent", "last year", etc.
    authority_level: str  # 'official', 'discussion', 'any'
    expanded_terms: List[str]  # Synonyms and related terms
    
class EnhancedSearchService:
    """Advanced search service with multi-pass retrieval and query analysis"""
    
    def __init__(self, base_search_service: SearchService):
        self.search_service = base_search_service
        
        # Parliamentary terminology mappings
        self.term_expansions = {
            'stance': ['position', 'policy', 'view', 'opinion', 'approach'],
            'government': ['administration', 'cabinet', 'minister', 'ministry', 'official'],
            'seabed mining': ['deep sea mining', 'ocean mining', 'seabed minerals', 'marine mining', 'nodule mining'],
            'exploration': ['prospecting', 'survey', 'investigation', 'research', 'study'],
            'regulation': ['law', 'legislation', 'rule', 'policy', 'framework', 'governance'],
            'license': ['permit', 'authorization', 'approval', 'certificate'],
            'environment': ['environmental', 'ecology', 'marine', 'ocean', 'conservation'],
            'economy': ['economic', 'financial', 'revenue', 'income', 'development']
        }
        
        # Authority indicators for prioritizing official statements
        self.authority_indicators = {
            'high': ['prime minister', 'minister', 'government', 'cabinet', 'official statement'],
            'medium': ['member of parliament', 'mp', 'honorable', 'speaker'],
            'low': ['committee', 'discussion', 'debate', 'question']
        }
        
    async def enhanced_search(self, request: SearchRequest) -> List[SearchResult]:
        """
        Perform enhanced multi-pass search with query analysis
        """
        try:
            logger.info(f"🔍 Enhanced search starting for: '{request.query}'")
            
            # Step 1: Analyze the query
            analysis = self._analyze_query(request.query)
            logger.info(f"📊 Query analysis: {analysis.intent} intent, {len(analysis.entities)} entities, expanded: {analysis.expanded_terms[:3]}")
            
            # Step 2: Multi-pass retrieval
            all_results = []
            
            # Pass 1: Original query (baseline)
            try:
                original_results = await self.search_service.hybrid_search(request)
                all_results.extend(original_results)
                logger.info(f"🎯 Pass 1 (original): {len(original_results)} results")
            except Exception as e:
                logger.error(f"❌ Pass 1 failed: {e}")
            
            # Pass 2: Expanded query with synonyms
            try:
                expanded_request = self._create_expanded_query(request, analysis)
                logger.info(f"🔄 Expanded query: '{expanded_request.query}'")
                expanded_results = await self.search_service.hybrid_search(expanded_request)
                all_results.extend(expanded_results)
                logger.info(f"🎯 Pass 2 (expanded): {len(expanded_results)} results")
            except Exception as e:
                logger.error(f"❌ Pass 2 failed: {e}")
            
            # Pass 3: Entity-focused search
            try:
                entity_results = await self._entity_focused_search(request, analysis)
                all_results.extend(entity_results)
                logger.info(f"🎯 Pass 3 (entities): {len(entity_results)} results")
            except Exception as e:
                logger.error(f"❌ Pass 3 failed: {e}")
            
            # Pass 4: Authority-prioritized search (for position/policy questions)
            if analysis.intent in ['position', 'policy'] or 'stance' in request.query.lower():
                try:
                    authority_results = await self._authority_search(request, analysis)
                    all_results.extend(authority_results)
                    logger.info(f"🎯 Pass 4 (authority): {len(authority_results)} results")
                except Exception as e:
                    logger.error(f"❌ Pass 4 failed: {e}")
            
            logger.info(f"📊 Total results before deduplication: {len(all_results)}")
            
            # Step 3: Deduplicate and rerank
            unique_results = self._deduplicate_results(all_results)
            logger.info(f"📊 Unique results after deduplication: {len(unique_results)}")
            
            reranked_results = self._intelligent_rerank(unique_results, analysis)
            logger.info(f"📊 Results after reranking: {len(reranked_results)}")
            
            # Step 4: Select diverse, high-quality chunks
            final_results = self._select_diverse_chunks(reranked_results, request.top_k, analysis)
            
            logger.info(f"✅ Enhanced search complete: {len(final_results)} final results")
            return final_results
            
        except Exception as e:
            logger.error(f"❌ Enhanced search failed completely: {e}")
            # Fallback to regular search
            logger.info("🔄 Falling back to regular hybrid search")
            return await self.search_service.hybrid_search(request)
    
    def _analyze_query(self, query: str) -> QueryAnalysis:
        """Analyze query to understand intent and extract key information"""
        query_lower = query.lower()
        
        # Determine intent
        intent = 'general'
        if any(word in query_lower for word in ['stance', 'position', 'policy', 'view', 'approach']):
            intent = 'position'
        elif any(word in query_lower for word in ['when', 'date', 'time', 'recent', 'latest']):
            intent = 'timeline'
        elif any(word in query_lower for word in ['compare', 'difference', 'versus', 'vs']):
            intent = 'comparison'
        elif any(word in query_lower for word in ['what', 'how', 'why', 'explain']):
            intent = 'factual'
        
        # Extract entities (key terms)
        entities = []
        for term, synonyms in self.term_expansions.items():
            if term in query_lower or any(syn in query_lower for syn in synonyms):
                entities.append(term)
        
        # Extract topics (broader categories)
        topics = []
        topic_patterns = {
            'mining': ['mining', 'extraction', 'seabed', 'minerals'],
            'environment': ['environment', 'marine', 'ocean', 'conservation'],
            'economy': ['economy', 'economic', 'financial', 'revenue'],
            'governance': ['government', 'policy', 'regulation', 'law'],
            'international': ['china', 'cooperation', 'agreement', 'treaty']
        }
        
        for topic, keywords in topic_patterns.items():
            if any(keyword in query_lower for keyword in keywords):
                topics.append(topic)
        
        # Detect time indicators
        time_indicators = []
        time_patterns = ['recent', 'latest', 'current', 'now', 'today', 'this year', 'last year']
        for pattern in time_patterns:
            if pattern in query_lower:
                time_indicators.append(pattern)
        
        # Determine authority level needed
        authority_level = 'any'
        if any(word in query_lower for word in ['government', 'official', 'minister', 'policy']):
            authority_level = 'official'
        elif any(word in query_lower for word in ['discussion', 'debate', 'opinion']):
            authority_level = 'discussion'
        
        # Generate expanded terms
        expanded_terms = []
        for entity in entities:
            if entity in self.term_expansions:
                expanded_terms.extend(self.term_expansions[entity])
        
        return QueryAnalysis(
            intent=intent,
            entities=entities,
            topics=topics,
            time_indicators=time_indicators,
            authority_level=authority_level,
            expanded_terms=expanded_terms
        )
    
    def _create_expanded_query(self, request: SearchRequest, analysis: QueryAnalysis) -> SearchRequest:
        """Create expanded query with synonyms and related terms"""
        expanded_query = request.query
        
        # Add key expanded terms
        if analysis.expanded_terms:
            # Take top 3 most relevant expanded terms to avoid query bloat
            top_expansions = analysis.expanded_terms[:3]
            expanded_query += " " + " ".join(top_expansions)
        
        # Add topic-specific terms
        if 'mining' in analysis.topics:
            expanded_query += " exploration license regulation"
        if 'governance' in analysis.topics:
            expanded_query += " government minister policy"
        
        return SearchRequest(
            query=expanded_query,
            filters=request.filters,
            top_k=request.top_k
        )
    
    async def _entity_focused_search(self, request: SearchRequest, analysis: QueryAnalysis) -> List[SearchResult]:
        """Search focusing on specific entities"""
        if not analysis.entities:
            return []
        
        # Create entity-focused query
        entity_query = " ".join(analysis.entities)
        
        entity_request = SearchRequest(
            query=entity_query,
            filters=request.filters,
            top_k=request.top_k
        )
        
        return await self.search_service.hybrid_search(entity_request)
    
    async def _authority_search(self, request: SearchRequest, analysis: QueryAnalysis) -> List[SearchResult]:
        """Search prioritizing authoritative sources for policy questions"""
        authority_terms = []
        
        if analysis.authority_level == 'official':
            authority_terms = self.authority_indicators['high']
        else:
            authority_terms = self.authority_indicators['medium']
        
        # Create authority-enhanced query
        authority_query = request.query + " " + " ".join(authority_terms[:2])
        
        authority_request = SearchRequest(
            query=authority_query,
            filters=request.filters,
            top_k=request.top_k
        )
        
        return await self.search_service.hybrid_search(authority_request)
    
    def _deduplicate_results(self, results: List[SearchResult]) -> List[SearchResult]:
        """Remove duplicate results based on document ID and chunk index"""
        seen = set()
        unique_results = []
        
        for result in results:
            # Use combination of doc_id and chunk_index as unique identifier
            key = f"{result.doc_id}_{result.chunk_index}"
            if key not in seen:
                seen.add(key)
                unique_results.append(result)
        
        return unique_results
    
    def _intelligent_rerank(self, results: List[SearchResult], analysis: QueryAnalysis) -> List[SearchResult]:
        """Rerank results based on query analysis"""
        
        def calculate_relevance_score(result: SearchResult) -> float:
            base_score = result.score
            bonus = 0.0
            
            content_lower = result.text.lower()
            
            # Bonus for authority level match
            if analysis.authority_level == 'official':
                if any(auth in content_lower for auth in self.authority_indicators['high']):
                    bonus += 0.3
            
            # Bonus for entity matches
            entity_matches = sum(1 for entity in analysis.entities if entity in content_lower)
            bonus += entity_matches * 0.2
            
            # Bonus for intent-specific content
            if analysis.intent == 'position':
                if any(word in content_lower for word in ['position', 'stance', 'policy', 'approach']):
                    bonus += 0.25
            elif analysis.intent == 'factual':
                if any(word in content_lower for word in ['act', 'regulation', 'law', 'bill']):
                    bonus += 0.25
            
            # Penalty for very short chunks (likely incomplete)
            if len(result.text) < 200:
                bonus -= 0.1
            
            return base_score + bonus
        
        # Calculate new scores and sort
        for result in results:
            result.score = calculate_relevance_score(result)
        
        return sorted(results, key=lambda x: x.score, reverse=True)
    
    def _select_diverse_chunks(self, results: List[SearchResult], top_k: int, analysis: QueryAnalysis) -> List[SearchResult]:
        """Select diverse, high-quality chunks avoiding redundancy"""
        if not results:
            return []
        
        selected = []
        used_docs = set()
        used_speakers = set()
        
        # First pass: Select highest scoring results with diversity constraints
        for result in results:
            if len(selected) >= top_k:
                break
            
            # Diversity constraints
            doc_count = sum(1 for r in selected if r.doc_id == result.doc_id)
            speaker_count = sum(1 for r in selected if r.speaker == result.speaker)
            
            # Allow up to 2 chunks from same document, 3 from same speaker
            if doc_count >= 2 or speaker_count >= 3:
                continue
            
            selected.append(result)
            used_docs.add(result.doc_id)
            used_speakers.add(result.speaker)
        
        # If we don't have enough, relax constraints
        if len(selected) < top_k:
            remaining_needed = top_k - len(selected)
            remaining_results = [r for r in results if r not in selected]
            
            for result in remaining_results[:remaining_needed]:
                selected.append(result)
        
        logger.info(f"📊 Selected {len(selected)} diverse chunks from {len(set(r.doc_id for r in selected))} documents")
        return selected