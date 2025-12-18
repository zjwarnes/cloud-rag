# Modular RAG - Quick Reference

## Service Ports
```
Ingestion:   http://localhost:8000
Retrieval:   http://localhost:8001
Synthesis:   http://localhost:8002
Frontend:    http://localhost:8003
```

## Environment Variables Template

Create `.env` in each app directory:

**apps/ingestion/.env**:
```env
OPENAI_API_KEY=sk-...
PINECONE_API_KEY=pk-...
PINECONE_INDEX_NAME=portfolio-rag
GCP_PROJECT_ID=your-project
GCS_BUCKET_NAME=your-bucket
EMBEDDING_BATCH_SIZE=20
```

**apps/retrieval/.env**:
```env
OPENAI_API_KEY=sk-...
PINECONE_API_KEY=pk-...
PINECONE_INDEX_NAME=portfolio-rag
GCP_PROJECT_ID=your-project
QUERY_TOP_K=10
```

**apps/synthesis/.env**:
```env
OPENAI_API_KEY=sk-...
GCP_PROJECT_ID=your-project
RETRIEVAL_SERVICE_URL=http://localhost:8001
LLM_TEMPERATURE=0.7
LLM_MAX_TOKENS=1000
MAX_CONTEXT_TOKENS=2000
```

**apps/frontend/.env**:
```env
SYNTHESIS_SERVICE_URL=http://localhost:8002
STREAMING_BUFFER_SIZE=100
```

## Startup Scripts

**One-liner to start all services** (run from repo root in separate tmux/screen windows):
```bash
# Terminal 1
cd apps/ingestion && pip install -r requirements.txt && uvicorn app:app --port 8000

# Terminal 2
cd apps/retrieval && pip install -r requirements.txt && uvicorn app:app --port 8001

# Terminal 3
cd apps/synthesis && pip install -r requirements.txt && uvicorn app:app --port 8002

# Terminal 4
cd apps/frontend && pip install -r requirements.txt && uvicorn app:app --port 8003
```

## Quick API Tests

**Health checks**:
```bash
curl http://localhost:8000/api/v1/health
curl http://localhost:8001/api/v1/health
curl http://localhost:8002/api/v1/health
curl http://localhost:8003/api/v1/health
```

**Upload PDF**:
```bash
curl -X POST -F "file=@document.pdf" http://localhost:8000/api/v1/ingest
```

**Retrieve chunks**:
```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{"query":"What is your experience?","top_k":5}' \
  http://localhost:8001/api/v1/retrieve
```

**Synthesize response**:
```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{"query":"What is your experience?"}' \
  http://localhost:8002/api/v1/synthesize
```

**Stream from frontend**:
```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{"query":"What is your experience?"}' \
  http://localhost:8003/api/v1/query
```

## Run Tests

```bash
# Ingestion tests
cd apps/ingestion && pytest tests/ -v

# Retrieval tests
cd apps/retrieval && pytest tests/ -v

# Synthesis tests
cd apps/synthesis && pytest tests/ -v
```

## Project Structure

```
apps/
├── ingestion/      # PDF upload, extraction, chunking, embedding
├── retrieval/      # Vector search, ranking, filtering
├── synthesis/      # LLM response generation with citations
└── frontend/       # SSE streaming API

common/            # Shared models, config, metrics
├── models.py       # Pydantic models
├── config.py       # Settings classes
├── metrics.py      # Metrics collection
└── utils.py        # Utilities

terraform/         # Cloud Run deployment
```

## Key Files per Service

Each service has:
- `app.py` - FastAPI entry point
- `config.py` - Settings loader
- `services/pipeline.py` - Business logic
- `handlers/routes.py` - API endpoints
- `tests/conftest.py` - Pytest fixtures
- `tests/test_*.py` - Unit tests
- `requirements.txt` - Dependencies
- `Dockerfile` - Container image
- `.env.example` - Environment template

## Common Models

**IngestRequest** → Ingestion service
```python
{"file": <UploadFile>, "user_id": "default"}
```

**RetrievalRequest** → Retrieval service
```python
{"query": "What is your experience?", "user_id": "default", "top_k": 10}
```

**SynthesisRequest** → Synthesis service
```python
{"query": "What is your experience?", "user_id": "default"}
```

**FrontendRequest** → Frontend service
```python
{"query": "What is your experience?", "user_id": "default"}
```

## Docker Build & Deploy

**Local build**:
```bash
export PROJECT_ID=your-project-id

docker build -t gcr.io/${PROJECT_ID}/rag-ingestion:latest apps/ingestion/
docker build -t gcr.io/${PROJECT_ID}/rag-retrieval:latest apps/retrieval/
docker build -t gcr.io/${PROJECT_ID}/rag-synthesis:latest apps/synthesis/
docker build -t gcr.io/${PROJECT_ID}/rag-frontend:latest apps/frontend/
```

**Push to GCR**:
```bash
docker push gcr.io/${PROJECT_ID}/rag-ingestion:latest
docker push gcr.io/${PROJECT_ID}/rag-retrieval:latest
docker push gcr.io/${PROJECT_ID}/rag-synthesis:latest
docker push gcr.io/${PROJECT_ID}/rag-frontend:latest
```

**Deploy with Terraform**:
```bash
cd terraform
terraform init
terraform plan
terraform apply
```

## Troubleshooting

**Port already in use**:
```bash
# Find process using port
lsof -i :8000

# Kill it
kill -9 <PID>
```

**Import errors**:
```bash
# Make sure PYTHONPATH includes parent directories
export PYTHONPATH=/home/zac/gcp-rag:$PYTHONPATH
```

**API key errors**:
```bash
# Check .env files are created and have correct keys
cat apps/ingestion/.env | grep OPENAI_API_KEY
cat apps/ingestion/.env | grep PINECONE_API_KEY
```

**Service not responding**:
```bash
# Check logs
uvicorn app:app --port 8000 --log-level debug

# Verify health endpoint
curl -v http://localhost:8000/api/v1/health
```

## Performance Tips

1. **Batch embeddings**: Ingestion batches requests (default 20)
2. **Vector search limit**: Retrieval retrieves top_k only
3. **Context budget**: Synthesis limits context to 2000 tokens
4. **Async I/O**: All services use httpx for async calls

## Scaling

Each service can auto-scale independently on Cloud Run:
- Min instances: 0 (save costs when idle)
- Max instances: 100 (handle traffic spikes)
- Memory: 256Mi (frontend) to 512Mi (synthesis)
- CPU: Shared (auto-adjusted based on memory)

## Metrics

All services log JSON metrics:
```json
{
  "query_id": "unique-id",
  "service": "ingestion",
  "latency_ms": 1250,
  "success": true,
  "error": null,
  "timestamp": "2024-01-15T10:30:45Z"
}
```

View in Cloud Logging:
```bash
gcloud logging read "service:rag-ingestion" --limit 50 --format=json
```

## Next Steps

1. ✅ All 4 services created with tests
2. ✅ Dockerfiles for each service
3. ✅ Terraform for Cloud Run deployment
4. 🔄 **You're here** - Ready to test locally
5. 📦 Next: Deploy to GCP

See [ARCHITECTURE.md](ARCHITECTURE.md) for detailed design docs.
