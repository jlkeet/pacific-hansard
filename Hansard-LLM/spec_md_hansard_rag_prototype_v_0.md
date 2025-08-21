# SPEC.md — Hansard RAG Prototype (v0.1)

## 1. Overview
**Goal:** Local Q&A over Hansard records using hybrid retrieval (BM25 + embeddings) and an on‑device LLM (Llama 3 8B via Ollama).  
**Owner:** Jackson Keet  
**Target hardware:** RTX 4060 8 GB (dev); optional cloud LLM fallback.  
**Outcomes:** Concise answers with correct citations (speaker/date/link) under 3 s p95.

---

## 2. System Architecture
```
Browser ─▶ API (FastAPI: /search, /ask)
             ├─▶ Solr 9 (BM25 + kNN/HNSW, alias: hansard_rag_current)
             └─▶ LLM runner (Ollama llama3:8b)  ←→  Optional cloud LLM
```
**Services**: Solr, API, LLM Runner (Ollama).  
**Data store**: Solr only (text + vector).  
**Indexes**: blue/green cores, published via alias.

---

## 3. Data Model (JSONL chunks)
**MVP fields**
- `id`, `doc_id`, `text`, `date`, `country`, `chamber`, `speaker`, `url`, `page_from`, `page_to`, `para_ids`, `embedding`
**Recommended**
- `speaker_raw`, `speaker_id`, `party`, `session`, `bill`, `language`, `source_type`, `hash`, `chunk_index`, `tokens`, `ocr_confidence`

**Chunking policy**: speaker‑aware; new chunk on speaker change or ~1000 tokens; ~120‑token overlap; carry paragraph IDs and page range.

---

## 4. Pipelines
### 4.1 Ingest (ETL)
1) **Extract** PDF/HTML → cleaned text + metadata  
2) **Normalize** (Unicode, whitespace, boilerplate strip, hyphen repair)  
3) **Structure** (date/chamber/speaker/session/bill detection)  
4) **Chunk** (speaker‑aware + overlap) → JSONL

### 4.2 Embeddings
- Model: `intfloat/e5-base-v2` (768‑dim; normalized)  
- Query prefix: `query: `; Passage prefix: `passage: `  
- Batch on GPU if available; CPU fallback.

### 4.3 Indexing (Solr 9)
- Fields: `text`, `date`, `speaker`, `bill`, `chamber`, `country`, `url`, `para_ids`, `embedding(knn_vector)`  
- HNSW: `M=16`, `efConstruction=128`; similarity `cosine`  
- Blue/green cores; publish via alias `hansard_rag_current`.

### 4.4 Retrieval (Hybrid)
1) BM25 (edismax) with filters  
2) kNN (`knn.q=embedding:[$EMBED(query)]&knn.k=50`)  
3) Fuse via **Reciprocal Rank Fusion** (RRF; k=60)  
4) Select top 12 chunks (or token budget)  
5) Optional: cross‑encoder re‑ranker (toggle).

### 4.5 Generation (LLM)
- Runner: **Ollama** `llama3:8b` (4‑bit recommended)  
- Prompt: “Answer **only** from provided excerpts; if unknown, say ‘Not found in the provided records.’ Attach [#id] after supported sentences. Include short Sources list.”  
- Post‑process: drop sentences without `[#id]`.

---

## 5. API Contract
### 5.1 `GET /search`
**Query:** `q`, optional `filters` (date_from/to, chamber, country, speaker, party), `top_k` (default 12)  
**Returns:** fused ranked hits (without LLM answer)

### 5.2 `POST /ask`
```json
{
  "question": "What did the Minister of Health say about tobacco excise in 2016?",
  "filters": {"date_from": "2016-01-01", "date_to": "2016-12-31", "chamber": "House", "country": "NZ"},
  "top_k": 12
}
```
**Response**
```json
{
  "answer": "… 10% annually for four years [#3]",
  "sources": [{"id": 3, "speaker": "Hon Jane Smith", "date": "2016-06-21", "url": "…"}]
}
```

---

## 6. Deployment
- **Local dev**: Docker Compose (Solr, Ollama, API)  
- **Reverse proxy**: Nginx/Caddy TLS in front of API  
- **Config**: `SOLR_URL`, `OLLAMA_URL`, `LLM_BACKEND` (ollama:// or cloud)  
- **Security**: JWT/API key, CORS to site, rate‑limit 10 req/min/IP, 25s timeout

---

## 7. Automation (Updates)
- Schedule: cron/Prefect  
- Steps: detect → download → extract → chunk → embed → index → verify → alias swap  
- Idempotency: `doc_id` & `hash`; embed only new/changed chunks  
- Verification: counts, canned `/search`, 3–5 gold `/ask` checks

---

## 8. Acceptance Criteria (v0.1)
- Index ≥ 50k chunks  
- `/ask` p95 < 3.0 s on RTX 4060  
- Each answer has ≥ 1 valid citation (speaker/date/link)  
- Retrieval nDCG@10 ≥ 0.7 on 20‑Q gold set  
- Alias‑based blue/green publish with rollback

---

## 9. Milestones & Tickets
1) Parser + Chunker + tests  
2) Embeddings job  
3) Solr schema + indexer + `solr-up`  
4) Hybrid retrieval + `/search`  
5) LLM prompt + `/ask` + citation guard  
6) Compose + README + healthchecks  
(Optional) Reranker; alias swap; auto‑pipeline.

---

## 10. Make Targets (suggested)
```
make solr-up       # start solr & create core/alias
make embed         # generate vectors from JSONL
make index         # index into build core
make api           # run FastAPI
make pipeline      # crawl→extract→chunk→embed→index→verify→publish
```

---

## 11. Observability & Logs
- Log timings: embed/retrieval/LLM; tokens; model used  
- `/metrics` counters: queries_total, cache_hits, avg_latency_ms  
- Redact PII; sample 1% of prompts for QA

---

## 12. Risks & Mitigations
- **Hallucinations** → strict prompt + citation enforcement; “Not found” fallback  
- **OCR noise** → confidence scores; heuristic cleaners; manual review queue  
- **Latency spikes** → cap chunks@12; 4‑bit LLM; cache retrieval  
- **Index drift** → nightly refresh; alias rollback

---

## 13. Quickstart
```bash
# Solr
solr start -p 8983 && solr create -c hansard_rag

# LLM
ollama pull llama3:8b && ollama serve

# Python
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Ingest → Embed → Index → API
python ingest/parse_html.py raw_html data/json
python ingest/chunker.py   data/json data/chunks.jsonl
python ingest/embed.py     --model e5-base-v2 --in data/chunks.jsonl --out data/vectors.jsonl
python ingest/index_solr.py --in data/vectors.jsonl --core hansard_rag
uvicorn api.main:app --reload
```

---

## 14. Appendix: Prompt Template (LLM)
```
SYSTEM:
Answer using ONLY the provided Hansard excerpts. If not found in them, say: "Not found in the provided records." Attach [#id] after supported sentences.

USER:
Question:
{question}

Excerpts:
{for i,chunk}
[#{i}] Speaker: {speaker} | Chamber: {chamber} | Date: {date} | URL: {url}
{text}
{/for}

Instructions:
- Be concise and neutral.
- Include a short "Sources" list with speaker/date/URL.
```

