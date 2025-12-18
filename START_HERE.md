# Modular RAG - Getting Started Index

## 🎯 Where to Start?

### First Time? Start Here:
1. [MODULAR_QUICK_REFERENCE.md](MODULAR_QUICK_REFERENCE.md) - Commands and setup (5 min read)
2. [README_MODULAR.md](README_MODULAR.md) - Full overview (10 min read)
3. [ARCHITECTURE.md](ARCHITECTURE.md) - Design details (15 min read)

### Running Locally:
```bash
# Terminal 1: Ingestion (port 8000)
cd apps/ingestion && pip install -r requirements.txt && cp .env.example .env && uvicorn app:app --port 8000

# Terminal 2: Retrieval (port 8001)
cd apps/retrieval && pip install -r requirements.txt && cp .env.example .env && uvicorn app:app --port 8001

# Terminal 3: Synthesis (port 8002)
cd apps/synthesis && pip install -r requirements.txt && cp .env.example .env && uvicorn app:app --port 8002

# Terminal 4: Frontend (port 8003)
cd apps/frontend && pip install -r requirements.txt && cp .env.example .env && uvicorn app:app --port 8003
```

### Quick Test:
```bash
# Health checks
curl http://localhost:8000/api/v1/health
curl http://localhost:8003/api/v1/health

# Query (streams response)
curl -X POST -H "Content-Type: application/json" \
  -d '{"query":"What is your experience?"}' \
  http://localhost:8003/api/v1/query
```

## 📚 Documentation Structure

```
README_MODULAR.md                    ← Start here: Overview & Quick Start
├── MODULAR_QUICK_REFERENCE.md       ← Commands, env vars, API examples
├── ARCHITECTURE.md                  ← Deep dive: Services & design
├── COMPLETION_SUMMARY.md            ← What was built
└── THIS_FILE (START_HERE.md)        ← Index & navigation
```

## 🏗️ Project Structure

```
apps/                               # 4 independent services
├── ingestion/                       # PDF → Vectors (port 8000)
│   ├── app.py                       # FastAPI entry point
│   ├── services/pipeline.py         # Business logic
│   ├── handlers/routes.py           # API endpoints
│   ├── tests/                       # Unit tests + conftest
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
│
├── retrieval/                       # Vector search (port 8001)
│   ├── app.py
│   ├── services/pipeline.py
│   ├── handlers/routes.py
│   ├── tests/
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
│
├── synthesis/                       # LLM response (port 8002)
│   ├── app.py
│   ├── services/pipeline.py
│   ├── handlers/routes.py
│   ├── tests/
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
│
└── frontend/                        # SSE streaming (port 8003)
    ├── app.py
    ├── handlers/routes.py
    ├── requirements.txt
    ├── Dockerfile
    └── .env.example

common/                             # Shared library
├── models.py                        # Pydantic models
├── config.py                        # Settings
├── metrics.py                       # Metrics & timing
└── utils.py                         # Utilities

terraform/                          # GCP deployment
└── main.tf                         # 4 Cloud Run services

Documentation files
├── README_MODULAR.md               # Getting started
├── ARCHITECTURE.md                 # Design details
├── MODULAR_QUICK_REFERENCE.md      # Commands
├── COMPLETION_SUMMARY.md           # What was built
└── START_HERE.md                   # This file
```

## 🚀 One-Minute Setup

**Prerequisites**: Python 3.11+, OpenAI API key, Pinecone API key

```bash
# Clone or download repo
cd gcp-rag

# Create env files for each app
for dir in apps/ingestion apps/retrieval apps/synthesis apps/frontend; do
  cp $dir/.env.example $dir/.env
done

# Edit .env files with your API keys
# OPENAI_API_KEY, PINECONE_API_KEY, etc.

# Run the services in 4 terminals
cd apps/ingestion && pip install -r requirements.txt && uvicorn app:app --port 8000
cd apps/retrieval && pip install -r requirements.txt && uvicorn app:app --port 8001
cd apps/synthesis && pip install -r requirements.txt && uvicorn app:app --port 8002
cd apps/frontend && pip install -r requirements.txt && uvicorn app:app --port 8003

# In another terminal, test:
curl http://localhost:8003/api/v1/health
```

## 🔗 Service Endpoints

| Service | Port | Key Endpoint |
|---------|------|--------------|
| Ingestion | 8000 | `POST /api/v1/ingest` |
| Retrieval | 8001 | `POST /api/v1/retrieve` |
| Synthesis | 8002 | `POST /api/v1/synthesize` |
| Frontend | 8003 | `POST /api/v1/query` (SSE) |

All services have `GET /api/v1/health` for health checks.

## 📖 Service Descriptions

### Ingestion (Port 8000)
- **Purpose**: Accept PDFs, extract text, chunk, generate embeddings, store in Pinecone
- **Tech**: PyPDF2, OpenAI embeddings, Pinecone
- **Input**: Multipart file upload
- **Output**: Chunks stored in vector database

### Retrieval (Port 8001)
- **Purpose**: Search vectors, rank results, return relevant chunks
- **Tech**: Pinecone query API, OpenAI embeddings
- **Input**: Query string, user_id, top_k
- **Output**: RetrievedChunk list

### Synthesis (Port 8002)
- **Purpose**: Call Retrieval, generate LLM response with citations
- **Tech**: OpenAI LLM, httpx for service calls
- **Input**: Query string
- **Output**: Answer + citations + metadata

### Frontend (Port 8003)
- **Purpose**: Lightweight API with SSE streaming
- **Tech**: FastAPI, httpx, Server-Sent Events
- **Input**: Query string
- **Output**: SSE stream (answer, citations, done)

## 🧪 Testing

```bash
# Run all tests
cd apps/ingestion && pytest tests/ -v
cd apps/retrieval && pytest tests/ -v
cd apps/synthesis && pytest tests/ -v

# Tests don't require API keys (all mocked)
# See conftest.py in each app for fixtures
```

## 📦 Deployment

### Local Docker
```bash
# Build images
docker build -t rag-ingestion:latest apps/ingestion/
docker build -t rag-retrieval:latest apps/retrieval/
docker build -t rag-synthesis:latest apps/synthesis/
docker build -t rag-frontend:latest apps/frontend/

# Run with docker-compose or docker run
```

### GCP Cloud Run
```bash
# Build and push
docker build -t gcr.io/PROJECT_ID/rag-ingestion:latest apps/ingestion/
docker push gcr.io/PROJECT_ID/rag-ingestion:latest
# ... repeat for other services

# Deploy
cd terraform
terraform apply
```

## ⚙️ Key Features

✅ **Modular**: 4 independent services
✅ **Testable**: 100% mockable dependencies
✅ **Type-Safe**: Pydantic models everywhere
✅ **Scalable**: Auto-scaling Cloud Run
✅ **Documented**: Complete architecture docs
✅ **Production-Ready**: Error handling, logging, metrics
✅ **Cost-Efficient**: Pay only for what you use
✅ **Extensible**: Easy to add new services

## 🆘 Troubleshooting

**Port in use?**
```bash
lsof -i :8000  # Find process
kill -9 <PID>  # Kill it
```

**Import errors?**
```bash
export PYTHONPATH=/home/zac/gcp-rag:$PYTHONPATH
```

**API key errors?**
```bash
# Check .env files exist and have values
cat apps/ingestion/.env | grep OPENAI_API_KEY
```

**Service not responding?**
```bash
# Check logs
curl -v http://localhost:8000/api/v1/health
# Run with debug logging
uvicorn app:app --port 8000 --log-level debug
```

## 📞 Next Steps

1. ✅ **Read**: [MODULAR_QUICK_REFERENCE.md](MODULAR_QUICK_REFERENCE.md)
2. ✅ **Start**: Run all 4 services locally
3. ✅ **Test**: Use curl commands to verify flow
4. ✅ **Deploy**: Follow GCP instructions in [README_MODULAR.md](README_MODULAR.md)
5. ✅ **Monitor**: Check logs in Cloud Console

## 📚 Full Documentation

- **[README_MODULAR.md](README_MODULAR.md)** - Complete getting started guide
- **[ARCHITECTURE.md](ARCHITECTURE.md)** - System design and data flows
- **[MODULAR_QUICK_REFERENCE.md](MODULAR_QUICK_REFERENCE.md)** - Command reference
- **[COMPLETION_SUMMARY.md](COMPLETION_SUMMARY.md)** - What was built

---

**Ready?** → [MODULAR_QUICK_REFERENCE.md](MODULAR_QUICK_REFERENCE.md)

**Questions?** → [ARCHITECTURE.md](ARCHITECTURE.md)

**Deploy?** → [README_MODULAR.md](README_MODULAR.md)
