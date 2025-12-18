# Modular GCP RAG Architecture

## System Architecture

The system is now split into **4 independently deployable FastAPI services**:

```
┌─────────────┐
│  Frontend   │ (Port 8003) - SSE streaming UI
└──────┬──────┘
       │
       ├─── POST /api/v1/query
       │
       ▼
┌─────────────────────┐
│    Synthesis        │ (Port 8002)
│  (LLM Response Gen) │
└──────┬──────────────┘
       │
       ├─── REST: Call Retrieval Service
       │
       ▼
┌──────────────────────┐       ┌─────────────────┐
│     Retrieval        │───────▶│    Pinecone     │
│  (Vector Search)     │       │   (Vector DB)   │
└──────────────────────┘       └─────────────────┘
       │
       └─── File: Upload PDF
           │
           ▼
       ┌──────────────────┐
       │    Ingestion     │ (Port 8000)
       │ (PDF → Vectors)  │
       └──────────────────┘
```

## Services Overview

### 1. **Ingestion Service** (Port 8000)
Handles PDF document upload, text extraction, chunking, embedding, and vector storage.

**Endpoint**: `POST /api/v1/ingest`
- Accepts multipart file upload
- Extracts text using PyPDF2
- Chunks text (configurable size + overlap)
- Generates embeddings (batched, 20 texts/batch)
- Stores vectors in Pinecone with metadata

**Classes**:
- `PDFExtractor` - Text extraction
- `EmbeddingService` - OpenAI embeddings (batched)
- `VectorStoreService` - Pinecone storage
- `IngestionPipeline` - Orchestration

### 2. **Retrieval Service** (Port 8001)
Searches vectors, ranks results, and returns relevant chunks.

**Endpoint**: `POST /api/v1/retrieve`
- Accepts query string
- Embeds query using OpenAI
- Searches Pinecone (with user_id filtering)
- Deduplicates results
- Ranks by relevance
- Returns `RetrievalResult` with chunks

**Classes**:
- `EmbeddingService` - Query embedding
- `VectorSearchService` - Pinecone queries
- `RankingService` - Deduplication & ranking
- `RetrievalPipeline` - Orchestration

### 3. **Synthesis Service** (Port 8002)
Calls Retrieval service, generates LLM response with citations.

**Endpoint**: `POST /api/v1/synthesize`
- Calls Retrieval service via REST (httpx)
- Builds system and user prompts
- Calls OpenAI chat completions
- Generates response with citations
- Returns `SynthesisResponse`

**Classes**:
- `LLMService` - OpenAI chat API
- `PromptBuilder` - Prompt construction
- `SynthesisPipeline` - Retrieval + LLM orchestration

**Inter-Service Communication**:
```python
async with httpx.AsyncClient() as client:
    response = await client.post(
        f"{settings.retrieval_service_url}/api/v1/retrieve",
        json=retrieval_request.model_dump(),
        timeout=30.0
    )
```

### 4. **Frontend Service** (Port 8003)
Lightweight API for SSE streaming responses.

**Endpoint**: `POST /api/v1/query`
- Accepts query string
- Calls Synthesis service via httpx
- Returns Server-Sent Events (SSE) stream:
  - `answer` - Response text
  - `citation` - Citation metadata
  - `done` - Final metadata (latency, tokens, cost)
  - `error` - Error messages

## Running Locally

Each service runs independently. Use 4 terminals:

**Terminal 1 - Ingestion**:
```bash
cd apps/ingestion
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your API keys
uvicorn app:app --reload --port 8000
```

**Terminal 2 - Retrieval**:
```bash
cd apps/retrieval
pip install -r requirements.txt
cp .env.example .env
uvicorn app:app --reload --port 8001
```

**Terminal 3 - Synthesis**:
```bash
cd apps/synthesis
pip install -r requirements.txt
cp .env.example .env
# Set RETRIEVAL_SERVICE_URL=http://localhost:8001
uvicorn app:app --reload --port 8002
```

**Terminal 4 - Frontend**:
```bash
cd apps/frontend
pip install -r requirements.txt
cp .env.example .env
# Set SYNTHESIS_SERVICE_URL=http://localhost:8002
uvicorn app:app --reload --port 8003
```

## Testing

Each app has comprehensive unit tests with mocked dependencies:

```bash
# Ingestion tests
cd apps/ingestion && pytest tests/ -v

# Retrieval tests
cd apps/retrieval && pytest tests/ -v

# Synthesis tests
cd apps/synthesis && pytest tests/ -v
```

**Test Structure** (`conftest.py`):
- Mocked OpenAI client
- Mocked Pinecone index
- Mocked httpx for inter-service calls
- Sample fixtures for all request types

## Configuration

### Environment Variables

**Common (all services)**:
```env
OPENAI_API_KEY=sk-...
PINECONE_API_KEY=pk-...
GCP_PROJECT_ID=your-project
GCS_BUCKET_NAME=your-bucket
```

**Ingestion** (`apps/ingestion/.env`):
```env
EMBEDDING_BATCH_SIZE=20
PINECONE_INDEX_NAME=portfolio-rag
```

**Retrieval** (`apps/retrieval/.env`):
```env
QUERY_TOP_K=10
PINECONE_INDEX_NAME=portfolio-rag
```

**Synthesis** (`apps/synthesis/.env`):
```env
RETRIEVAL_SERVICE_URL=http://retrieval:8001
LLM_TEMPERATURE=0.7
LLM_MAX_TOKENS=1000
MAX_CONTEXT_TOKENS=2000
```

**Frontend** (`apps/frontend/.env`):
```env
SYNTHESIS_SERVICE_URL=http://synthesis:8002
STREAMING_BUFFER_SIZE=100
```

## Deployment on GCP

### 1. Build Docker Images
```bash
export PROJECT_ID=your-project-id

docker build -t gcr.io/${PROJECT_ID}/rag-ingestion:latest apps/ingestion/
docker build -t gcr.io/${PROJECT_ID}/rag-retrieval:latest apps/retrieval/
docker build -t gcr.io/${PROJECT_ID}/rag-synthesis:latest apps/synthesis/
docker build -t gcr.io/${PROJECT_ID}/rag-frontend:latest apps/frontend/

# Push to Container Registry
docker push gcr.io/${PROJECT_ID}/rag-ingestion:latest
docker push gcr.io/${PROJECT_ID}/rag-retrieval:latest
docker push gcr.io/${PROJECT_ID}/rag-synthesis:latest
docker push gcr.io/${PROJECT_ID}/rag-frontend:latest
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
```

### 3. Verify Deployment
```bash
# Get service URLs
terraform output ingestion_url
terraform output retrieval_url
terraform output synthesis_url
terraform output frontend_url

# Test ingestion
curl -X POST https://rag-ingestion-xxx.a.run.app/api/v1/health

# Test frontend
curl https://rag-frontend-xxx.a.run.app/api/v1/health
```

## Data Models (Pydantic)

All service-to-service communication uses strongly-typed models:

**Ingestion**:
```python
class IngestRequest(BaseModel):
    file: UploadFile
    user_id: str = "default"

class IngestResponse(BaseModel):
    num_chunks: int
    num_tokens: int
    cost_estimate: float
```

**Retrieval**:
```python
class RetrievalRequest(BaseModel):
    query: str
    user_id: str = "default"
    top_k: int = 10

class RetrievalResult(BaseModel):
    query: str
    chunks: List[RetrievedChunk]
    retrieval_latency_ms: float
    num_chunks_searched: int
```

**Synthesis**:
```python
class SynthesisRequest(BaseModel):
    query: str
    user_id: str = "default"
    retrieval_result: Optional[RetrievalResult] = None

class SynthesisResponse(BaseModel):
    answer: str
    citations: List[Citation]
    synthesis_latency_ms: float
    tokens_used: int
    cost_estimate: float
```

## Metrics & Monitoring

All services record metrics as JSON logs:

```json
{
  "query_id": "abc-123-def",
  "service": "synthesis",
  "latency_ms": 1250,
  "success": true,
  "tokens_used": 350,
  "cost_estimate": 0.015,
  "timestamp": "2024-01-15T10:30:45Z"
}
```

**Metrics per service**:
- **Ingestion**: `latency_ms`, `num_chunks`, `tokens_used`, `cost_estimate`
- **Retrieval**: `latency_ms`, `num_results`, `search_time_ms`
- **Synthesis**: `latency_ms`, `tokens_used`, `cost_estimate`, `citations_count`

## Future Enhancements

1. **Advanced Retrieval**
   - Re-ranking with cross-encoders
   - Semantic filtering
   - Hybrid search (keyword + vector)

2. **Multi-Tenancy**
   - User-specific namespaces in Pinecone
   - Cost tracking per user
   - Rate limiting per user

3. **Caching**
   - Redis cache for embeddings
   - Query result caching
   - TTL-based expiration

4. **Monitoring**
   - Prometheus metrics
   - Distributed tracing (Jaeger)
   - Cloud Trace integration
   - Custom dashboards in Cloud Console

5. **Scaling**
   - Horizontal Pod Autoscaler (GKE)
   - Custom metrics for autoscaling
   - Request queuing with Pub/Sub

## Architecture Benefits

✅ **Independent Deployment**: Each service deploys separately
✅ **Testability**: All dependencies mockable
✅ **Scalability**: Per-service resource allocation
✅ **Modularity**: Clear separation of concerns
✅ **Type Safety**: Pydantic models for all boundaries
✅ **Cost Efficient**: Pay only for what you use on Cloud Run
✅ **Maintainability**: Smaller, focused codebases
✅ **Extensibility**: Easy to add new services
