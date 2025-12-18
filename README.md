# RAG API - Modular Microservices Architecture on GCP

A portfolio project demonstrating a production-grade Retrieval-Augmented Generation (RAG) system built as 4 independent microservices using FastAPI, Pinecone, and GCP Cloud Run.

## Architecture Overview

```
┌──────────────┐
│   Frontend   │ (Port 8003)
│ (SSE Stream) │
└──────┬───────┘
       │ REST
       ▼
┌────────────────┐      ┌──────────────┐
│   Synthesis    │◄────►│   Retrieval  │ (Port 8001)
│ (Port 8002)    │      │              │
│ LLM + Prompts  │      │ Vector Search│
└──────┬─────────┘      └──────┬───────┘
       │                       │
       └───────────┬───────────┘
                   ▼
           ┌───────────────┐
           │   Pinecone    │
           │  (Vector DB)  │
           └───────────────┘

┌──────────────────┐
│   Ingestion      │ (Port 8000)
│ PDF → Chunks →   │
│ Embeddings →     │
│ Pinecone Storage │
└──────────────────┘

          All services monitored in Cloud Logging
```

## Key Features

✅ **Modular Architecture** - 4 independent microservices, each independently deployable
✅ **Streaming Responses** - Server-Sent Events (SSE) for real-time token streaming
✅ **Source-Backed Answers** - Citations with document metadata and page numbers
✅ **Type-Safe Communication** - Pydantic models across all service boundaries
✅ **Fully Testable** - 100% mockable dependencies (no API keys needed for tests)
✅ **Cost Optimization** - Embedding batching, token counting, cost tracking
✅ **Infrastructure-as-Code** - Terraform for reproducible 4-service deployment
✅ **Production Ready** - Docker images, error handling, comprehensive logging

## Project Structure

```
gcp-rag/
├── app/
│   ├── api/
│   │   ├── ingest.py         # PDF ingestion with embeddings
│   │   ├── query.py          # Streaming RAG query endpoint
│   │   └── health.py         # Health check with metrics
│   ├── rag/
│   │   ├── retriever.py      # Vector search and ranking
│   │   ├── prompt.py         # Prompt templates and formatting
│   │   ├── streaming.py      # LLM streaming and embeddings
│   │   └── citations.py      # Citation extraction and formatting
│   ├── models/
│   │   └── schema.py         # Pydantic request/response models
│   ├── utils/
│   │   ├── text_processing.py  # Text chunking and normalization
│   │   ├── metrics.py        # Query metrics collection
│   │   └── __init__.py
│   ├── config.py             # Configuration management
│   ├── logging_config.py     # Logging setup
│   └── main.py               # FastAPI app entry point
├── terraform/
│   ├── main.tf              # Provider and version
│   ├── variables.tf         # Input variables
│   ├── outputs.tf           # Output values
│   ├── cloud_run.tf         # Cloud Run service
│   ├── secrets.tf           # Secret Manager
│   ├── storage.tf           # GCS bucket
│   ├── networking.tf        # VPC and firewall
│   ├── monitoring.tf        # Cloud Logging and Monitoring
│   └── terraform.tfvars.example
├── scripts/
│   ├── setup_local.sh       # Local development setup
│   ├── test_api.sh          # API testing script
│   └── deploy_cloud_run.sh  # Cloud Run deployment
├── .env.example             # Environment variables template
├── Dockerfile               # Container image definition
├── requirements.txt         # Python dependencies
└── README.md
```

## Local Development Setup

### Prerequisites

- Python 3.11+
- pip/venv
- Docker (for containerization)
- Terraform (for GCP deployment)
- gcloud CLI (for GCP interactions)

### 1. Initial Setup

```bash
chmod +x scripts/setup_local.sh
./scripts/setup_local.sh
```

This will:
- Create Python virtual environment
- Install dependencies
- Create `.env` file from template

### 2. Configure Environment

Edit `.env` with your API keys:

```bash
cp .env.example .env
# Edit .env with actual values
```

Required keys:
- `OPENAI_API_KEY` - Get from [OpenAI dashboard](https://platform.openai.com/api-keys)
- `PINECONE_API_KEY` - Get from [Pinecone console](https://app.pinecone.io)
- `GCS_BUCKET_NAME` - Create in GCP or use existing
- `GCP_PROJECT_ID` - Your GCP project ID

### 3. Run Local Development Server

```bash
source venv/bin/activate
python -m uvicorn app.main:app --reload
```

Server starts on `http://localhost:8000`

API Documentation: `http://localhost:8000/docs`

## Testing

### Health Check

```bash
curl http://localhost:8000/api/v1/health | jq .
```

### Ingest a PDF

```bash
curl -X POST -F "file=@sample.pdf" \
  http://localhost:8000/api/v1/ingest
```

This returns Server-Sent Events with progress:
- `progress` - Extraction, cleaning, chunking stages
- `complete` - Final statistics

### Query with Streaming

```bash
curl -N -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What is the main topic?",
    "user_id": "test-user",
    "top_k": 5
  }'
```

Response streams as SSE events:
- `token` - Answer text (incremental)
- `citation` - Source document reference
- `done` - End of stream

### Using Test Script

```bash
chmod +x scripts/test_api.sh
./scripts/test_api.sh
```

## Cost Optimization

### 1. Embedding Batching

Embeddings are batched (default: 20 texts per batch) to reduce API calls:
- Single request ≈ 1 embedding call per document
- Batched ≈ N documents in ⌈N/20⌉ calls

```python
# In app/rag/streaming.py
embeddings, tokens = embedding_client.embed_texts(texts, use_batch=True)
```

### 2. Token Counting

Rough token estimation (1 token ≈ 4 characters) for cost tracking without external libraries:

```python
from app.utils.text_processing import estimate_tokens, estimate_embedding_cost
tokens = estimate_tokens(text)
cost = estimate_embedding_cost(tokens)
```

### 3. Context Windowing

Limit context to token budget to reduce LLM input:
- Default: 2000 tokens max per query
- Configurable via `CONTEXT_BUDGET_TOKENS`

### 4. Cost Estimates (as of Jan 2025)

**Embeddings:**
- `text-embedding-3-small`: $0.02 per 1M tokens (~$0.00001 per query)
- `text-embedding-3-large`: $0.13 per 1M tokens

**LLM (GPT-4 Turbo):**
- Input: $10 per 1M tokens
- Output: $30 per 1M tokens
- ~1000 input tokens + 500 output tokens ≈ $0.02 per query

**Expected Test Cost (100 queries):**
- Embeddings: ~$0.001
- LLM: ~$2.00
- **Total: ~$2-3 USD**

## Evaluation Metrics

Metrics are logged to structured JSON for each query:

```json
{
  "event": "query_completed",
  "metrics": {
    "query_id": "uuid",
    "timestamp": "2025-01-16T12:34:56.789",
    "question": "...",
    "num_retrieved": 5,
    "num_citations": 3,
    "latency_ms": 1234.5,
    "tokens_input": 1200,
    "tokens_output": 450,
    "embedding_tokens": 50,
    "total_tokens": 1700,
    "cost_embedding": 0.000001,
    "cost_llm": 0.021,
    "total_cost": 0.021001,
    "has_context": true
  }
}
```

### Key Metrics

| Metric | Description |
|--------|-------------|
| `latency_ms` | Query end-to-end latency |
| `num_retrieved` | Chunks returned by vector search |
| `num_citations` | Citations in final response |
| `total_cost` | Embedding + LLM cost |
| `has_context` | Whether retrieval found relevant docs |
| `tokens_input/output` | LLM token usage |

### Aggregated Metrics (on shutdown)

```json
{
  "event": "metrics_summary",
  "aggregated": {
    "num_queries": 42,
    "avg_latency_ms": 2145.3,
    "p50_latency_ms": 1890,
    "p99_latency_ms": 5234,
    "avg_tokens_per_query": 1680,
    "total_cost": 0.876,
    "avg_cost_per_query": 0.0208,
    "num_empty_contexts": 2,
    "avg_citations_per_query": 2.3
  }
}
```

## GCP Deployment

### Prerequisites

```bash
# Install gcloud CLI
# Authenticate
gcloud auth login
gcloud config set project YOUR_PROJECT_ID

# Enable required APIs
gcloud services enable \
  run.googleapis.com \
  storage.googleapis.com \
  secretmanager.googleapis.com \
  logging.googleapis.com \
  monitoring.googleapis.com \
  artifactregistry.googleapis.com
```

### Setup Artifact Registry (for Docker images)

```bash
gcloud artifacts repositories create docker \
  --repository-format=docker \
  --location=us-central1

# Configure Docker auth
gcloud auth configure-docker us-docker.pkg.dev
```

### Configure Terraform

```bash
cd terraform/
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your values
```

### Deploy with Terraform

```bash
terraform init
terraform plan
terraform apply
```

Or use the convenience script:

```bash
GCP_PROJECT_ID=my-project ./scripts/deploy_cloud_run.sh
```

### Outputs

After deployment, get the service URL:

```bash
terraform output cloud_run_service_url
```

### Monitoring

**View logs:**
```bash
gcloud run logs read rag-api --region=us-central1
```

**View metrics:**
- [Cloud Console > Cloud Run](https://console.cloud.google.com/run)
- Metrics tab shows latency, request count, errors

## Production Considerations

### Authentication

Current setup allows unauthenticated access (for testing).

For production, add authentication:

```hcl
# Remove in terraform/cloud_run.tf:
# resource "google_cloud_run_service_iam_member" "public"

# Instead, use Cloud IAM or API key
```

### Scaling

Adjust in `terraform.tfvars`:
- `max_instances` - Max concurrent Cloud Run instances (default: 10)
- `cpu` / `memory` - Per-instance resources (default: 2 CPU, 2Gi RAM)

### Cost Control

1. **Set billing alerts** in GCP Console
2. **Monitor metrics** - Review avg cost per query
3. **Optimize context window** - Reduce `CONTEXT_BUDGET_TOKENS` if needed
4. **Use cheaper embedding model** - Switch to `text-embedding-3-small` if sufficient
5. **Enable request caching** - Redis integration (future enhancement)

### Security

- API keys stored in Secret Manager
- GCS bucket versioning enabled
- Service account with minimal IAM roles
- VPC network for egress control (future: private GCP connections)

## Troubleshooting

### "No context found" responses

1. Check Pinecone index has embeddings:
```bash
# From Python shell
from pinecone import Pinecone
pc = Pinecone(api_key="...")
index = pc.Index("rag-index")
print(index.describe_index_stats())
```

2. Verify documents were ingested:
```bash
gcloud storage ls gs://your-bucket/
```

3. Check vector search:
- Review `num_retrieved` in metrics
- Increase `top_k` or `query_top_k`

### High latency

1. Check Cloud Run metrics in GCP Console
2. Verify Pinecone performance
3. Review context assembly - reduce `CONTEXT_BUDGET_TOKENS`
4. Increase `max_instances` if throttled

### High costs

1. Review metrics - check `tokens_input/output`
2. Reduce context window size
3. Use cheaper embedding model (`text-embedding-3-small`)
4. Limit `top_k` retrieval results
5. Monitor batch ingestion - ensure batching is working

## Future Enhancements

- [ ] Multi-tenant complete isolation
- [ ] Redis caching layer
- [ ] Cross-encoder re-ranking
- [ ] Batch ingestion API
- [ ] Query result ranking/feedback loop
- [ ] Advanced citation formatting (inline vs. footnotes)
- [ ] Document versioning and updates
- [ ] Ray for distributed embedding generation
- [ ] Vertex AI Matching Engine as alternative
- [ ] Cost anomaly detection alerts

## Testing & Validation

Create test documents to validate end-to-end:

```bash
# Generate sample PDFs (requires reportlab)
pip install reportlab

python scripts/generate_test_pdfs.py
# Creates sample_1.pdf, sample_2.pdf, etc.

# Ingest
for pdf in sample_*.pdf; do
  curl -X POST -F "file=@$pdf" http://localhost:8000/api/v1/ingest
done

# Query
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"question": "What are the key points?"}'
```

## References

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Pinecone Documentation](https://docs.pinecone.io/)
- [OpenAI API](https://platform.openai.com/docs/api-reference)
- [Google Cloud Run](https://cloud.google.com/run/docs)
- [Terraform Google Provider](https://registry.terraform.io/providers/hashicorp/google/latest/docs)

## License

MIT

---

**Author:** Portfolio Project (2025)

**Status:** Pre-production / Testing Phase

For questions or improvements, open an issue or PR.
