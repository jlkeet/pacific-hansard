"""
Pydantic models for API request/response schemas
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from datetime import datetime

class SearchRequest(BaseModel):
    """Request model for search endpoint"""
    query: str = Field(..., description="Search query text")
    filters: Dict[str, Optional[str]] = Field(default_factory=dict, description="Search filters")
    top_k: int = Field(default=12, ge=1, le=50, description="Number of results to return")

class SearchResult(BaseModel):
    """Individual search result"""
    id: str = Field(..., description="Unique chunk ID")
    doc_id: str = Field(..., description="Source document ID") 
    text: str = Field(..., description="Chunk text content")
    speaker: str = Field(..., description="Speaker name")
    date: str = Field(..., description="Document date")
    country: str = Field(..., description="Country/source")
    chamber: str = Field(..., description="Parliament chamber")
    url: str = Field(..., description="Source document URL")
    score: float = Field(..., description="Relevance score")
    chunk_index: int = Field(..., description="Chunk position in document")

class SearchResponse(BaseModel):
    """Response model for search endpoint"""
    query: str = Field(..., description="Original search query")
    results: List[SearchResult] = Field(..., description="Search results")
    total_found: int = Field(..., description="Total number of results found")
    response_time_ms: float = Field(..., description="Response time in milliseconds")
    search_type: str = Field(..., description="Type of search performed")

class AskRequest(BaseModel):
    """Request model for ask endpoint"""
    question: str = Field(..., description="Natural language question")
    filters: Dict[str, Optional[str]] = Field(default_factory=dict, description="Search filters")
    top_k: int = Field(default=12, ge=1, le=50, description="Number of chunks to retrieve")
    temperature: float = Field(default=0.1, ge=0.0, le=1.0, description="LLM temperature")

class SourceCitation(BaseModel):
    """Source citation for answers"""
    id: str = Field(..., description="Chunk ID")
    speaker: str = Field(..., description="Speaker name")
    date: str = Field(..., description="Document date")
    url: str = Field(..., description="Source document URL")
    text_preview: str = Field(..., description="Preview of source text")
    full_text: str = Field(..., description="Complete source text")
    country: str = Field(..., description="Country/source")
    doc_id: Optional[str] = Field(None, description="Document ID")
    chunk_index: Optional[int] = Field(None, description="Chunk position")

class AskResponse(BaseModel):
    """Response model for ask endpoint"""
    question: str = Field(..., description="Original question")
    answer: str = Field(..., description="Generated answer with citations")
    sources: List[SourceCitation] = Field(..., description="Source citations")
    response_time_ms: float = Field(..., description="Response time in milliseconds")
    model_used: str = Field(..., description="LLM model used for generation")
    chunks_used: int = Field(..., description="Number of chunks used in context")

class HealthResponse(BaseModel):
    """Response model for health check"""
    status: str = Field(..., description="Overall health status")
    timestamp: datetime = Field(..., description="Health check timestamp")
    services: Dict[str, str] = Field(..., description="Individual service status")
    version: str = Field(..., description="API version")

class ErrorResponse(BaseModel):
    """Error response model"""
    error: str = Field(..., description="Error message")
    status_code: int = Field(..., description="HTTP status code")
    timestamp: str = Field(..., description="Error timestamp")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")