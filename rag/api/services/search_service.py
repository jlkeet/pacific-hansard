"""
Search Service for Solr integration and hybrid search
"""

import pysolr
import logging
import json
import numpy as np
from typing import List, Dict, Optional, Any
from rag.api.models.schemas import SearchRequest, SearchResult
from rag.embedding_service import get_embedding_service
from rag.reranker_service import get_reranker_service

logger = logging.getLogger(__name__)

class SearchService:
    """Service for search operations using Solr"""
    
    def __init__(self, solr_url: str = "http://localhost:8983/solr/hansard_core", 
                 enable_reranker: bool = True):
        self.solr_url = solr_url
        self.solr = pysolr.Solr(solr_url, always_commit=True)
        self.embedding_service = None
        self.reranker = get_reranker_service(enabled=enable_reranker)
        
    async def health_check(self) -> bool:
        """Check if Solr is running and responsive"""
        try:
            # Test Solr connection with a simple ping
            results = self.solr.search('*:*', rows=1)
            logger.info(f"✅ Solr healthy, {len(results)} total documents indexed")
            return True
        except Exception as e:
            logger.error(f"❌ Solr health check failed: {e}")
            return False
    
    def _get_embedding_service(self):
        """Get embedding service instance."""
        if self.embedding_service is None:
            self.embedding_service = get_embedding_service()
        return self.embedding_service
    
    async def bm25_search(self, request: SearchRequest) -> List[SearchResult]:
        """Perform BM25 text search."""
        try:
            # Build Solr query
            query = self._build_solr_query(request)
            
            # Execute search
            results = self.solr.search(
                query,
                rows=request.top_k * 2,  # Get more results for fusion
                fl='*,score',
                sort='score desc'
            )
            
            return self._parse_search_results(results, 'bm25')
            
        except Exception as e:
            logger.error(f"BM25 search failed: {e}")
            return []
    
    async def vector_search(self, request: SearchRequest) -> List[SearchResult]:
        """Perform vector similarity search."""
        try:
            # Get query embedding
            embedding_service = self._get_embedding_service()
            query_embedding = embedding_service.encode_query(request.query)
            query_vector = query_embedding.tolist()
            
            # Build kNN query
            knn_query = f"{{!knn f=content_vector topK={request.top_k * 2}}}{query_vector}"
            
            # Execute vector search
            results = self.solr.search(
                knn_query,
                rows=request.top_k * 2,
                fl='*,score'
            )
            
            return self._parse_search_results(results, 'vector')
            
        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            return []
    
    def reciprocal_rank_fusion(self, bm25_results: List[SearchResult], 
                              vector_results: List[SearchResult], 
                              k: int = 60) -> List[SearchResult]:
        """
        Combine results from BM25 and vector search using Reciprocal Rank Fusion.
        
        Args:
            bm25_results: Results from BM25 search
            vector_results: Results from vector search  
            k: RRF constant (default 60)
            
        Returns:
            Fused and re-ranked results
        """
        # Create maps for results
        bm25_map = {result.id: (i + 1, result) for i, result in enumerate(bm25_results)}
        vector_map = {result.id: (i + 1, result) for i, result in enumerate(vector_results)}
        
        # Get all unique document IDs
        all_ids = set(bm25_map.keys()) | set(vector_map.keys())
        
        # Calculate RRF scores
        rrf_scores = {}
        for doc_id in all_ids:
            rrf_score = 0.0
            
            # Add BM25 contribution
            if doc_id in bm25_map:
                rank, result = bm25_map[doc_id]
                rrf_score += 1.0 / (k + rank)
            
            # Add vector contribution  
            if doc_id in vector_map:
                rank, result = vector_map[doc_id]
                rrf_score += 1.0 / (k + rank)
            
            rrf_scores[doc_id] = rrf_score
        
        # Sort by RRF score and create final results
        sorted_ids = sorted(rrf_scores.keys(), key=lambda x: rrf_scores[x], reverse=True)
        
        final_results = []
        for doc_id in sorted_ids:
            # Get result object (prefer BM25, fallback to vector)
            if doc_id in bm25_map:
                _, result = bm25_map[doc_id]
            else:
                _, result = vector_map[doc_id]
            
            # Update score to RRF score
            result.score = rrf_scores[doc_id]
            final_results.append(result)
        
        logger.info(f"RRF fusion: {len(bm25_results)} BM25 + {len(vector_results)} vector = {len(final_results)} fused")
        return final_results
    
    async def hybrid_search(self, request: SearchRequest) -> List[SearchResult]:
        """
        Perform hybrid search combining BM25 and semantic vector search with RRF.
        """
        try:
            # Perform both searches concurrently
            logger.info(f"Starting hybrid search for: '{request.query}'")
            
            # BM25 search
            bm25_results = await self.bm25_search(request)
            logger.info(f"BM25 found {len(bm25_results)} results")
            
            # Vector search
            vector_results = await self.vector_search(request) 
            logger.info(f"Vector search found {len(vector_results)} results")
            
            # Combine with RRF
            if not bm25_results and not vector_results:
                return []
            elif not bm25_results:
                return vector_results[:request.top_k]
            elif not vector_results:
                return bm25_results[:request.top_k]
            else:
                fused_results = self.reciprocal_rank_fusion(bm25_results, vector_results)
                
                # Apply re-ranking if enabled
                final_results = self.reranker.rerank(request.query, fused_results)
                return final_results[:request.top_k]
            
        except Exception as e:
            logger.error(f"Hybrid search failed: {e}")
            return []
    
    def _parse_search_results(self, results, search_type: str = 'hybrid') -> List[SearchResult]:
        """Parse Solr results into SearchResult objects."""
        search_results = []
        
        for i, doc in enumerate(results):
            try:
                # Helper function to extract value from Solr field (which can be a list)
                def get_field_value(field_name, default=''):
                    value = doc.get(field_name, default)
                    return value[0] if isinstance(value, list) and len(value) > 0 else value
                
                # Extract values safely
                chunk_idx = get_field_value('chunk_index', i)
                if chunk_idx is None:
                    chunk_idx = i
                
                # Extract text content
                extracted_text = get_field_value('content', get_field_value('text', ''))
                
                # Debug: Log the extracted text for the first few results
                if i < 2:
                    logger.info(f"🔍 SEARCH RESULT {i}: ID={get_field_value('id', f'unknown_{i}')}")
                    logger.info(f"📝 EXTRACTED TEXT (first 200 chars): {extracted_text[:200]}...")
                    logger.info(f"📊 TEXT LENGTH: {len(extracted_text)}")
                
                result = SearchResult(
                    id=get_field_value('id', f'unknown_{i}'),
                    doc_id=str(get_field_value('document_id', get_field_value('id', ''))),
                    text=extracted_text,
                    speaker=get_field_value('speakers', get_field_value('speaker', 'Unknown')),
                    date=str(get_field_value('date', '')),
                    country=get_field_value('source', get_field_value('country', 'Unknown')),
                    chamber=get_field_value('chamber', 'Parliament'),
                    url=get_field_value('url', ''),
                    score=float(doc.get('score', 0.0)),
                    chunk_index=int(chunk_idx)
                )
                search_results.append(result)
                
            except Exception as e:
                logger.error(f"Failed to parse {search_type} search result {i}: {e}")
                continue
        
        return search_results
    
    def _build_solr_query(self, request: SearchRequest) -> str:
        """Build Solr query string with filters"""
        
        # Base query - search in content field (both exact phrase and individual words)
        base_query = f'content:("{request.query}") OR content:({request.query})'
        
        # Add filters
        filters = []
        
        if request.filters.get('country'):
            filters.append(f'source:"{request.filters["country"]}"')
        
        if request.filters.get('speaker'):
            filters.append(f'speaker:"{request.filters["speaker"]}"')
            
        if request.filters.get('chamber'):
            filters.append(f'chamber:"{request.filters["chamber"]}"')
        
        # Date range filters
        if request.filters.get('date_from') or request.filters.get('date_to'):
            date_from = request.filters.get('date_from', '*')
            date_to = request.filters.get('date_to', '*')
            filters.append(f'date:[{date_from} TO {date_to}]')
        
        # Combine query and filters
        if filters:
            filter_string = ' AND '.join(filters)
            full_query = f'({base_query}) AND ({filter_string})'
        else:
            full_query = base_query
            
        logger.debug(f"Solr query: {full_query}")
        return full_query
    
    async def get_document_by_id(self, doc_id: str) -> Optional[Dict]:
        """Get a specific document by ID"""
        try:
            results = self.solr.search(f'id:"{doc_id}"', rows=1)
            return results.docs[0] if results.docs else None
        except Exception as e:
            logger.error(f"Failed to get document {doc_id}: {e}")
            return None
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get search index statistics"""
        try:
            # Get total document count
            results = self.solr.search('*:*', rows=0)
            total_docs = results.hits
            
            # Simple country counts by doing separate searches
            countries = {}
            try:
                cook_islands = self.solr.search('source:"Cook Islands"', rows=0)
                fiji = self.solr.search('source:"Fiji"', rows=0)
                png = self.solr.search('source:"Papua New Guinea"', rows=0)
                
                countries = {
                    "Cook Islands": cook_islands.hits,
                    "Fiji": fiji.hits,
                    "Papua New Guinea": png.hits
                }
            except Exception as country_error:
                logger.warning(f"Could not get country counts: {country_error}")
                countries = {"Cook Islands": 0, "Fiji": 0, "Papua New Guinea": 0}
            
            return {
                'total_documents': total_docs,
                'countries': countries,
                'index_status': 'healthy'
            }
            
        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return {
                'total_documents': 0,
                'countries': {},
                'index_status': 'error'
            }
    
    async def get_full_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the complete document content for a given document ID.
        This attempts to retrieve all chunks for the document and reconstruct the full text.
        """
        try:
            logger.info(f"📄 Searching for full document: {doc_id}")
            
            # First, try to get chunks that match this doc_id
            results = self.solr.search(f'document_id:"{doc_id}"', rows=100, sort='chunk_index asc')
            
            if not results.docs:
                logger.warning(f"❌ No chunks found for doc_id: {doc_id}")
                return None
            
            logger.info(f"✅ Found {len(results.docs)} chunks for doc_id: {doc_id}")
            
            # Sort chunks by chunk_index to maintain order
            chunks = sorted(results.docs, key=lambda x: x.get('chunk_index', 0))
            
            # Reconstruct the full document from chunks
            full_text_parts = []
            metadata = None
            
            for chunk in chunks:
                # Get metadata from the first chunk (handling list fields)
                if metadata is None:
                    def get_field_value(field_name, default=''):
                        value = chunk.get(field_name, default)
                        return value[0] if isinstance(value, list) and len(value) > 0 else value
                    
                    metadata = {
                        'doc_id': get_field_value('document_id', doc_id),
                        'country': get_field_value('source', 'Unknown'),
                        'date': get_field_value('date', ''),
                        'speaker': get_field_value('speakers', ''),
                        'url': get_field_value('url', ''),
                        'title': get_field_value('title', ''),
                        'source': get_field_value('source', '')
                    }
                
                # Add chunk text to full document
                chunk_text = get_field_value('content', '')
                if chunk_text:
                    full_text_parts.append(chunk_text)
            
            # Combine all chunks into full document
            raw_content = '\n\n'.join(full_text_parts)
            
            # Format the content for better readability
            formatted_content = self._format_document_content(raw_content, metadata)
            
            result = {
                'doc_id': doc_id,
                'content': raw_content,  # Keep original for compatibility
                'formatted_content': formatted_content,  # New formatted version
                'text': formatted_content,  # Use formatted as default text
                'metadata': metadata,
                'chunk_count': len(chunks),
                'total_length': len(raw_content)
            }
            
            logger.info(f"📄 Reconstructed document: {len(raw_content)} characters from {len(chunks)} chunks")
            return result
            
        except Exception as e:
            logger.error(f"❌ Error retrieving full document {doc_id}: {e}")
            return None

    def _format_document_content(self, raw_content: str, metadata: Dict) -> str:
        """
        Format document content for better readability with proper paragraphs,
        speaker formatting, and structure.
        """
        try:
            # Start with document header
            header_parts = []
            if metadata.get('title'):
                header_parts.append(f"# {metadata['title']}")
            
            if metadata.get('country'):
                header_parts.append(f"**Country:** {metadata['country']}")
            
            if metadata.get('date'):
                date_str = metadata['date']
                if 'T' in date_str:
                    date_str = date_str.split('T')[0]  # Remove time part
                header_parts.append(f"**Date:** {date_str}")
            
            if metadata.get('speaker') and metadata['speaker'] != 'Parliament':
                header_parts.append(f"**Speaker:** {metadata['speaker']}")
            
            header = '\n'.join(header_parts) + '\n\n---\n\n' if header_parts else ''
            
            # Clean and format the content
            content = raw_content
            
            # Create a more readable version with proper paragraphs and speaker formatting
            import re
            
            # Clean up excessive whitespace
            content = re.sub(r'\s+', ' ', content)
            
            # Split content into chunks and format
            formatted_sections = []
            
            # Look for speaker patterns and format them - simplified approach
            # Match any "HON." or "MR." followed by text and ending with ".-"
            speaker_pattern = r'((?:HON\.|MR\.|MS\.|DR\.|PROF\.)[^.]*?\.[-–]\s*)'
            
            # Split by speakers but keep the delimiter
            parts = re.split(f'({speaker_pattern})', content)
            
            current_section = ""
            for part in parts:
                part = part.strip()
                if not part:
                    continue
                
                # Check if this is a speaker header
                if re.match(speaker_pattern, part):
                    # Save previous section if exists
                    if current_section:
                        # Break into readable paragraphs
                        paragraphs = self._create_paragraphs(current_section)
                        formatted_sections.extend(paragraphs)
                        current_section = ""
                    
                    # Format speaker header - always starts a new paragraph
                    formatted_speaker = f"**{part}**"
                    formatted_sections.append(formatted_speaker.strip())
                else:
                    # Accumulate content for this speaker
                    current_section += part + " "
            
            # Handle final section
            if current_section:
                paragraphs = self._create_paragraphs(current_section)
                formatted_sections.extend(paragraphs)
            
            # Join all sections
            formatted_body = '\n\n'.join(formatted_sections)
            
            # Clean up excessive spacing and formatting issues
            formatted_body = formatted_body.replace('\n\n\n', '\n\n')
            formatted_body = formatted_body.replace('  ', ' ')
            
            # Combine header and body
            final_content = header + formatted_body
            
            return final_content
            
        except Exception as e:
            logger.warning(f"Failed to format document content: {e}")
            # Return original content if formatting fails
            return raw_content
    
    def _create_paragraphs(self, text: str) -> List[str]:
        """
        Break text into readable paragraphs based on sentence structure and length.
        Since each speaker now gets their own section, we can make longer paragraphs.
        """
        # For speaker sections, we want fewer but more substantial paragraph breaks
        text = text.strip()
        if not text:
            return []
        
        # Split into sentences
        sentences = text.split('.')
        paragraphs = []
        current_para = []
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            
            # Add the sentence back with its period
            sentence = sentence + '.'
            current_para.append(sentence)
            
            # Break paragraph only for major breaks or very long content
            para_text = ' '.join(current_para)
            if (len(para_text) > 600 or  # Longer paragraphs now that speakers are separate
                'Thank you, Mr. Speaker' in sentence or
                'I thank you' in sentence or
                sentence.endswith('Thank you, Sir.') or
                sentence.endswith('I conclude.')):
                
                if para_text.strip():
                    paragraphs.append(para_text.strip())
                current_para = []
        
        # Add remaining content
        if current_para:
            para_text = ' '.join(current_para).strip()
            if para_text:
                paragraphs.append(para_text)
        
        # If we got no paragraphs but have text, return the original text as one paragraph
        if not paragraphs and text:
            paragraphs.append(text)
        
        return paragraphs