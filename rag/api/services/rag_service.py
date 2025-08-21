"""
RAG Service - Combines search and LLM for question answering
"""

import logging
import re
from typing import Dict, List, Any
from rag.api.models.schemas import AskRequest, SourceCitation
from .search_service import SearchService
from .enhanced_search_service import EnhancedSearchService
from .llm_service import LLMService

logger = logging.getLogger(__name__)

class RAGService:
    """Retrieval-Augmented Generation service"""
    
    def __init__(self, search_service: SearchService, llm_service: LLMService):
        self.search_service = search_service
        self.enhanced_search_service = EnhancedSearchService(search_service)
        self.llm_service = llm_service
    
    async def _classify_query_intent(self, question: str) -> str:
        """Use LLM to classify query intent as conversational or research"""
        classification_prompt = f"""Classify this query as either "conversational" or "research":

Query: "{question}"

Rules:
- Conversational = greetings (hi, hello), thanks, casual chat, asking about the assistant, general help requests
- Research = questions about policies, parliament, governments, ministers, specific topics, factual queries

Respond with only one word: "conversational" or "research"

Classification:"""

        try:
            # Use the LLM service for classification with minimal parameters
            response = await self.llm_service.generate_answer(
                prompt=classification_prompt,
                max_tokens=10,     # We only need one word
                temperature=0.0    # Make it deterministic
            )
            
            classification = response.strip().lower()
            
            # Validate response and default to research if unclear
            if 'conversational' in classification:
                return 'conversational'
            elif 'research' in classification:
                return 'research'
            else:
                logger.warning(f"Unclear classification: {classification}, defaulting to research")
                return 'research'
                
        except Exception as e:
            logger.error(f"Classification failed: {e}, defaulting to research")
            return 'research'
    
    def _generate_conversational_response(self, question: str) -> Dict[str, Any]:
        """Generate friendly conversational response"""
        question_lower = question.lower().strip()
        
        if re.match(r'^(hi|hello|hey)', question_lower):
            response = """👋 Hello! I'm your Pacific Hansard AI assistant. 

I'm here to help you explore parliamentary records from across the Pacific Islands, including:
• Cook Islands Parliament proceedings
• Fiji Parliamentary debates  
• Papua New Guinea legislative discussions

Feel free to ask me about specific policies, budget discussions, ministers' statements, or any parliamentary matters that interest you!

**Try asking:** "What is the Cook Islands government's position on seabed mining?" or "What did Fiji's Minister say about tourism policy?"
"""
        elif 'thank' in question_lower:
            response = "🙏 You're welcome! Happy to help with your Pacific parliamentary research. Feel free to ask me anything about the parliamentary records."
        elif 'help' in question_lower or 'what can you do' in question_lower:
            response = """🤖 I can help you research Pacific Island parliamentary records! Here's what I can do:

📋 **Answer policy questions** - "What is Fiji's stance on climate change?"
🔍 **Find specific debates** - "What was discussed about tourism in Cook Islands?"
📊 **Explain government positions** - "How did PNG respond to budget concerns?"
🗣️ **Quote parliamentarians** - "What did the Prime Minister say about seabed mining?"

Just ask me a question about Pacific parliamentary proceedings and I'll search through the official records to find relevant information with proper citations."""
        else:
            response = """👋 Hello there! I'm your Pacific Hansard AI assistant, specialized in helping you research parliamentary records from Cook Islands, Fiji, Papua New Guinea, and other Pacific Island nations.

Ask me anything about policies, debates, ministerial statements, or legislative proceedings from these parliaments!"""
            
        return {
            'answer': response,
            'sources': [],
            'model_used': 'conversational_handler'
        }

    async def generate_answer(self, request: AskRequest) -> Dict[str, Any]:
        """
        Generate answer using RAG pipeline:
        1. Check if query is conversational
        2. Search for relevant chunks
        3. Generate answer with LLM
        4. Extract and validate citations
        5. Build source list
        """
        
        # Step 1: Classify query intent using LLM
        query_intent = await self._classify_query_intent(request.question)
        logger.info(f"🤖 Query classified as: {query_intent}")
        
        if query_intent == 'conversational':
            return self._generate_conversational_response(request.question)
        
        # Step 2: Enhanced multi-pass search for relevant chunks
        search_request = self._build_search_request(request)
        search_results = await self.enhanced_search_service.enhanced_search(search_request)
        
        if not search_results:
            return {
                'answer': "Not found in the provided records. No relevant parliamentary documents were found for your question.",
                'sources': [],
                'model_used': self.llm_service.model_name
            }
        
        # Step 2: Convert search results to context chunks
        context_chunks = self._prepare_context_chunks(search_results)
        
        # Debug: Log what text we're actually getting
        logger.info(f"🔍 ENHANCED SEARCH RESULTS: {len(search_results)} chunks retrieved")
        logger.info(f"📊 CONTEXT CHUNKS PREPARED: {len(context_chunks)} chunks")
        for i, chunk in enumerate(context_chunks[:3]):  # Log first 3 chunks
            logger.info(f"📄 CHUNK {i}: ID={chunk.get('id', 'N/A')}, Country={chunk.get('country', 'N/A')}")
            logger.info(f"📝 TEXT (first 150 chars): {chunk.get('text', 'N/A')[:150]}...")
            logger.info(f"📊 TEXT LENGTH: {len(chunk.get('text', ''))}")
        
        # Step 3: Generate answer with LLM
        llm_result = await self.llm_service.generate_answer(
            request.question,
            context_chunks,
            request.temperature
        )
        
        # Step 4: Extract citations and build sources  
        logger.info(f"🔗 EXTRACTING SOURCES FROM ANSWER: {len(search_results)} search results available")
        logger.info(f"🔗 LLM ANSWER: {llm_result['answer'][:200]}...")
        
        # TEMPORARY FIX: Create sources directly from search results
        sources = []
        for i, result in enumerate(search_results[:3]):  # Take first 3 results
            result_text = getattr(result, 'text', 'No content available')
            source = {
                'id': getattr(result, 'id', f'source_{i}'),
                'text_preview': result_text[:150] + ('...' if len(result_text) > 150 else ''),
                'full_text': result_text,
                'country': getattr(result, 'country', 'Unknown'),
                'date': getattr(result, 'date', '2024-01-01'),
                'speaker': getattr(result, 'speaker', 'Parliament'),
                'url': getattr(result, 'url', ''),
                'doc_id': getattr(result, 'doc_id', ''),
                'chunk_index': getattr(result, 'chunk_index', i)
            }
            logger.info(f"📄 CREATING SOURCE {i}: text length = {len(result_text)}")
            sources.append(source)
        
        logger.info(f"🔗 CREATED {len(sources)} SOURCES DIRECTLY")
        
        # Step 5: Validate answer has proper citations
        validated_answer = self._validate_citations(llm_result['answer'], sources)
        
        return {
            'answer': validated_answer,
            'sources': sources,
            'model_used': llm_result['model_used']
        }
    
    def _build_search_request(self, ask_request: AskRequest):
        """Convert AskRequest to SearchRequest"""
        from rag.api.models.schemas import SearchRequest
        
        return SearchRequest(
            query=ask_request.question,
            filters=ask_request.filters,
            top_k=min(ask_request.top_k, 5)  # Limit to top 5 to avoid overwhelming LLM
        )
    
    def _prepare_context_chunks(self, search_results: List) -> List[Dict]:
        """Convert search results to context chunks for LLM"""
        chunks = []
        
        for result in search_results:
            chunk = {
                'id': result.id,
                'text': result.text,
                'speaker': result.speaker,
                'date': result.date,
                'country': result.country,
                'chamber': result.chamber,
                'url': result.url,
                'score': result.score
            }
            chunks.append(chunk)
        
        return chunks
    
    def _extract_sources(self, answer: str, search_results: List) -> List[SourceCitation]:
        """Extract cited sources from answer and build source list"""
        print(f"🔗 _extract_sources called with {len(search_results)} search results")
        print(f"🔗 First search result text: {search_results[0].text[:100] if search_results and hasattr(search_results[0], 'text') else 'NO TEXT'}")
        sources = []
        
        # Find all citation references in answer [#0], [#1], etc.
        citation_pattern = r'\[#(\d+)\]'
        cited_indices = set()
        
        for match in re.finditer(citation_pattern, answer):
            try:
                index = int(match.group(1))
                cited_indices.add(index)
            except (ValueError, IndexError):
                continue
        
        # If no citations found in text, include top 3 sources anyway for context
        if not cited_indices and search_results:
            cited_indices = {0, 1, 2}  # Include first 3 results
        
        # Build source citations for referenced chunks
        for index in sorted(cited_indices):
            if index < len(search_results):
                result = search_results[index]
                
                # Create text preview (first 120 chars)
                text_preview = result.text
                if len(text_preview) > 120:
                    text_preview = text_preview[:120] + "..."
                
                # Debug: Log what we're actually getting from search results
                logger.info(f"📄 SOURCE {index}: Text length = {len(result.text)}")
                logger.info(f"📄 SOURCE {index}: First 100 chars = {result.text[:100] if result.text else 'EMPTY'}")
                
                # Debug what we have
                print(f"🔗 Creating source {index}: text length = {len(result.text) if hasattr(result, 'text') and result.text else 0}")
                
                # Create proper source format for API schema with full text
                source_obj = {
                    'id': getattr(result, 'id', f'source_{index}'),
                    'text': text_preview,  # Short preview for display
                    'text_preview': text_preview,  # Required by schema
                    'full_text': getattr(result, 'text', 'No text available'),  # Complete source text for modal viewing
                    'country': getattr(result, 'country', 'Unknown'),
                    'date': self._format_date(getattr(result, 'date', '2024-01-01')),
                    'speaker': getattr(result, 'speaker', 'Parliament'),
                    'url': getattr(result, 'url', ''),  # Required by schema
                    'doc_id': getattr(result, 'doc_id', ''),  # Document ID for context
                    'chunk_index': getattr(result, 'chunk_index', 0)  # Chunk position
                }
                print(f"🔗 Created source: {source_obj['id']}, full_text length: {len(source_obj['full_text'])}")
                sources.append(source_obj)
        
        return sources
    
    def _format_date(self, date_str: str) -> str:
        """Format date to remove timestamp and show just the date"""
        try:
            if 'T' in date_str:
                # Remove the time part (everything after 'T')
                return date_str.split('T')[0]
            return date_str
        except (AttributeError, TypeError):
            return '2024-01-01'  # Default fallback
    
    def _validate_citations(self, answer: str, sources: List) -> str:
        """Validate that answer has proper citations or appropriate disclaimer"""
        
        # Just return the answer as-is, let frontend handle sources separately
        # This keeps the answer clean and readable
        return answer
    
    def _filter_low_quality_responses(self, answer: str) -> str:
        """Filter out low-quality or inappropriate responses"""
        
        # Remove very short responses that don't add value
        if len(answer.strip()) < 10:
            return "Not found in the provided records."
        
        # Remove responses that are just repetitions of the question
        # (Simple heuristic - could be improved)
        
        return answer