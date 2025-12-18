# Quick Start Guide - Modular Microservices

Get all 4 RAG services running locally in 10 minutes.

## Prerequisites

- Python 3.11+
- API Keys:
  - OpenAI API key (from https://platform.openai.com)
  - Pinecone API key (from https://pinecone.io)

## 1. Setup Environment Variables

```bash
# Create .env files for each service
for dir in apps/ingestion apps/retrieval apps/synthesis apps/frontend; do
  cp $dir/.env.example $dir/.env
done

# Edit each .env with your keys
nano apps/ingestion/.env    # Add OPENAI_API_KEY, PINECONE_API_KEY
nano apps/retrieval/.env    # Add OPENAI_API_KEY, PINECONE_API_KEY
nano apps/synthesis/.env    # Add OPENAI_API_KEY, set RETRIEVAL_SERVICE_URL=http://localhost:8001
nano apps/frontend/.env     # Set SYNTHESIS_SERVICE_URL=http://localhost:8002
```

## 2. Start All 4 Services (in separate terminals)

**Terminal 1 - Ingestion (Port 8000):**
```bash
cd apps/ingestion
pip install -r requirements.txt
uvicorn app:app --port 8000 --reload
```

**Terminal 2 - Retrieval (Port 8001):**
```bash
cd apps/retrieval
pip install -r requirements.txt
uvicorn app:app --port 8001 --reload
```

**Terminal 3 - Synthesis (Port 8002):**
```bash
cd apps/synthesis
pip install -r requirements.txt
uvicorn app:app --port 8002 --reload
```

**Terminal 4 - Frontend (Port 8003):**
```bash
cd apps/frontend
pip install -r requirements.txt
uvicorn app:app --port 8003 --reload
```

## 3. Test the Services

### Health Checks (in another terminal):
```bash
# Verify all services are running
curl http://localhost:8000/api/v1/health
curl http://localhost:8001/api/v1/health
curl http://localhost:8002/api/v1/health
curl http://localhost:8003/api/v1/health
```

### Test Ingestion Service:
```bash
# Upload a PDF
curl -X POST -F "file=@your_document.pdf" \
  http://localhost:8000/api/v1/ingest
```

### Test Retrieval Service:
```bash
# Search for similar chunks
curl -X POST -H "Content-Type: application/json" \
  -d '{"query":"What is your experience?","top_k":5}' \
  http://localhost:8001/api/v1/retrieve
```

### Test Synthesis Service:
```bash
# Generate LLM response with citations
curl -X POST -H "Content-Type: application/json" \
  -d '{"query":"What is your experience?"}' \
  http://localhost:8002/api/v1/synthesize
```

### Test Frontend Service (SSE Streaming):
```bash
# Get streaming response
curl -N -X POST -H "Content-Type: application/json" \
  -d '{"query":"What is your experience?"}' \
  http://localhost:8003/api/v1/query
```

Watch the SSE stream:
```
event: answer
data: {"text":"Based on the documents..."}

event: citation
data: {"doc_id": "...", "source_url": "...", "page": 1}

event: done
data: {"latency_ms": 1250, "tokens": 350}
```

## 4. Run Unit Tests

Each service has comprehensive unit tests with mocked dependencies (no API keys needed):

```bash
# Test Ingestion
cd apps/ingestion && pytest tests/ -v

# Test Retrieval
cd apps/retrieval && pytest tests/ -v

# Test Synthesis
cd apps/synthesis && pytest tests/ -v
```

All tests use conftest.py fixtures that mock OpenAI, Pinecone, and httpx calls.

## 5. View API Documentation

Each service has auto-generated docs:
- **Ingestion**: http://localhost:8000/docs
- **Retrieval**: http://localhost:8001/docs
- **Synthesis**: http://localhost:8002/docs
- **Frontend**: http://localhost:8003/docs

## Next Steps

1. **Ingest Multiple PDFs** - Try uploading various documents to ingestion service
2. **Monitor Metrics** - Check service logs for query metrics and costs
3. **Run Full Test Suite** - `pytest` in each app directory
4. **Deploy to GCP** - See [README_MODULAR.md](README_MODULAR.md) for Terraform setup

## Troubleshooting

**"Service not responding"**
- Check all 4 services are running in separate terminals
- Verify `.env` files are created and populated
- Check port assignments (8000-8003)

**"Pinecone error: Index does not exist"**
- Create index in Pinecone console or verify `PINECONE_INDEX_NAME` in `.env`

**"OpenAI API Error"**
- Verify `OPENAI_API_KEY` is correct and has quota
- Check `.env` for typos in variable names

**"Port already in use"**
```bash
# Use different ports
cd apps/ingestion && uvicorn app:app --port 9000
```

## Next: Deploy to GCP

Once tested locally, deploy all 4 services to Cloud Run:

```bash
# Build Docker images
for service in ingestion retrieval synthesis frontend; do
  docker build -t gcr.io/PROJECT_ID/rag-${service}:latest apps/${service}/
  docker push gcr.io/PROJECT_ID/rag-${service}:latest
done

# Deploy with Terraform
cd terraform/
terraform apply
```
```
event: progress
data: {"stage": "extracting", "message": "Extracting text from PDF..."}

event: progress
data: {"stage": "chunking", "message": "Chunking text..."}

event: complete
data: {"chunks_created": 15, "tokens_used": 2340, "cost_estimate": 0.000047}
```

**Query:**
```bash
curl -N -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What is machine learning?",
    "user_id": "test-user",
    "top_k": 3
  }'
```

Response streams as SSE:
```
event: token
data: "Machine Learning is a subset of"

event: token
data: " Artificial Intelligence"

event: citation
data: {"doc_id": "...", "source_url": "...", "page": 1}

event: done
data: {}
```

## 5. View API Docs

Open in browser:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Next Steps

1. **Ingest Multiple PDFs** - Try the other sample documents
2. **Monitor Metrics** - Check stdout logs for query metrics
3. **Deploy to GCP** - See [README.md](../README.md) for Terraform setup
4. **Fine-tune Prompts** - Edit `app/rag/prompt.py`

## Troubleshooting

**"Pinecone error: Index does not exist"**
- Create index in Pinecone console or verify `PINECONE_INDEX_NAME` in `.env`

**"OpenAI API Error"**
- Verify `OPENAI_API_KEY` is correct and has quota
- Check for typos in variable names

**"No chunks created"**
- PDF extraction may have failed
- Try with a different PDF or test with sample PDFs

**Port 8000 already in use**
- Use: `python -m uvicorn app.main:app --port 8001`

## Cost Tracking

Each query logs metrics:
```bash
# Grep logs for costs
python -m uvicorn app.main:app --reload 2>&1 | grep total_cost
```

Or check metrics on shutdown - aggregated summary is printed.

## Next: Deploy to GCP

Once tested locally, deploy to Cloud Run:

```bash
# Build and deploy
cd terraform/
terraform init
terraform apply
```

See [README.md](../README.md) for full deployment instructions.
