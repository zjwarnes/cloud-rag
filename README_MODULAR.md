# GCP RAG - Modular Microservices Architecture

A production-grade Retrieval-Augmented Generation (RAG) system on Google Cloud Platform, split into 4 independently deployable microservices.

## 🏗️ Architecture

```
Frontend (8003)
    ↓
Synthesis (8002) → Retrieval (8001)
    ↓                  ↓
    ←─────────────────→ Pinecone
           ↑
        (upload)
           ↑
     Ingestion (8000)
```

**Services**:
- **Ingestion** (Port 8000): PDF upload → chunking → embedding → Pinecone storage
- **Retrieval** (Port 8001): Query embedding → vector search → ranking → chunks
- **Synthesis** (Port 8002): Calls Retrieval + LLM → response with citations
- **Frontend** (Port 8003): SSE streaming API consumer

## 🚀 Quick Start

### Prerequisites
```bash
export OPENAI_API_KEY=sk-...
export PINECONE_API_KEY=pk-...
export GCP_PROJECT_ID=your-project
export GCS_BUCKET_NAME=your-bucket
```

### Run All Services (4 terminals)

**Terminal 1 - Ingestion**:
```bash
cd apps/ingestion && pip install -r requirements.txt && cp .env.example .env
# Edit .env with your keys
uvicorn app:app --reload --port 8000
```

**Terminal 2 - Retrieval**:
```bash
cd apps/retrieval && pip install -r requirements.txt && cp .env.example .env
uvicorn app:app --reload --port 8001
```

**Terminal 3 - Synthesis**:
```bash
cd apps/synthesis && pip install -r requirements.txt && cp .env.example .env
# Set RETRIEVAL_SERVICE_URL=http://localhost:8001 in .env
uvicorn app:app --reload --port 8002
```

**Terminal 4 - Frontend**:
```bash
cd apps/frontend && pip install -r requirements.txt && cp .env.example .env
# Set SYNTHESIS_SERVICE_URL=http://localhost:8002 in .env
uvicorn app:app --reload --port 8003
```

### Test the System
```bash
# Check health
curl http://localhost:8000/api/v1/health
curl http://localhost:8001/api/v1/health
curl http://localhost:8002/api/v1/health
curl http://localhost:8003/api/v1/health

# Ingest a PDF
curl -X POST -F "file=@/path/to/document.pdf" http://localhost:8000/api/v1/ingest

# Query
curl -X POST -H "Content-Type: application/json" \
  -d '{"query":"What is the main topic?"}' \
  http://localhost:8003/api/v1/query
```

## 📋 Project Structure

```
gcp-rag/
├── common/                    # Shared library (models, config, metrics)
│   ├── models.py             # Pydantic models for all services
│   ├── config.py             # Settings with lru_cache
│   ├── metrics.py            # Metrics collection and timing
│   └── utils.py              # Utilities (chunking, cost estimation)
│
├── apps/
│   ├── ingestion/            # PDF ingestion service
│   │   ├── app.py            # FastAPI entry point
│   │   ├── config.py         # Ingestion settings
│   │   ├── services/
│   │   │   └── pipeline.py   # PDFExtractor, Embedding, VectorStore
│   │   ├── handlers/
│   │   │   └── routes.py     # POST /ingest, GET /health
│   │   ├── tests/
│   │   │   ├── conftest.py   # Pytest fixtures
│   │   │   └── test_pipeline.py
│   │   ├── requirements.txt
│   │   ├── Dockerfile
│   │   └── .env.example
│   │
│   ├── retrieval/            # Vector search service
│   │   ├── app.py
│   │   ├── config.py
│   │   ├── services/
│   │   │   └── pipeline.py   # Search, Ranking, Deduplication
│   │   ├── handlers/
│   │   │   └── routes.py     # POST /retrieve
│   │   ├── tests/
│   │   ├── requirements.txt
│   │   ├── Dockerfile
│   │   └── .env.example
│   │
│   ├── synthesis/            # LLM response generation
│   │   ├── app.py
│   │   ├── config.py
│   │   ├── services/
│   │   │   └── pipeline.py   # Calls Retrieval + LLM + Citations
│   │   ├── handlers/
│   │   │   └── routes.py     # POST /synthesize
│   │   ├── tests/
│   │   ├── requirements.txt
│   │   ├── Dockerfile
│   │   └── .env.example
│   │
│   └── frontend/             # SSE streaming API
│       ├── app.py
│       ├── config.py
│       ├── handlers/
│       │   └── routes.py     # POST /query (SSE)
│       ├── requirements.txt
│       ├── Dockerfile
│       └── .env.example
│
├── terraform/
│   └── main.tf               # Cloud Run + Networking
│
├── ARCHITECTURE.md           # Detailed architecture
└── README.md                 # This file
```

## 🧪 Testing

Each service has comprehensive unit tests with mocked dependencies:

```bash
# Test all services
cd apps/ingestion && pytest tests/ -v
cd apps/retrieval && pytest tests/ -v
cd apps/synthesis && pytest tests/ -v
```

**Mock fixtures** (in `conftest.py`):
- ✅ OpenAI API mocked
- ✅ Pinecone index mocked
- ✅ httpx for inter-service calls mocked
- ✅ All tests run without API keys

## 🔧 Configuration

All services use environment variables (see `.env.example` in each directory):

**Common**:
- `OPENAI_API_KEY` - OpenAI API key
- `PINECONE_API_KEY` - Pinecone API key
- `GCP_PROJECT_ID` - GCP project ID
- `GCS_BUCKET_NAME` - GCS bucket name

**Ingestion**:
- `EMBEDDING_BATCH_SIZE` - Batch size for embeddings (default: 20)

**Retrieval**:
- `QUERY_TOP_K` - Number of chunks to retrieve (default: 10)

**Synthesis**:
- `RETRIEVAL_SERVICE_URL` - Retrieval service URL
- `LLM_TEMPERATURE` - LLM temperature (default: 0.7)
- `LLM_MAX_TOKENS` - Max tokens for response (default: 1000)
- `MAX_CONTEXT_TOKENS` - Max context tokens (default: 2000)

**Frontend**:
- `SYNTHESIS_SERVICE_URL` - Synthesis service URL
- `STREAMING_BUFFER_SIZE` - SSE buffer size (default: 100)

## 📦 Deployment on GCP

### 1. Build Docker Images
```bash
export PROJECT_ID=your-project-id

for service in ingestion retrieval synthesis frontend; do
  docker build -t gcr.io/${PROJECT_ID}/rag-${service}:latest apps/${service}/
  docker push gcr.io/${PROJECT_ID}/rag-${service}:latest
done
```

### 2. Deploy with Terraform
```bash
cd terraform

# Create configuration
cat > terraform.tfvars <<EOF
gcp_project_id      = "your-project-id"
gcp_region          = "us-central1"
openai_api_key      = "sk-..."
pinecone_api_key    = "pk-..."
gcs_bucket_name     = "your-unique-bucket-name"
EOF

# Deploy
terraform init
terraform plan
terraform apply

# Get output URLs
terraform output frontend_url
```

## 📊 Monitoring

All services log metrics as JSON:

```json
{
  "query_id": "abc-123",
  "service": "synthesis",
  "latency_ms": 1250,
  "success": true,
  "tokens_used": 350,
  "cost_estimate": 0.015
}
```

View logs:
```bash
gcloud logging read "service:rag-*" --limit 50 --format=json
```

## 🔗 API Endpoints

### Ingestion Service
- `POST /api/v1/ingest` - Upload and ingest PDF
- `GET /api/v1/health` - Health check

### Retrieval Service
- `POST /api/v1/retrieve` - Search and retrieve chunks
- `GET /api/v1/health` - Health check

### Synthesis Service
- `POST /api/v1/synthesize` - Generate response with citations
- `GET /api/v1/health` - Health check

### Frontend Service
- `POST /api/v1/query` - Query with SSE streaming
- `GET /api/v1/health` - Health check

## ✨ Key Features

✅ **Independent Services**: Deploy each service separately
✅ **Type-Safe**: Pydantic models for all service boundaries
✅ **Testable**: All dependencies mockable with pytest fixtures
✅ **Scalable**: Each service auto-scales on Cloud Run
✅ **Modular**: Clear separation of concerns
✅ **Cost-Efficient**: Pay only for what you use
✅ **Extensible**: Easy to add new services or features
✅ **Monitored**: JSON logging for easy parsing

## 🚦 What's Next

1. **Local Testing**: Start all 4 services and test end-to-end
2. **GCP Setup**: Create GCP project and enable services
3. **Deploy**: Build images and deploy with Terraform
4. **Monitor**: Watch logs and metrics in Cloud Console
5. **Scale**: Adjust Cloud Run min/max instances as needed

## 📚 Documentation

- **[ARCHITECTURE.md](ARCHITECTURE.md)** - Detailed architecture and design decisions
- **[DEVELOPMENT.md](DEVELOPMENT.md)** - Development guide (if exists)
- **[SETUP_CHECKLIST.md](SETUP_CHECKLIST.md)** - Step-by-step setup checklist

## 🤝 Contributing

To add a new service:
1. Create `apps/newservice/` with same structure
2. Add models to `common/models.py`
3. Add settings to `common/config.py`
4. Create FastAPI app in `newservice/app.py`
5. Add tests in `newservice/tests/`
6. Add Dockerfile and requirements.txt
7. Update Terraform for Cloud Run deployment

## 📝 License

MIT

---

**Questions?** Check [ARCHITECTURE.md](ARCHITECTURE.md) or review example code in the services.
