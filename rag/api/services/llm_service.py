"""
LLM Service for Ollama integration
"""

import httpx
import json
import logging
import re
from typing import Dict, List, Optional, Any
from datetime import datetime

logger = logging.getLogger(__name__)

class LLMService:
    """Service for LLM operations using Ollama"""
    
    def __init__(self, ollama_url: str = "http://localhost:11434"):
        self.ollama_url = ollama_url
        self.model_name = "qwen2.5:7b"  # Switched to Qwen2.5 7B - better for RAG tasks
        self.client = httpx.AsyncClient(timeout=60.0)   # Reduced timeout for faster model
    
    async def health_check(self) -> bool:
        """Check if Ollama is running and model is available"""
        try:
            response = await self.client.get(f"{self.ollama_url}/api/tags")
            if response.status_code == 200:
                models = response.json()
                available_models = [m['name'] for m in models.get('models', [])]
                
                # Check if our model is available
                model_available = any(self.model_name in model for model in available_models)
                
                if model_available:
                    logger.info(f"✅ Ollama healthy, {self.model_name} available")
                    return True
                else:
                    logger.warning(f"⚠️ Ollama healthy but {self.model_name} not found. Available: {available_models}")
                    return False
            else:
                logger.error(f"❌ Ollama unhealthy: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Cannot connect to Ollama: {e}")
            return False
    
    async def list_models(self) -> List[str]:
        """List available models in Ollama"""
        try:
            response = await self.client.get(f"{self.ollama_url}/api/tags")
            if response.status_code == 200:
                models = response.json()
                return [m['name'] for m in models.get('models', [])]
            else:
                return []
        except Exception as e:
            logger.error(f"Failed to list models: {e}")
            return []
    
    async def generate_answer(
        self,
        question: str,
        context_chunks: List[Dict],
        temperature: float = 0.1
    ) -> Dict[str, Any]:
        """
        Generate answer using Ollama with Hansard context chunks.
        
        Args:
            question: User's natural language question
            context_chunks: List of relevant Hansard chunks
            temperature: LLM temperature (0.1 for factual responses)
            
        Returns:
            Dict with 'answer', 'model_used', 'generation_time'
        """
        try:
            # Build context from chunks
            context = self._build_context(context_chunks)
            
            # Create prompt with strict citation requirements
            prompt = self._build_prompt(question, context)
            
            # Debug: Log the full prompt being sent
            logger.info(f"📝 FULL PROMPT LENGTH: {len(prompt)} characters")
            logger.info(f"📝 PROMPT BEING SENT TO LLM:\n{prompt}")
            
            # Generate response
            start_time = datetime.now()
            
            response = await self.client.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.model_name,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": temperature,
                        "top_p": 0.9,
                        "repeat_penalty": 1.1,
                        "stop": ["</answer>"]  # Stop at our answer tag
                    }
                }
            )
            
            generation_time = (datetime.now() - start_time).total_seconds()
            
            if response.status_code == 200:
                result = response.json()
                raw_answer = result.get('response', '')
                
                # Post-process the answer
                processed_answer = self._post_process_answer(raw_answer)
                
                return {
                    'answer': processed_answer,
                    'model_used': self.model_name,
                    'generation_time': generation_time,
                    'raw_response': raw_answer  # For debugging
                }
            else:
                logger.error(f"Ollama generation failed: {response.status_code}")
                return {
                    'answer': "Sorry, I encountered an error generating the response.",
                    'model_used': self.model_name,
                    'generation_time': generation_time
                }
                
        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            
            # Provide helpful error message for timeout issues
            error_msg = "Sorry, I encountered an error processing your question."
            if "timeout" in str(e).lower():
                error_msg = "The AI model is responding slowly. Please try a simpler question or try again later."
            
            return {
                'answer': error_msg,
                'model_used': self.model_name,
                'generation_time': 0
            }
    
    def _build_context(self, chunks: List[Dict]) -> str:
        """Build context string from Hansard chunks"""
        context_parts = []
        
        for i, chunk in enumerate(chunks):
            context_part = f"[#{i}] Speaker: {chunk.get('speaker', 'Unknown')} | " \
                          f"Date: {chunk.get('date', 'Unknown')} | " \
                          f"Country: {chunk.get('country', 'Unknown')}\n" \
                          f"{chunk.get('text', '')}"
            context_parts.append(context_part)
        
        return "\n\n".join(context_parts)
    
    def _build_prompt(self, question: str, context: str) -> str:
        """Build enhanced structured prompt for parliamentary analysis"""
        
        prompt = f"""You are an expert parliamentary research assistant specializing in Pacific Island democracies. Your expertise includes parliamentary procedures, policy analysis, government positions, and political context across Cook Islands, Fiji, and other Pacific nations.

RESEARCH QUESTION: {question}

RELEVANCE CHECK: Before providing analysis, determine if the Parliamentary Sources below contain information relevant to the research question. If the sources do NOT address the question topic, respond with:

"❌ **No Relevant Information Found**

The parliamentary records searched do not contain specific information about [topic from question]. The available sources discuss [brief 1-sentence summary of what sources actually contain], but do not address the question asked.

Please try rephrasing your question or asking about topics that are covered in the Pacific parliamentary records."

Only proceed with full analysis if the sources ARE relevant to the question.

PARLIAMENTARY SOURCES:
{context}

ANALYSIS METHODOLOGY:
1. EXTRACT KEY FACTS: Identify concrete facts, dates, votes, and official positions
2. ANALYZE PERSPECTIVES: Note government vs. opposition viewpoints, debates, disagreements  
3. TRACK CHRONOLOGY: Understand policy evolution and timeline of events
4. CONTEXTUALIZE: Place statements within broader parliamentary and political context
5. VERIFY ATTRIBUTION: Ensure accuracy of who said what and when

RESPONSE FORMAT:
📋 Executive Summary
[1-2 sentences answering the core question directly]

🔍 Key Findings
• [Main fact with citations [#X]]
• [Another key fact with citations [#X]]
• [Additional finding with citations [#X]]

📊 Detailed Analysis  
[In-depth discussion with evidence and context]

🗣️ Perspectives & Debate
• Government position: [details with citations]
• Opposition response: [details with citations]
• Other viewpoints: [details with citations]

📈 Status & Implications
▸ Current status: [what's happening now]
▸ Next steps: [what comes next]
▸ Significance: [why this matters]

PARLIAMENTARY EXPERTISE GUIDELINES:
• Distinguish between government statements, opposition responses, and neutral parliamentary processes
• Recognize parliamentary language (motions, readings, committees, standing orders)
• Understand Pacific Island political context and regional considerations
• Identify policy changes, legislative progress, and procedural matters
• Note voting patterns, party positions, and bipartisan agreements where relevant

CITATION REQUIREMENTS:
• Use [#0], [#1], [#2] etc. immediately after each specific claim
• Cite direct quotes with speaker attribution
• Reference specific parliamentary sessions and dates where mentioned
• Distinguish between direct quotes and paraphrased content

RESPONSE PRINCIPLES:
• Lead with actionable information for researchers and policymakers
• Be precise and concise while maintaining completeness
• Acknowledge limitations, gaps, or conflicting information
• Use clear headings and structure for easy scanning
• Focus on what parliamentarians actually said and decided

COMPREHENSIVE PARLIAMENTARY ANALYSIS:"""
        return prompt
    
    def _post_process_answer(self, raw_answer: str) -> str:
        """Post-process the generated answer"""
        
        # Remove Chinese characters (just in case)
        answer = re.sub(r'[\u4e00-\u9fff]+', '', raw_answer)
        
        # Remove any thinking tags or reasoning sections that might appear
        answer = re.sub(r'<think>.*?</think>', '', answer, flags=re.DOTALL)
        answer = re.sub(r'<thinking>.*?</thinking>', '', answer, flags=re.DOTALL)
        
        # Clean up whitespace
        answer = re.sub(r'\n\s*\n', '\n\n', answer)
        answer = answer.strip()
        
        # Validate that the response seems to use provided context
        # Check for common signs the LLM ignored context and hallucinated
        suspicious_patterns = [
            r'education.*grant',  # Common hallucination topic
            r'fiji.*education',   # Previous wrong response
            r'boarding.*grant',   # Previous wrong response
            r'VAT.*increase'      # Previous wrong response
        ]
        
        is_suspicious = any(re.search(pattern, answer.lower()) for pattern in suspicious_patterns)
        
        if is_suspicious and '[#' not in answer:
            logger.warning("LLM response appears to ignore provided context")
            return "No relevant information found in the provided parliamentary records."
        
        # Ensure we have citations - but be more lenient about requiring "not found"
        if '[#' not in answer and len(answer.strip()) > 50:
            # If it's a substantial answer without citations, add a note
            answer += "\n\n[Note: Please refer to the source excerpts for verification]"
        
        return answer
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()