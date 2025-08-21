# Hansard LLM Implementation Progress

## Project Overview
Converting existing Pacific Hansard search system into an intelligent Q&A system using RAG (Retrieval-Augmented Generation) with local LLM.

**Goal**: Enable natural language queries over parliamentary records with accurate citations and sub-3s response times.

---

## Current Infrastructure Analysis (Completed ✅)

### Existing System
- **Data Sources**: Cook Islands, Fiji, Papua New Guinea parliamentary records
- **Storage**: MySQL database + Solr search index  
- **Web Interface**: PHP-based search with Bootstrap UI
- **Processing**: Python pipelines for document parsing/indexing
- **Deployment**: Docker Compose (MySQL, Solr, Nginx, PHP-FPM)

### Data Pipeline
- HTML/PDF parsing with BeautifulSoup
- Metadata extraction (speaker, date, chamber, country)
- Content cleaning and normalization
- Solr indexing for full-text search

### Current Capabilities
- Full-text search across documents
- Filter by country, speaker, date range
- Document browsing and export
- Real-time search suggestions

---

## LLM Integration Architecture (Planned)

### Target Architecture
```
Browser ─▶ FastAPI (/search, /ask)
             ├─▶ Solr 9 (BM25 + kNN/HNSW)  
             └─▶ Ollama (Llama 3 8B) ←→ Optional cloud fallback
```

### Key Components
1. **FastAPI Service**: New Python backend for LLM endpoints
2. **Ollama**: Local LLM runner (Llama 3 8B, 4-bit quantization)
3. **Enhanced Solr**: Add vector embeddings to existing schema
4. **Hybrid Search**: BM25 + semantic search with RRF fusion
5. **Citation System**: Track sources with [#id] references

---

## Implementation Roadmap

### Phase 1: Core LLM Infrastructure
- [x] **Task 5**: Create FastAPI backend service for LLM integration ✅
- [x] **Task 7**: Set up Ollama LLM service integration ✅  
- [ ] **Task 10**: Update Docker Compose with new services

### Phase 2: RAG Pipeline
- [x] **Task 8**: Create data chunking and embedding pipeline ✅
- [ ] **Task 6**: Implement hybrid search (BM25 + embeddings) with existing Solr
- [x] **Task 9**: Build RAG Q&A endpoints with citation tracking ✅

### Phase 3: Integration & UI  
- [ ] **Task 11**: Create enhanced web UI for LLM chat interface

---

## Technical Specifications

### Data Model (JSONL chunks)
**MVP Fields**: `id`, `doc_id`, `text`, `date`, `country`, `chamber`, `speaker`, `url`, `page_from`, `page_to`, `embedding`

**Chunking Policy**: Speaker-aware; new chunk on speaker change or ~1000 tokens; ~120-token overlap

### LLM Configuration
- **Model**: Llama 3 8B via Ollama (4-bit recommended for RTX 4060)
- **Embeddings**: `intfloat/e5-base-v2` (768-dim, normalized)
- **Retrieval**: Top 12 chunks via RRF fusion (k=60)

### API Endpoints
- `GET /search` - Hybrid search without LLM
- `POST /ask` - Natural language Q&A with citations

---

## Success Criteria
- Index ≥ 50k chunks from existing data
- `/ask` p95 < 3.0s on RTX 4060  
- Each answer has ≥ 1 valid citation (speaker/date/link)
- Strict citation enforcement to prevent hallucinations

---

## Next Steps
1. **Start with FastAPI service setup** - Foundation for LLM integration
2. **Ollama installation and testing** - Verify local LLM capabilities
3. **Enhanced Solr schema** - Add vector field support

---

## Session Notes
- **Date**: 2025-01-20
- **Current Status**: Analysis complete, ready to begin implementation
- **Focus**: Leverage existing infrastructure, add RAG capabilities on top
- **Architecture Decision**: FastAPI service complements existing PHP APIs rather than replacing them
