#!/usr/bin/env python3
"""
FastAPI Backend for Hansard RAG System

Provides REST API endpoints for:
- /search - Hybrid search (BM25 + embeddings) 
- /ask - Natural language Q&A with citations
- /health - Service health check
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
import time
import logging
import os
from datetime import datetime
import asyncio
import httpx

# Import our custom modules
from rag.api.services.search_service import SearchService
from rag.api.services.llm_service import LLMService
from rag.api.services.rag_service import RAGService
from rag.api.models.schemas import SearchRequest, SearchResponse, AskRequest, AskResponse, HealthResponse

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Hansard RAG API",
    description="Retrieval-Augmented Generation API for Pacific Parliamentary Records",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS for web frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for hybrid deployment
    allow_credentials=False,  # Set to False for ngrok deployment
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# Global service instances
search_service: Optional[SearchService] = None
llm_service: Optional[LLMService] = None
rag_service: Optional[RAGService] = None

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    global search_service, llm_service, rag_service
    
    logger.info("🚀 Starting Hansard RAG API...")
    
    try:
        # Initialize services
        search_service = SearchService()
        llm_service = LLMService()
        rag_service = RAGService(search_service, llm_service)
        
        # Test connections
        await search_service.health_check()
        await llm_service.health_check()
        
        logger.info("✅ All services initialized successfully")
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize services: {e}")
        raise

@app.on_event("shutdown") 
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("🛑 Shutting down Hansard RAG API...")

@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "service": "Hansard RAG API",
        "version": "0.1.0",
        "status": "running",
        "docs": "/docs",
        "endpoints": {
            "search": "/search",
            "ask": "/ask", 
            "health": "/health"
        }
    }

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    try:
        # Check all service health
        solr_healthy = await search_service.health_check() if search_service else False
        llm_healthy = await llm_service.health_check() if llm_service else False
        
        overall_healthy = solr_healthy and llm_healthy
        
        return HealthResponse(
            status="healthy" if overall_healthy else "unhealthy",
            timestamp=datetime.utcnow(),
            services={
                "solr": "healthy" if solr_healthy else "unhealthy",
                "ollama": "healthy" if llm_healthy else "unhealthy",
                "api": "healthy"
            },
            version="0.1.0"
        )
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Service unavailable")

@app.get("/search", response_model=SearchResponse)
async def search_documents_get(
    q: str = Query(..., description="Search query"),
    country: Optional[str] = Query(None, description="Filter by country"),
    speaker: Optional[str] = Query(None, description="Filter by speaker"),
    date_from: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    chamber: Optional[str] = Query(None, description="Parliament chamber"),
    top_k: int = Query(12, description="Number of results to return")
):
    """
    Search documents using hybrid search (BM25 + semantic embeddings).
    Returns ranked documents without LLM generation.
    """
    try:
        start_time = time.time()
        
        # Build search request
        search_req = SearchRequest(
            query=q,
            filters={
                "country": country,
                "speaker": speaker, 
                "date_from": date_from,
                "date_to": date_to,
                "chamber": chamber
            },
            top_k=top_k
        )
        
        # Perform search
        results = await search_service.hybrid_search(search_req)
        
        response_time = time.time() - start_time
        
        return SearchResponse(
            query=q,
            results=results,
            total_found=len(results),
            response_time_ms=round(response_time * 1000, 2),
            search_type="hybrid"
        )
        
    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

@app.post("/search")
async def search_documents_post(request: SearchRequest):
    """
    Search documents using hybrid search (BM25 + semantic embeddings) via POST.
    Returns ranked documents without LLM generation.
    """
    try:
        start_time = time.time()
        
        # Perform search
        results = await search_service.hybrid_search(request)
        
        response_time = time.time() - start_time
        
        return {
            "query": request.query,
            "results": [result.dict() for result in results],
            "total_found": len(results),
            "response_time_ms": round(response_time * 1000, 2),
            "search_type": "hybrid"
        }
        
    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

@app.post("/ask", response_model=AskResponse)
async def ask_question(request: AskRequest):
    """
    Answer questions using RAG pipeline:
    1. Hybrid search for relevant chunks
    2. LLM generation with citations
    3. Post-processing for citation validation
    """
    try:
        start_time = time.time()
        
        # Generate answer using RAG pipeline
        answer_data = await rag_service.generate_answer(request)
        
        response_time = time.time() - start_time
        
        return AskResponse(
            question=request.question,
            answer=answer_data["answer"],
            sources=answer_data["sources"],
            response_time_ms=round(response_time * 1000, 2),
            model_used=answer_data["model_used"],
            chunks_used=len(answer_data["sources"])
        )
        
    except Exception as e:
        logger.error(f"Question answering failed: {e}")
        raise HTTPException(status_code=500, detail=f"Question answering failed: {str(e)}")

@app.get("/models", response_model=Dict[str, Any])
async def list_available_models():
    """List available LLM models"""
    try:
        models = await llm_service.list_models()
        return {"models": models}
    except Exception as e:
        logger.error(f"Failed to list models: {e}")
        raise HTTPException(status_code=500, detail="Failed to list models")

@app.get("/stats", response_model=Dict[str, Any])
async def get_api_stats():
    """Get search index statistics"""
    try:
        if search_service:
            stats = await search_service.get_stats()
            return stats
        else:
            return {
                "total_documents": 0,
                "countries": {},
                "index_status": "not_initialized"
            }
    except Exception as e:
        logger.error(f"Failed to get stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to get statistics")

@app.get("/test-sources")
async def test_sources():
    """Test endpoint to check what sources look like"""
    try:
        from rag.api.models.schemas import SearchRequest
        
        # Do a simple search
        search_request = SearchRequest(query="seabed mining", top_k=2)
        search_results = await search_service.hybrid_search(search_request)
        
        # Extract sources manually
        sources = []
        for i, result in enumerate(search_results[:2]):
            source = {
                'id': getattr(result, 'id', f'test_{i}'),
                'text': getattr(result, 'text', 'No text')[:100],
                'full_text': getattr(result, 'text', 'No full text available'),
                'country': getattr(result, 'country', 'Unknown'),
                'date': getattr(result, 'date', '2024-01-01'),
                'speaker': getattr(result, 'speaker', 'Parliament'),
                'text_length': len(getattr(result, 'text', ''))
            }
            sources.append(source)
        
        return {
            "search_results_count": len(search_results),
            "sources": sources
        }
    except Exception as e:
        return {"error": str(e)}

@app.get("/document/{doc_id}")
async def get_full_document(doc_id: str):
    """
    Get the full document content by document ID.
    This endpoint attempts to retrieve the complete source document.
    """
    try:
        logger.info(f"📄 Fetching full document for doc_id: {doc_id}")
        
        if not search_service:
            raise HTTPException(status_code=503, detail="Search service not available")
        
        # Try to get the full document from the search service
        full_doc = await search_service.get_full_document(doc_id)
        
        if not full_doc:
            logger.warning(f"❌ Document not found: {doc_id}")
            raise HTTPException(status_code=404, detail="Document not found")
        
        logger.info(f"✅ Retrieved full document: {len(full_doc.get('content', ''))} characters")
        return full_doc
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error fetching document {doc_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching document: {str(e)}")

# Error handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Custom HTTP exception handler"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code,
            "timestamp": datetime.utcnow().isoformat()
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """General exception handler"""
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "status_code": 500,
            "timestamp": datetime.utcnow().isoformat()
        }
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )