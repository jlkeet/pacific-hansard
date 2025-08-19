# Hansard RAG Prototype — Coding Agent Build Spec (v0.1)

**Owner:** Jackson Keet\
**Agent audience:** Full‑stack coding agent (Python + Solr)\
**Goal:** Deliver a local, end‑to‑end Q&A prototype over Hansard records using hybrid retrieval (BM25 + embeddings) and an on‑device LLM (Llama 3 8B via Ollama).\
**Target hardware:** RTX 4060 8 GB (Windows/Linux/macOS acceptable).

---

## 0) Scope & Non‑Goals

**In‑scope**

- Parse Hansard HTML/PDF → normalized JSON items with rich metadata
- Chunking (speaker‑aware) + overlap
- Embedding generation (local, e5‑base‑v2 by default)
- Solr core with BM25 + kNN vector field (HNSW)
- Hybrid retrieval with reciprocal rank fusion (RRF)
- Optional re‑ranker stub (can be toggled off)
- LLM answer composer (Ollama Llama 3 8B, 4‑bit) with strict citation rules
- Minimal web API (FastAPI) + simple web UI (search bar, filters, results)

**Out‑of‑scope (v0.1)**

- Multi‑tenant auth, complex ACLs
- Training/fine‑tuning LLMs
- Full production observability; we’ll do simple logs/metrics

Success = local prototype answers questions with correct speaker/date/link citations at acceptable latency.

---

## 1) Glossary

- **Chunk:** A contiguous passage (≈600–900 words) ideally aligned to speaker turns.
- **Embedding:** Dense vector produced by an embedding model, used for semantic retrieval.
- **RAG:** Retrieval‑Augmented Generation; LLM answers using retrieved chunks only.

---

## 2) Data Model

### 2.1 Normalized JSON (one record per chunk)

```json
{
  "id": "nz-2016-06-21-house-1234-0001",
  "country": "NZ",
  "parliament": "52nd",
  "date": "2016-06-21",
  "chamber": "House",
  "session": "Budget Debate",
  "bill": "Tobacco Excise (Budget Measures)",
  "speaker": "Hon Jane Smith",
  "party": "National",
  "language": "en",
  "url": "https://example/hansard/2016-06-21#para-0001",
  "para_ids": [1,2,3],
  "text": "This Bill increases tobacco excise by 10% annually for four years…",
  "embedding": [/* float[] length 768; omitted at ingest pre-embedding step */]
}
```

Mandatory fields: `id,country,date,chamber,speaker,text,url`.\
Optional: `parliament,session,bill,party,language,para_ids`.

### 2.2 Speaker‑aware chunking rules

- Start a new chunk when:
  - Speaker changes, **or**
  - Token count > \~1000 tokens (≈750 words).
- Add overlap: \~120 tokens from end of previous chunk to start of next.
- Keep `para_ids` for in‑document context linking.

---

## 3) Solr Setup

### 3.1 Core & Schema

Create core: `hansard_rag`.

Field sketch (managed‑schema):

```xml
<field name="text"       type="text_en"    indexed="true" stored="true" multiValued="false"/>
<field name="date"       type="pdate"      indexed="true" stored="true"/>
<field name="speaker"    type="string"     indexed="true" stored="true"/>
<field name="bill"       type="text_en"    indexed="true" stored="true"/>
<field name="chamber"    type="string"     indexed="true" stored="true"/>
<field name="country"    type="string"     indexed="true" stored="true"/>
<field name="url"        type="string"     indexed="false" stored="true"/>
<field name="para_ids"   type="strings"    indexed="false" stored="true" multiValued="true"/>
<field name="embedding"  type="knn_vector" indexed="true" stored="false" vectorDimension="768" similarityFunction="cosine"/>
```

Configure HNSW params (example):

```json
{
  "add":{
    "name":"knn_hnsw",
    "class":"solr.DenseVectorField",
    "vectorDimension":768,
    "similarityFunction":"cosine",
    "hnsw": {"M":16, "efConstruction":128}
  }
}
```

### 3.2 Ingest

- POST JSON docs without `embedding` first (optional), or include precomputed vectors.
- Commit in batches of 1k–5k.

---

## 4) Embeddings Pipeline

Default model: `` (768‑dim). Alternative: `bge-base-en-v1.5`.

**Formatting for e5:**

- Query text → prefix with `query: `
- Passage text → prefix with `passage: `

**Batching:**

- Batch size auto‑tuned to fit VRAM (start 64; fall back to 32/16).

**Output:** float32 vectors; normalize to unit length.

**CLI (make target):**

```
make embed MODEL=e5-base-v2 INPUT=./data/json OUT=./data/with_vectors.jsonl
```

---

## 5) Retrieval Algorithm (Hybrid)

1. **BM25**: Solr `q=` with `edismax`; apply filters (date range, chamber, speaker, country).
2. **kNN**: `knn.q=embedding:[$EMBED(query_text)]&knn.k=50`.
3. **Merge** with **Reciprocal Rank Fusion (RRF)**: score = Σ 1/(k + rankᵢ). Use k=60. Keep top 30.
4. **Optional**: cross‑encoder re‑rank (stub; off by default).
5. **Select** top 12 chunks (by RRF or re‑ranked score) for LLM context.

Latency target (local): < 700 ms for retrieval @ 100k chunks.

---

## 6) LLM Integration

**Runner:** Ollama with `llama3:8b` (4‑bit).\
**Startup:**

```bash
ollama pull llama3:8b
ollama serve   # ensures API at http://localhost:11434
```

**Prompt (strict citations)**

```
SYSTEM:
You answer using ONLY the provided Hansard excerpts. If not found in them, say: "Not found in the provided records." Always cite like [#chunkId].

USER:
Question:
{question}

Excerpts:
{for each chunk i}
[#{i}] Speaker: {speaker} | Chamber: {chamber} | Date: {date} | URL: {url}
{text}
{/for}

Instructions:
- Be concise. Use neutral tone.
- Attach [#id] after the sentences they support.
- Include a short "Sources" list with speaker/date/URL.
```

**Guardrails**

- If model outputs claims without [#id], post‑process to drop those sentences or append a disclaimer.

---

## 7) API Design (FastAPI)

### 7.1 Endpoints

- `POST /ingest` — accept raw Hansard HTML/PDF (optional for v0.1; local batch is fine)
- `POST /index` — push prepared JSONL (with/without vectors) into Solr
- `GET  /search` — return hybrid results (no LLM)
- `POST /ask` — RAG: {question, filters} → answer + citations
- `GET  /healthz` — readiness check

### 7.2 Request/Response (examples)

**POST /ask**

```json
{
  "question": "What did the Minister of Health say about tobacco excise in 2016?",
  "filters": {
    "date_from": "2016-01-01",
    "date_to": "2016-12-31",
    "chamber": "House",
    "country": "NZ"
  },
  "top_k": 12
}
```

**Response**

```json
{
  "answer": "In 2016, the Minister stated that excise would rise 10% annually for four years… [#3]",
  "sources": [
    {"id": 3, "speaker": "Hon Jane Smith", "date": "2016-06-21", "url": "..."}
  ]
}
```

---

## 8) Simple Web UI (v0.1)

- Search bar + filters (date range picker, chamber, speaker, country)
- Results panel: final answer + collapsible list of cited chunks
- “Open in context” link → source URL with anchor/para id

---

## 9) Local Dev

**Requirements**

- Python 3.11+
- Java + Solr 9.x
- Ollama
- `pip install -r requirements.txt`

**Key packages**

- `fastapi`, `uvicorn`
- `pysolr`
- `sentence-transformers` (e5)
- `numpy`, `scikit-learn`
- `pydantic`

**Make targets**

```
make solr-up         # start solr & create core
make index           # index JSONL into solr
make embed           # generate vectors
make api             # run FastAPI
make ui              # run simple UI (vite/react) [optional]
```

---

## 10) Testing & Evaluation

### 10.1 Functional tests

- **/search** returns BM25 + kNN merged list, stable ordering (snapshot)
- **/ask** returns answer ≤ 2,000 chars with ≥1 citation
- Missing evidence → returns "Not found in the provided records."

### 10.2 Gold set (seed 20 Q→A)

Create small YAML with questions + expected doc IDs and regex for key facts. Example:

```yaml
- q: "Who introduced the Tobacco Excise Bill in 2016?"
  must_contain: ["Tobacco Excise", "2016"]
  expect_doc_speakers: ["Hon Jane Smith"]
```

### 10.3 Metrics

- Retrieval nDCG\@10 ≥ 0.7 against gold
- Answer citation accuracy ≥ 0.9 (IDs correspond to correct docs)
- Latency: p95 < 3.0s end‑to‑end on RTX 4060

---

## 11) Observability

- Structured logs (JSON) for `/ask`: question, filters, top doc IDs, tokens used, latency
- Simple `/metrics` with counters: queries\_total, cache\_hits, avg\_latency\_ms

---

## 12) Security & Privacy (local)

- No external calls in default mode (except model pulls)
- CORS locked to localhost for UI
- Input size limits: question ≤ 2,000 chars

---

## 13) Directory Layout

```
project/
  api/
    main.py            # FastAPI
    rag.py             # retrieval + fusion
    prompts.py         # LLM prompts
    models.py          # pydantic
  ingest/
    parse_html.py
    chunker.py
    embed.py
    index_solr.py
  ui/
    (optional simple SPA)
  configs/
    solr_schema.json
    settings.yaml
  data/
    json/              # raw parsed JSON
    with_vectors/      # JSONL with embeddings
  tests/
    test_search.py
    test_ask.py
  Makefile
  requirements.txt
```

---

## 14) Implementation Steps (Agent Task List)

1. **Bootstrap Solr core** (`hansard_rag`) with fields above; verify kNN works via a mock vector.
2. **Write parser** for sample Hansard HTML (provide 10 docs) → normalized JSON.
3. **Implement chunker** (speaker‑aware, overlap) + unit tests.
4. **Embedding script** using e5‑base‑v2 with GPU if available; persist vectors.
5. **Indexing script** to Solr (text + metadata + vectors).
6. **Hybrid retrieval** function (BM25 + kNN + RRF) with filters.
7. **LLM client** (Ollama) + strict prompt; compose answer + citations.
8. **FastAPI endpoints** `/search` and `/ask`; return JSON.
9. **Smoke tests** (gold set); measure latency.
10. **(Optional)** Simple UI: search, filters, answer + sources.

---

## 15) Acceptance Criteria (v0.1)

- Can index ≥ 50k chunks locally
- `/ask` answers within 3 s p95 on RTX 4060
- Each answer includes ≥1 valid citation with correct speaker/date/link
- Passing functional tests; nDCG\@10 ≥ 0.7 on seed gold set

---

## 16) Extensions (later)

- Cross‑encoder re‑ranker (e.g., `ms-marco-MiniLM-L-6-v2`)
- Multi‑country sharding + facets
- PDF viewer with highlighted spans
- Long‑context models (e.g., Llama 3.1‑8B‑instruct‑405B‑ctx) if available locally
- Caching layer (Faiss ANN cache for popular queries)
- Auth & audit logging for institutional users

---

## 17) Risks & Mitigations

- **Hallucination:** strict prompt; drop uncited sentences; show sources prominently
- **Index drift:** nightly embedding/index refresh jobs
- **Latency spikes:** cap chunks at 12; cache top‑k retrieval; use 4‑bit LLM
- **OCR noise in PDFs:** run OCR pass; strip artifacts; use language detection

---

## 18) Quickstart Commands

```bash
# 1) Start Solr
solr start -p 8983 && solr create -c hansard_rag

# 2) Pull LLM
ollama pull llama3:8b && ollama serve

# 3) Create virtualenv & deps
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 4) Parse, chunk, embed, index
python ingest/parse_html.py ./raw_html ./data/json
python ingest/chunker.py ./data/json ./data/json
py
```
