# Cloud RAG - Production-Grade Retrieval-Augmented Generation System

A comprehensive Retrieval-Augmented Generation (RAG) system built as 4 independent microservices using FastAPI, Pinecone, and Google Cloud Run. Designed for production deployments with enterprise-grade features including distributed processing, cost tracking, and comprehensive monitoring.

## System Architecture

```
                          ┌─────────────────┐
                          │    Frontend     │
                          │  (Port 8003)    │
                          │  SSE Streaming  │
                          └────────┬────────┘
                                   │
                                   ▼
                    ┌──────────────────────────┐
                    │      Synthesis           │
                    │   LLM Response Gen       │
                    │      (Port 8002)         │
                    └──────────┬───────────────┘
                               │
                               ▼
        ┌──────────────────────────────────────────┐
        │            Retrieval Service             │
        │      Vector Search & Ranking             │
        │           (Port 8001)                    │
        └──────────────┬──────────────────────────┘
                       │
                       ▼
        ┌──────────────────────────────────────────┐
        │           Pinecone Vector DB             │
        │      (Embeddings & Metadata)             │
        └──────────────────────────────────────────┘

┌──────────────────────────────────────────────────┐
│         Ingestion Service (Port 8000)            │
│    PDF → Chunks → Embeddings → Vector Storage   │
└──────────────────────────────────────────────────┘
```

## Core Features

- **Modular Microservices Architecture** - 4 independently deployable FastAPI services
- **Real-Time Streaming** - Server-Sent Events (SSE) for progressive response streaming
- **Citation-Backed Answers** - Source references with document metadata and page numbers
- **Type-Safe APIs** - Pydantic models for all inter-service communication
- **Production Ready** - Docker containerization, comprehensive error handling, structured logging
- **Cost Tracking** - Real-time token counting, embedding cost calculation, usage monitoring
- **Infrastructure as Code** - Terraform automation for GCP Cloud Run deployment
- **Comprehensive Testing** - Full test coverage with mocked dependencies (no API keys required)

## Project Structure

```
cloud-rag/
├── apps/
│   ├── frontend/                    # Frontend service (SSE streaming)
│   │   ├── handlers/
│   │   │   ├── __init__.py
│   │   │   └── routes.py           # Query endpoint, health checks
│   │   ├── app.py                  # FastAPI app
│   │   ├── config.py               # Service configuration
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   └── tests/                  # Comprehensive test suite
│   │
│   ├── ingestion/                  # Ingestion service (PDF upload & embedding)
│   │   ├── handlers/
│   │   │   ├── __init__.py
│   │   │   └── routes.py           # Ingest endpoint
│   │   ├── services/
│   │   │   └── pipeline.py         # PDF extraction, chunking, embeddings
│   │   ├── app.py                  # FastAPI app
│   │   ├── config.py               # Service configuration
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   └── tests/                  # Full test coverage
│   │
│   ├── retrieval/                  # Retrieval service (vector search)
│   │   ├── handlers/
│   │   │   └── routes.py           # Retrieve endpoint
│   │   ├── services/
│   │   │   └── pipeline.py         # Vector search, ranking, deduplication
│   │   ├── app.py
│   │   ├── config.py
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   └── tests/
│   │
│   └── synthesis/                  # Synthesis service (LLM generation)
│       ├── handlers/
│       │   └── routes.py           # Synthesize endpoint
│       ├── services/
│       │   └── pipeline.py         # Retrieval + LLM orchestration
│       ├── app.py
│       ├── config.py
│       ├── Dockerfile
│       ├── requirements.txt
│       └── tests/
│
├── common/                         # Shared code across services
│   ├── __init__.py
│   ├── config.py                  # Shared configuration
│   ├── models.py                  # Pydantic models (all services)
│   ├── metrics.py                 # Metrics collection
│   └── utils.py                   # Utility functions
│
├── terraform/                     # Infrastructure as Code
│   ├── main.tf
│   ├── services.tf                # Cloud Run services
│   ├── variables.tf
│   ├── outputs.tf
│   ├── monitoring.tf              # Cloud Logging & Monitoring
│   ├── networking.tf              # VPC & Firewall
│   ├── storage.tf                 # GCS buckets
│   ├── secrets.tf                 # Secret Manager
│   └── terraform.tfvars.example
│
├── Dockerfile                     # Root container setup
├── requirements.txt               # Root dependencies
└── README.md
```

## Quick Start - Local Development

### Prerequisites

- Python 3.11+
- OpenAI API key (from https://platform.openai.com)
- Pinecone API key (from https://pinecone.io)

### Setup

1. **Clone and install dependencies:**
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install all service dependencies
pip install -r requirements.txt
for dir in apps/ingestion apps/retrieval apps/synthesis apps/frontend; do
  pip install -r $dir/requirements.txt
done
```

2. **Set up environment variables:**
```bash
# Create .env files
for dir in apps/ingestion apps/retrieval apps/synthesis apps/frontend; do
  cat > $dir/.env << ENVFILE
ENVIRONMENT=development
OPENAI_API_KEY=your_openai_key_here
PINECONE_API_KEY=your_pinecone_key_here
ENVFILE
done

# Additional config for synthesis and frontend
echo "RETRIEVAL_SERVICE_URL=http://localhost:8001" >> apps/synthesis/.env
echo "SYNTHESIS_SERVICE_URL=http://localhost:8002" >> apps/frontend/.env
```

3. **Start all services in separate terminals:**

```bash
# Terminal 1: Ingestion (Port 8000)
cd apps/ingestion && uvicorn app:app --port 8000

# Terminal 2: Retrieval (Port 8001)
cd apps/retrieval && uvicorn app:app --port 8001

# Terminal 3: Synthesis (Port 8002)
cd apps/synthesis && uvicorn app:app --port 8002

# Terminal 4: Frontend (Port 8003)
cd apps/frontend && uvicorn app:app --port 8003
```

### Testing the System

**Health Checks:**
```bash
curl http://localhost:8000/api/v1/health
curl http://localhost:8001/api/v1/health
curl http://localhost:8002/api/v1/health
curl http://localhost:8003/api/v1/health
```

**Upload a Document:**
```bash
curl -X POST -F "file=@document.pdf" \
  http://localhost:8000/api/v1/ingest
```

**Query the System (SSE Streaming):**
```bash
curl -N -X POST http://localhost:8003/api/v1/query \
  -H 'Content-Type: application/json' \
  -d '{"query":"Your question here"}'
```

**Expected Response:**
```
event: answer
data: {"text":"Based on the documents..."}

event: citation
data: {"chunk_id":"...", "doc_id":"...", "page":1, "text_preview":"..."}

event: done
data: {"latency_ms":2500, "cost":0.025, "tokens":450}
```

### Run Tests

Each service has comprehensive tests with mocked dependencies:

```bash
# Test all services
for dir in apps/ingestion apps/retrieval apps/synthesis apps/frontend; do
  echo "Testing $dir..."
  (cd $dir && pytest tests/ -v)
done
```

## Service Endpoints

### Ingestion Service (Port 8000)
- **POST** `/api/v1/ingest` - Upload and process PDF documents
- **GET** `/api/v1/health` - Health check

### Retrieval Service (Port 8001)
- **POST** `/api/v1/retrieve` - Search for relevant chunks
- **GET** `/api/v1/health` - Health check

### Synthesis Service (Port 8002)
- **POST** `/api/v1/synthesize` - Generate LLM response with citations
- **GET** `/api/v1/health` - Health check

### Frontend Service (Port 8003)
- **POST** `/api/v1/query` - Streaming endpoint (SSE)
- **GET** `/api/v1/health` - Health check

## Deployment to GCP Cloud Run

### Prerequisites

- Google Cloud account with billing enabled
- Terraform installed
- gcloud CLI configured
- Docker installed

### Deploy

```bash
# Set your GCP project
export GCP_PROJECT_ID="your-project-id"
gcloud config set project $GCP_PROJECT_ID

# Build and push images
docker build -f apps/ingestion/Dockerfile -t gcr.io/$GCP_PROJECT_ID/rag-ingestion:latest .
docker build -f apps/retrieval/Dockerfile -t gcr.io/$GCP_PROJECT_ID/rag-retrieval:latest .
docker build -f apps/synthesis/Dockerfile -t gcr.io/$GCP_PROJECT_ID/rag-synthesis:latest .
docker build -f apps/frontend/Dockerfile -t gcr.io/$GCP_PROJECT_ID/rag-frontend:latest .

docker push gcr.io/$GCP_PROJECT_ID/rag-ingestion:latest
docker push gcr.io/$GCP_PROJECT_ID/rag-retrieval:latest
docker push gcr.io/$GCP_PROJECT_ID/rag-synthesis:latest
docker push gcr.io/$GCP_PROJECT_ID/rag-frontend:latest

# Deploy with Terraform
cd terraform
export TF_VAR_openai_api_key="your-openai-key"
export TF_VAR_pinecone_api_key="your-pinecone-key"
terraform apply -auto-approve
```

## Technology Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| API Framework | FastAPI 0.104 | Async REST APIs |
| Server | Uvicorn | ASGI server |
| Data Validation | Pydantic 2.5 | Type-safe request/response models |
| Vector Database | Pinecone | Semantic search over embeddings |
| LLM | OpenAI GPT-4 | Response generation |
| Embeddings | OpenAI Embeddings | Vector representations |
| Cloud Platform | Google Cloud Run | Serverless deployment |
| Infrastructure | Terraform | Infrastructure as Code |
| Containerization | Docker | Service packaging |
| Testing | pytest | Unit and integration tests |
| HTTP Client | httpx | Async service-to-service calls |

## Key Implementation Details

### Service-to-Service Communication
Services communicate via REST APIs using httpx for async HTTP requests:
```python
async with httpx.AsyncClient() as client:
    response = await client.post(
        f"{settings.retrieval_service_url}/api/v1/retrieve",
        json=retrieval_request.model_dump(),
        timeout=30.0
    )
```

### Type Safety
All inter-service communication uses Pydantic models:
- `FrontendRequest` - User query input
- `SynthesisRequest` - Request to synthesis service
- `RetrievalRequest` - Request to retrieval service
- `RetrievalResult` - Chunks returned from vector search
- `SynthesisResponse` - Final response with citations

### Cost Tracking
Real-time cost calculation for all operations:
- Embedding costs (OpenAI API pricing)
- Token usage (prompt + completion)
- Service-level cost estimation

### Error Handling
Comprehensive error handling with structured logging:
- Validation errors (400)
- Resource not found (404)
- Service errors (500)
- Timeout handling across service boundaries

## Configuration

Each service reads configuration from environment variables using Pydantic Settings:

```python
class IngestionSettings(CommonSettings):
    embedding_batch_size: int = 20
    chunk_size: int = 512
    chunk_overlap: int = 100
    max_file_size_mb: int = 100
```

Configuration can be overridden per environment using `.env` files or environment variables.

## Monitoring and Logging

Services send structured logs to Google Cloud Logging:
- Request/response logging
- Error tracking with stack traces
- Performance metrics (latency, tokens, costs)
- Service health status

Configure logging in `common/config.py` or individual service configs.

## Troubleshooting

### Services Not Connecting
- Verify all 4 services are running on correct ports (8000-8003)
- Check `.env` files have correct `SERVICE_URL` values
- Confirm network connectivity between services

### Pinecone Errors
- Verify `PINECONE_API_KEY` is correct
- Check index name matches in configuration
- Ensure Pinecone index is properly initialized

### OpenAI Errors
- Verify `OPENAI_API_KEY` is valid and has sufficient quota
- Check API rate limits
- Ensure correct model names in configuration

### Vector Dimension Mismatch
- Verify embeddings model matches Pinecone index dimension
- Default: text-embedding-3-small (1536 dimensions)
- Recreate Pinecone index if models change

## Contributing

Contributions and improvements are welcome.

## License

MIT License
