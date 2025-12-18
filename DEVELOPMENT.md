# Development Notes & Implementation Details

## Architecture Decisions

### 1. Streaming with SSE (Server-Sent Events)

**Why SSE instead of WebSockets?**
- Simpler to implement and debug
- Works with standard HTTP proxies and load balancers
- Native browser support with EventSource API
- Sufficient for unidirectional streaming (server → client)

**Implementation:**
```python
# apps/frontend/handlers/routes.py - Frontend service
@router.post("/api/v1/query")
async def stream_rag_response(...) -> StreamingResponse:
    async def event_generator():
        async for chunk in synthesis_client.stream_answer(...):
            yield f"event: {chunk['event']}\ndata: {json.dumps(chunk['data'])}\n\n"
    return StreamingResponse(event_generator(), media_type="text/event-stream")
```

### 2. Embedding Batching for Cost Optimization

**Problem:** Embedding API calls have overhead; single texts = more calls

**Solution:** Batch embeddings in groups (default: 20)

**Cost Impact:**
- Unbatched: 100 PDFs × avg 50 chunks = 5000 API calls
- Batched (20): 5000 ÷ 20 = 250 API calls (~95% reduction)

**Implementation:**
```python
# apps/ingestion/services/pipeline.py - Ingestion service
for i in range(0, len(texts), self.batch_size):
    batch = texts[i : i + self.batch_size]
    batch_embeddings = self._embed_batch(batch)
```

### 3. Token Counting Without tiktoken

**Approach:** Simple character-based estimation (1 token ≈ 4 chars)

**Why not tiktoken?**
- Extra dependency increases image size
- Estimation is "good enough" for cost tracking
- Can upgrade to tiktoken later if needed

**Usage:**
```python
from common.utils import estimate_tokens
tokens = estimate_tokens(text)  # Rough estimate
cost = estimate_embedding_cost(tokens)  # Calculate cost
```

**Accuracy:** ±10-15% error, acceptable for budget tracking

### 4. Vector Search with Multi-Tenancy

**Implementation:** Pinecone metadata filtering in Retrieval service

```python
# apps/retrieval/services/pipeline.py - Retrieval service
filter_dict = {"user_id": {"$eq": user_id}}
results = self.index.query(
    vector=query_embedding,
    top_k=top_k,
    filter=filter_dict  # User-level isolation
)
```

**Currently single-tenant but extensible:** User ID defaults to "default" but field is in metadata for future multi-tenancy.

### 5. Context Window Management

**Problem:** Unlimited context = high costs and model degradation

**Solution:** Token-budgeted context assembly in Synthesis service

```python
# apps/synthesis/services/pipeline.py - Synthesis service
def assemble_context(chunks, max_tokens=2000):
    for chunk in chunks:
        chunk_tokens = estimate_tokens(chunk["text"])
        if current_tokens + chunk_tokens <= max_tokens:
            # Add chunk
```

**Default:** 2000 tokens max context, tunable via `CONTEXT_BUDGET_TOKENS`

### 6. Metrics Collection Architecture

**Design:**
- Per-query metrics captured immediately after response
- Singleton `MetricsCollector` instance tracks all queries
- Aggregated metrics (p50, p99, avg) computed on shutdown
- Shared via `common.metrics` module

**Logged as JSON for easy parsing:**
```json
{
  "event": "query_completed",
  "metrics": {
    "query_id": "uuid",
    "latency_ms": 1234.5,
    "total_cost": 0.021
  }
}
```

### 7. Service-to-Service Communication

**Pattern:** REST API calls via httpx in Synthesis and Frontend services

```python
# apps/synthesis/services/pipeline.py - Calls Retrieval service
async def get_context(query: str):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://retrieval:8001/api/v1/retrieve",
            json={"query": query, "top_k": 5}
        )
    return response.json()
```

**Testability:** Mocked via conftest.py, no actual service calls needed

## Configuration Management

### Pydantic Settings

Using `pydantic-settings` for environment-based configuration in all 4 services:

```python
# apps/[ingestion|retrieval|synthesis|frontend]/config.py
class Settings(BaseSettings):
    openai_api_key: str
    pinecone_api_key: str
    # ... fields auto-loaded from .env or environment

    class Config:
        env_file = ".env"
        case_sensitive = False

@lru_cache()
def get_settings() -> Settings:
    return Settings()  # Cached singleton
```

**Advantages:**
- Type validation (Pydantic)
- Environment variable support
- Cached singleton pattern
- Easy testing (can override settings in conftest.py)

**Shared Settings:** Common base settings in `common/config.py`, service-specific overrides in each app's `config.py`

## Error Handling

### Graceful Degradation

**Empty Context Handling:**
```python
if not has_context:
    response = "I don't have information about that in the provided documents"
    # Don't call LLM, save cost
```

**API Error Fallbacks:**
```python
try:
    results = self.index.query(...)
except Exception as e:
    logger.error(f"Pinecone error: {e}")
    raise HTTPException(status_code=500, detail=str(e))
```

### Logging Strategy

- **INFO level:** Query events, component status
- **ERROR level:** API failures, configuration issues
- **Structured JSON:** All metrics logged as JSON for parsing

## Testing Strategy

### Unit & Integration Tests

Each of the 4 services has comprehensive test suites:

1. **Unit:** Test individual components (retriever, synthesizer, pipeline logic)
2. **Integration:** Test service's own endpoints with mocked dependencies
3. **No API Keys Needed:** All external calls (OpenAI, Pinecone, httpx) mocked in conftest.py

### Running Tests

```bash
# Test each service independently
cd apps/ingestion && pytest tests/ -v
cd apps/retrieval && pytest tests/ -v
cd apps/synthesis && pytest tests/ -v
cd apps/frontend && pytest tests/ -v
```

### Test Fixtures (conftest.py pattern)

```python
# apps/[service]/tests/conftest.py
@pytest.fixture
def mock_openai(monkeypatch):
    def mock_create(*args, **kwargs):
        return MagicMock(choices=[MagicMock(message=MagicMock(content="Test response"))])
    monkeypatch.setattr("openai.ChatCompletion.create", mock_create)

@pytest.fixture
def mock_pinecone(monkeypatch):
    def mock_query(*args, **kwargs):
        return {"matches": [...]}  # Sample results
    monkeypatch.setattr("pinecone.Index.query", mock_query)
```

### Coverage

- All services target >80% code coverage
- Critical paths (ingestion, retrieval, synthesis) have >90% coverage
- Integration points mocked for reproducible tests

## Performance Considerations

### Latency Breakdown (typical query)

| Stage | Time |
|-------|------|
| Embedding query | 100-200ms |
| Pinecone search | 200-500ms |
| Context assembly | 50-100ms |
| LLM streaming | 1000-2000ms |
| **Total** | **1500-2800ms** |

### Memory Usage

- FastAPI app: ~200MB base
- Per request: ~50-100MB (context + streaming buffer)
- Cloud Run allocation: 2GB (comfortable for concurrent requests)

### Scaling

- Cloud Run auto-scales 0 → 10 instances (configurable)
- Each instance handles ~5-10 concurrent requests
- Total capacity: 50-100 concurrent queries

## Security Considerations

### Current Implementation (Development)

- ✅ API keys stored in Secret Manager
- ✅ GCS bucket with versioning
- ✅ Service account with minimal IAM
- ⚠️ **No authentication** (current)
- ⚠️ **Public endpoint** (currently)

### For Production

1. **Add Authentication:**
   ```hcl
   # terraform/cloud_run.tf
   # Remove or restrict:
   # resource "google_cloud_run_service_iam_member" "public"
   ```

2. **Use API Keys or OAuth:**
   - Implement in FastAPI middleware
   - Store in Secret Manager
   - Validate per request

3. **Rate Limiting:**
   - Cloud Armor or FastAPI middleware
   - Per-user/API-key quotas

4. **VPC-SC (VPC Service Controls):**
   - Restrict egress to OpenAI/Pinecone
   - Private GCP network connections

## Cost Optimization Techniques

### 1. Early Exit for Empty Context
```python
if not has_context:
    return empty_response  # Skip expensive LLM call
```

### 2. Embedding Batching
```python
embeddings = client.embed_texts(texts, use_batch=True)  # 20 per batch
```

### 3. Context Windowing
```python
max_tokens = 2000  # Limit input to reduce LLM cost
```

### 4. Model Selection
```python
# Use cheaper embedding model
embedding_model = "text-embedding-3-small"  # $0.02/1M vs $0.13/1M for large

# Monitor LLM usage; could switch to GPT-3.5-turbo if sufficient
```

### 5. Query Caching (Future)
```python
# Redis cache for identical/similar queries
# Estimated savings: 20-30% on repeated queries
```

## Pinecone Integration Notes

### Index Setup

```bash
# Create index manually in Pinecone console:
# - Name: rag-index
# - Dimension: 1536 (for text-embedding-3-small)
# - Metric: cosine
# - Regions: us-west1-gcp (or your region)
```

### Metadata Filtering

Vectors stored with metadata:
```python
{
    "id": "doc_id_chunk_0",
    "values": [0.1, 0.2, ...],  # 1536 dimensions
    "metadata": {
        "doc_id": "uuid",
        "source_url": "gs://...",
        "page": 1,
        "chunk_index": 0,
        "text": "full chunk text",
        "user_id": "default",
        "created_at": timestamp
    }
}
```

### Query Performance

- Typical query: 200-500ms
- Depends on index size and number of results (top_k)
- Can optimize with different metric types

## OpenAI API Usage

### Embedding Model Choice

```
text-embedding-3-small
- 1536 dimensions
- Fast, cheap (~$0.02/1M tokens)
- Good for general use

text-embedding-3-large
- 3072 dimensions
- Slower, more expensive (~$0.13/1M)
- Better quality if needed
```

### LLM Model Choice

```
gpt-4-turbo-preview
- $10/$30 per 1M (in/out)
- Best quality, highest cost

gpt-3.5-turbo
- $0.5/$1.5 per 1M
- Faster, cheaper, sufficient for many tasks
```

### Streaming Implementation

```python
async with self.client.messages.stream(...) as stream:
    async for text in stream.text_stream:
        yield {"event": "token", "data": text}
```

- Uses asyncio for non-blocking I/O
- Yields tokens as they arrive
- Reduces time-to-first-token from user perspective

## Deployment Notes

### Terraform Workflow

```bash
terraform init     # Download providers
terraform plan     # Preview changes
terraform apply    # Deploy resources
terraform destroy  # Clean up (costs)
```

### Environment Variables for Deployment

```bash
export GCP_PROJECT_ID=my-project
export TF_VAR_openai_api_key=sk-...
export TF_VAR_pinecone_api_key=...

terraform apply
```

### Container Image Building

```dockerfile
# Dockerfile strategy:
# 1. Use slim Python 3.11 base (smaller size)
# 2. Install system deps (gcc for compilation)
# 3. Install Python packages
# 4. Copy app code
# 5. Health check for readiness probes
```

### Cold Start Performance

- Cloud Run cold start: ~5-10 seconds
- Warm start: <1 second
- Mitigated by min_instances or traffic spike handling

## Monitoring & Observability

### Metrics Captured Per Query

1. **Latency**: Total query time
2. **Retrieval**: Chunks retrieved, citations used
3. **Cost**: Embedding + LLM costs
4. **Content**: Empty context detection
5. **Tokens**: Input/output token usage

### Log Aggregation

Local: stdout as JSON
Production: Cloud Logging (automatically parsed)

```bash
# View logs
gcloud run logs read rag-api --region=us-central1 --limit=50
```

### Alerts Configured

1. **High Error Rate** (5%+)
2. **High Latency** (p99 > 10s)

## Future Enhancement Ideas

### High Priority
- [ ] Authentication (API keys)
- [ ] Rate limiting
- [ ] Query caching (Redis)
- [ ] Cross-encoder re-ranking

### Medium Priority
- [ ] Batch ingestion endpoint
- [ ] Document versioning
- [ ] User feedback loop
- [ ] Cost anomaly alerts

### Lower Priority
- [ ] Vertex AI Matching Engine support
- [ ] Ray for distributed embeddings
- [ ] Advanced monitoring dashboards
- [ ] Query result ranking

## Debugging Tips

### "No chunks retrieved"
1. Check Pinecone index has vectors
2. Verify document was ingested successfully
3. Try increasing `query_top_k`
4. Check user_id filter logic

### "API rate limited"
1. Check API key quotas
2. Verify batch sizing (not too large)
3. Add exponential backoff retry logic

### High costs
1. Review tokens in metrics logs
2. Reduce `CONTEXT_BUDGET_TOKENS`
3. Switch to cheaper embedding model
4. Limit `query_top_k`

### Development Hang
1. Check event loop: `asyncio` might be blocking
2. Use `run_in_executor` for blocking I/O
3. Check Cloud Run logs for timeouts

---

**Last Updated:** January 2025
**Status:** Pre-production / Testing
