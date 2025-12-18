# Getting Started Checklist

Complete these steps to get your RAG API running.

## Phase 1: Prerequisites ✅

- [ ] Python 3.11+ installed (`python --version`)
- [ ] pip available (`pip --version`)
- [ ] OpenAI account with API key (https://platform.openai.com)
- [ ] Pinecone account with API key (https://pinecone.io)
- [ ] GCP account (for later deployment)

## Phase 2: Local Development Setup 🚀

### Step 1: Initialize Repository
```bash
cd /home/zac/gcp-rag
ls -la apps/  # Verify 4 services present: ingestion, retrieval, synthesis, frontend
ls -la common/  # Verify shared library
```
- [ ] All 4 service directories present
- [ ] common/ directory present with models.py, config.py, metrics.py, utils.py

### Step 2: Setup Python Environment (Ingestion Service)
```bash
cd apps/ingestion
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```
- [ ] Virtual environment created
- [ ] Dependencies installed
- [ ] Activation script works

### Step 3: Configure Environment (Ingestion)
```bash
cp .env.example .env
nano .env  # or your favorite editor
```
- [ ] `OPENAI_API_KEY` set
- [ ] `PINECONE_API_KEY` set
- [ ] `PINECONE_INDEX_NAME` set
- [ ] `GCP_PROJECT_ID` set (can be dummy for testing)

### Step 4: Repeat for Other Services
Repeat steps 2-3 for:
```bash
# Retrieval
cd apps/retrieval
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env

# Synthesis
cd apps/synthesis
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env

# Frontend
cd apps/frontend
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env
```

- [ ] All 4 services have venv/ directories
- [ ] All 4 services have .env files with API keys
- [ ] All 4 services dependencies installed

### Step 5: Verify Pinecone Setup
```python
# In Python shell with any service venv activated
from pinecone import Pinecone
pc = Pinecone(api_key="your-key")
index = pc.Index("rag-index")  # Must exist
print(index.describe_index_stats())
```
- [ ] Pinecone index exists and is accessible
- [ ] Index dimension is 1536 (for text-embedding-3-small)

## Phase 3: Test Local Services 🧪

Each of the 4 services runs independently on different ports. Start them in separate terminals.

### Terminal 1: Ingestion Service (Port 8000)
```bash
cd apps/ingestion
source venv/bin/activate
uvicorn app:app --port 8000 --reload
```
- [ ] Server starts on http://localhost:8000
- [ ] No errors in startup logs

### Terminal 2: Retrieval Service (Port 8001)
```bash
cd apps/retrieval
source venv/bin/activate
uvicorn app:app --port 8001 --reload
```
- [ ] Server starts on http://localhost:8001
- [ ] No errors in startup logs

### Terminal 3: Synthesis Service (Port 8002)
```bash
cd apps/synthesis
source venv/bin/activate
uvicorn app:app --port 8002 --reload
```
- [ ] Server starts on http://localhost:8002
- [ ] No errors in startup logs

### Terminal 4: Frontend Service (Port 8003)
```bash
cd apps/frontend
source venv/bin/activate
uvicorn app:app --port 8003 --reload
```
- [ ] Server starts on http://localhost:8003
- [ ] No errors in startup logs

### Step 2: Health Checks (in another terminal)
```bash
# Test all 4 services
curl http://localhost:8000/api/v1/health
curl http://localhost:8001/api/v1/health
curl http://localhost:8002/api/v1/health
curl http://localhost:8003/api/v1/health
```
- [ ] All return HTTP 200
- [ ] Show component status

### Step 3: Run Unit Tests
```bash
# Test each service independently
cd apps/ingestion && pytest tests/ -v
cd apps/retrieval && pytest tests/ -v
cd apps/synthesis && pytest tests/ -v
cd apps/frontend && pytest tests/ -v
```
- [ ] All tests pass
- [ ] No API keys needed (all mocked)

### Step 4: Ingest a Document
```bash
curl -X POST -F "file=@sample.pdf" \
  http://localhost:8000/api/v1/ingest
```
- [ ] HTTP 200 response
- [ ] Document processed and stored

### Step 5: Retrieve Similar Chunks
```bash
curl -X POST -H "Content-Type: application/json" \
  -d '{"query":"Your question","top_k":5}' \
  http://localhost:8001/api/v1/retrieve
```
- [ ] Returns list of similar chunks
- [ ] Contains relevance scores

### Step 6: Generate Response with Synthesis
```bash
curl -X POST -H "Content-Type: application/json" \
  -d '{"query":"Your question"}' \
  http://localhost:8002/api/v1/synthesize
```
- [ ] Returns LLM response
- [ ] Includes citations to source chunks

### Step 7: Query with Streaming (Frontend)
```bash
curl -N -X POST http://localhost:8003/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query":"Your question"}'
```
- [ ] Response streams as SSE events
- [ ] Contains answer chunks (incremental)
- [ ] Contains citation events
- [ ] Contains done event (metrics)

### Step 6: Review Metrics
Check stdout logs for JSON metrics:
```
{"event": "query_completed", "metrics": {...}}
{"event": "metrics_summary", "aggregated": {...}}
```
- [ ] Latency values reasonable (1-5 seconds)
- [ ] Cost estimates calculated
- [ ] Citations present

## Phase 4: Full Testing 🧪

```bash
python scripts/test_e2e.py
```
- [ ] Health check passes
- [ ] Document ingestion succeeds
- [ ] Query streaming works
- [ ] All tests green

## Phase 5: GCP Deployment (Optional) 🌐

### Prerequisites
- [ ] gcloud CLI installed
- [ ] Authenticated to GCP: `gcloud auth login`
- [ ] Project set: `gcloud config set project YOUR_PROJECT_ID`
- [ ] APIs enabled (see README.md)

### Terraform Setup
```bash
cd terraform/
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your values
```
- [ ] terraform.tfvars configured
- [ ] All required fields filled

### Deploy
```bash
terraform init
terraform plan
terraform apply
```
- [ ] Terraform init completes
- [ ] Plan shows all resources
- [ ] Apply succeeds
- [ ] Cloud Run service URL output

### Verify Deployment
```bash
# Get service URL
terraform output cloud_run_service_url

# Test endpoint
curl $(terraform output -raw cloud_run_service_url)/api/v1/health
```
- [ ] Service accessible at Cloud Run URL
- [ ] Health check responds

## Phase 6: Monitor Costs 💰

### Local Testing
```bash
# Watch cost logs during testing
grep total_cost < <(python -m uvicorn app.main:app --reload)
```
- [ ] Costs tracking in logs
- [ ] Values are reasonable (~$0.01-0.03 per query)

### Expected Testing Budget
| Queries | Estimated Cost |
|---------|----------------|
| 10 | $0.20 |
| 50 | $1.00 |
| 100 | $2.00 |
| 200 | $4.00 |

- [ ] Set GCP billing alerts (optional but recommended)
- [ ] Monitor actual costs in GCP Console

## Troubleshooting Checklist

### API won't start
- [ ] Python 3.11+ being used
- [ ] Virtual environment activated
- [ ] Dependencies installed: `pip list | grep fastapi`
- [ ] Port 8000 not in use: `lsof -i :8000`

### Pinecone errors
- [ ] API key correct in .env
- [ ] Index exists in Pinecone console
- [ ] Index dimension is 1536
- [ ] Network connectivity to Pinecone

### OpenAI errors
- [ ] API key has quota/credits
- [ ] API key not expired
- [ ] Rate limits not hit
- [ ] Models exist (gpt-4-turbo, text-embedding-3-small)

### No context in responses
- [ ] Document ingested successfully
- [ ] Check "chunks_created" in ingest response
- [ ] Try ingesting multiple documents
- [ ] Increase `query_top_k` in query request
- [ ] Check Pinecone index stats: `describe_index_stats()`

### High latency
- [ ] Check Cloud Run metrics (if deployed)
- [ ] Review Pinecone search latency
- [ ] Reduce `CONTEXT_BUDGET_TOKENS` if too large
- [ ] Check network connectivity

### Costs higher than expected
- [ ] Review tokens in metrics logs
- [ ] Check for failed requests (retries)
- [ ] Verify batch size is working (should be 20)
- [ ] Consider using cheaper embedding model

## Documentation Reference

| Document | Purpose |
|----------|---------|
| [README.md](README.md) | Full documentation |
| [QUICKSTART.md](QUICKSTART.md) | 5-minute setup |
| [PROJECT_SUMMARY.md](PROJECT_SUMMARY.md) | Overview & architecture |
| [DEVELOPMENT.md](DEVELOPMENT.md) | Implementation details |

## Next Steps After Setup

### Option A: Experiment & Learn
1. Try different queries and documents
2. Monitor metrics and costs
3. Adjust parameters (context_budget_tokens, top_k, etc.)
4. Review prompts in `app/rag/prompt.py`

### Option B: Prepare for Production
1. Add authentication (see DEVELOPMENT.md)
2. Set up monitoring dashboards
3. Configure cost alerts
4. Load test with concurrent requests
5. Review security settings

### Option C: Deploy to GCP
1. Follow Phase 5 above
2. Deploy from local Terraform
3. Test Cloud Run endpoint
4. Monitor costs on GCP

## Support

**Having issues?**
1. Check [README.md Troubleshooting](README.md#troubleshooting)
2. Check [DEVELOPMENT.md Debugging Tips](DEVELOPMENT.md#debugging-tips)
3. Review logs: `grep -i error`
4. Verify environment: `cat .env`

**Need help?**
- See inline comments in Python code
- Review test scripts for usage examples
- Check GCP Cloud Logging for deployment issues

---

**Estimated Total Setup Time:** 15-30 minutes (local) + 15 minutes (GCP if deploying)

**Enjoy your RAG API! 🚀**
