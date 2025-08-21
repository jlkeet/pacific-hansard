# AI Chat Integration - Railway Deployment Guide

## Current Architecture Overview

### Existing Railway Deployment
- **Platform**: Railway.app
- **Current Setup**: PHP/Apache container with MySQL + Python indexing
- **Repository**: https://github.com/jlkeet/pacific-hansard.git
- **Dockerfile**: `Dockerfile.railway-complete`
- **Health Check**: `/health.php`
- **Port**: Dynamic (set by Railway via $PORT)

### AI Chat Components (Currently Local)
1. **FastAPI RAG Service** - Python API at localhost:8000
2. **Ollama LLM** - Qwen2.5 7B model at localhost:11434  
3. **Updated Main Site** - Enhanced with AI chat modal integration

## Integration Status
✅ **Completed Locally:**
- AI chat modal integrated into main site (`/site/index.html`)
- Beautiful emoji-based response formatting (📋 Executive Summary, 🔍 Key Findings, etc.)
- Clickable citations with source modals
- Clean formatting without markdown symbols
- Responsive design matching existing site

## Deployment Strategy Options

### Option 1: Hybrid Deployment (Recommended for Testing)

**Deploy to Railway:**
- Main site with AI chat interface
- Keep RAG service running locally on development PC

**Required Changes:**
1. Update API URL in `/site/index.html` JavaScript:
   ```javascript
   // Change from:
   apiUrl: 'http://localhost:8000'
   // To:
   apiUrl: 'http://YOUR-PC-IP:8000'  // or use ngrok tunnel
   ```

2. Configure local PC to accept external connections:
   - Allow FastAPI on port 8000 through firewall
   - Consider using ngrok for secure tunneling

**Pros:** 
- Quick deployment
- Uses existing powerful PC for LLM processing
- Minimal infrastructure changes

**Cons:**
- Development PC must remain online 24/7
- Network dependency

### Option 2: Full Railway Deployment

**Requirements:**
- Railway service with sufficient specs for Ollama (8GB+ RAM, GPU preferred)
- Deploy complete RAG system to Railway

**New Services Needed:**
1. **RAG API Service** (FastAPI + Ollama)
2. **Enhanced Web Service** (existing + AI chat)

**Railway Configuration Changes:**
1. Create new `railway-ai.json`:
   ```json
   {
     "services": [
       {
         "name": "web",
         "source": { "repo": "https://github.com/jlkeet/pacific-hansard.git" },
         "dockerfile": "Dockerfile.web"
       },
       {
         "name": "ai-service", 
         "source": { "repo": "https://github.com/jlkeet/pacific-hansard.git" },
         "dockerfile": "Dockerfile.ai"
       }
     ]
   }
   ```

2. New Dockerfiles required:
   - `Dockerfile.web` - Current site + AI interface
   - `Dockerfile.ai` - FastAPI + Ollama service

### Option 3: Cloud LLM Integration

**Replace Local Ollama with:**
- OpenAI API
- Anthropic Claude API  
- Hugging Face Inference API

**Advantages:**
- No heavy compute requirements
- Serverless scaling
- Professional reliability

**Changes Required:**
- Modify `/rag/api/services/llm_service.py` to use cloud API
- Add API keys as Railway environment variables

## Recommended Implementation Steps

### Phase 1: Hybrid Testing
1. **Deploy updated site to Railway** with AI chat interface
2. **Set up secure tunnel** (ngrok) from Railway to local PC
3. **Test end-to-end functionality**
4. **Monitor performance and reliability**

### Phase 2: Full Cloud Migration (if Phase 1 successful)
1. **Choose LLM approach** (local Ollama vs cloud API)
2. **Create multi-service Railway configuration**
3. **Set up proper environment variables**
4. **Deploy and test**

## Files Modified for AI Integration

### Updated Files:
- `/site/index.html` - Added AI chat modal, JavaScript, and CSS
- `/rag/api/services/llm_service.py` - Enhanced prompt formatting

### Current API Endpoint Used:
- `POST /ask` - Main chat endpoint
- `GET /document/{doc_id}` - Full document viewing

## Environment Variables Needed

### For Railway Deployment:
```bash
# Existing
MYSQL_URL=(Railway provides)
SOLR_URL=http://solr-service:8983/solr/hansard_core

# New for AI Chat
AI_API_URL=http://ai-service:8000  # if using separate service
OLLAMA_URL=http://localhost:11434  # if bundled
LLM_MODEL=qwen2.5:7b

# If using cloud LLM instead
OPENAI_API_KEY=your_key_here
# OR
ANTHROPIC_API_KEY=your_key_here
```

## Next Session Action Items

When resuming work:

1. **Choose deployment approach** (Hybrid vs Full vs Cloud LLM)
2. **Update JavaScript API URL** if going hybrid
3. **Create appropriate Dockerfile(s)** if going full Railway
4. **Set up environment variables** in Railway dashboard
5. **Test deployment** and troubleshoot any issues
6. **Monitor performance** and user experience

## Technical Notes

- **Current LLM Model**: Qwen2.5 7B (requires ~8GB RAM)
- **Response Format**: Emoji headers with bullet points (no markdown symbols)
- **Citation System**: Clickable [#0], [#1] references with source modals
- **Mobile Responsive**: Chat interface adapts to small screens
- **Integration**: Modal overlay, doesn't interfere with existing search functionality

## Cost Considerations

- **Hybrid**: Free (uses existing PC)
- **Railway Full**: Higher tier service needed for LLM (~$20-50/month)
- **Cloud LLM**: Pay per API call (~$0.01-0.10 per response)

---

*Document created for context preservation across conversation sessions*