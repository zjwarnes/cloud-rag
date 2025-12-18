# Architecture Patterns & Deployment Scenarios

Visual guide to understanding how your services interact and how to extend for different deployment scenarios.

---

## Current Architecture (Single Environment)

```
┌──────────────────────────────────────────────────────────────┐
│                    GCP Cloud Run                             │
│                   (Single Region: us-central1)               │
└──────────────────────────────────────────────────────────────┘
        │                                          │
        │ PDF Upload                              │ Query
        ▼                                          ▼
    ┌────────────┐                          ┌────────────┐
    │ INGESTION  │                          │ FRONTEND   │
    │ Port 8000  │                          │ Port 8003  │
    │ 2GB Memory │                          │ 2GB Memory │
    │ Public     │                          │ Public     │
    └─────┬──────┘                          └─────┬──────┘
          │                                       │
          │ Stores vectors                        │ Calls
          │                                       │
          ▼                                       ▼
    ┌────────────────────────────┐         ┌────────────────┐
    │   Secret Manager           │◄───────►│   Synthesis    │
    │   (API Keys)               │         │   Port 8002    │
    └────────────────────────────┘         │   2GB Memory   │
          ▲          ▲                     │   Private      │
          │          │                     └────────┬───────┘
          │          │ Access Keys                  │
          │          │                              │ Calls
    ┌─────┴──────────┴──────┐                       │
    │  Retrieval Service    │◄──────────────────────┘
    │  Port 8001            │
    │  2GB Memory           │
    │  Private              │
    └─────────┬─────────────┘
              │ Queries
              ▼
    ┌─────────────────────┐
    │  Pinecone (External)│
    │  Vector Database    │
    └─────────────────────┘


┌───────────────────────────────────────────────────────────────┐
│               Shared Resources                               │
├───────────────────────────────────────────────────────────────┤
│ • GCS Bucket (PDF storage)                                   │
│ • Service Accounts (IAM per service)                         │
│ • Cloud Logging (centralized logs)                           │
│ • Cloud Monitoring (alerts)                                  │
└───────────────────────────────────────────────────────────────┘
```

---

## Request Flow: User Query

```
1. User Request
   │
   │ POST /api/v1/query
   │ {"query": "What is deployed?", "user_id": "user123"}
   │
   ▼
┌─────────────────────────────────────────────────────────────┐
│ Frontend Service (Port 8003)                                │
│ • Receives HTTP request                                     │
│ • Validates request parameters                              │
└────────────────┬────────────────────────────────────────────┘
                 │ Internal: Call Synthesis
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│ Synthesis Service (Port 8002)                               │
│ • Gets query and user_id                                    │
│ • Calls Retrieval service                                   │
└────────────────┬────────────────────────────────────────────┘
                 │ Internal: Call Retrieval
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│ Retrieval Service (Port 8001)                               │
│ • Embeds query using OpenAI                                 │
│ • Searches Pinecone vector DB                               │
│ • Returns top 10 chunks with scores                         │
└────────────────┬────────────────────────────────────────────┘
                 │ HTTP Response
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│ Synthesis Service (receives chunks)                         │
│ • Builds prompt with retrieved context                      │
│ • Calls OpenAI chat completions                             │
│ • Extracts citations from response                          │
└────────────────┬────────────────────────────────────────────┘
                 │ HTTP Response
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│ Frontend Service (receives response)                        │
│ • Streams response back to user via SSE                     │
│ • Handles connection/retry logic                            │
└────────────────┬────────────────────────────────────────────┘
                 │ SSE Stream
                 │
                 ▼
2. User receives streaming response
   data: {"token":"The"}
   data: {"token":"system"}
   data: {"token":"is"}
   ...
```

---

## Request Flow: Document Upload

```
1. User uploads PDF
   │
   │ POST /api/v1/ingest
   │ multipart/form-data: file=document.pdf, user_id=user123
   │
   ▼
┌─────────────────────────────────────────────────────────────┐
│ Ingestion Service (Port 8000)                               │
│ • Receives PDF file                                         │
│ • Saves to GCS bucket                                       │
│ • Extracts text using PyPDF2                                │
│ • Splits into chunks (500 tokens, 100 overlap)              │
└────────────────┬────────────────────────────────────────────┘
                 │ Call OpenAI embeddings API
                 │ (batched: 20 texts per call)
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│ OpenAI API (External)                                       │
│ • text-embedding-3-small model                              │
│ • Returns 1536-dimensional vectors                          │
└────────────────┬────────────────────────────────────────────┘
                 │ Vectors returned
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│ Ingestion Service (receives vectors)                        │
│ • Calls Pinecone with vectors + metadata                    │
│ • Metadata includes: user_id, chunk_id, page, text_preview  │
└────────────────┬────────────────────────────────────────────┘
                 │ Call Pinecone API
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│ Pinecone (External Vector DB)                               │
│ • Stores vectors with metadata                              │
│ • Indexes for fast retrieval                                │
└────────────────┬────────────────────────────────────────────┘
                 │ Success response
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│ Ingestion Service (returns result)                          │
│ {"status": "success", "chunks": 42, "vectors_stored": 42}   │
└────────────────┬────────────────────────────────────────────┘
                 │ HTTP Response
                 │
                 ▼
2. User receives success response
```

---

## Deployment Scenario 1: DEV/PROD Split

Use **separate GCP projects** for isolation:

```
┌─────────────────────────────────────────────────────────────┐
│             GCP Organization                                │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────────────┐      ┌──────────────────────┐   │
│  │  GCP Project: DEV    │      │ GCP Project: PROD    │   │
│  │  ├─ rag-ingestion    │      │ ├─ rag-ingestion     │   │
│  │  ├─ rag-retrieval    │      │ ├─ rag-retrieval     │   │
│  │  ├─ rag-synthesis    │      │ ├─ rag-synthesis     │   │
│  │  ├─ rag-frontend     │      │ ├─ rag-frontend      │   │
│  │  │  (512MB, 1 CPU)   │      │ │  (4GB, 2 CPU)      │   │
│  │  ├─ dev-documents    │      │ ├─ prod-documents    │   │
│  │  └─ Pinecone: dev    │      │ └─ Pinecone: prod    │   │
│  │                      │      │                      │   │
│  │  Max instances: 1    │      │ Max instances: 20    │   │
│  │  Budget: $30/month   │      │ Budget: $200/month   │   │
│  └──────────────────────┘      └──────────────────────┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘

Terraform Deployment:
cd terraform/dev   && terraform apply -var-file=dev.tfvars
cd terraform/prod  && terraform apply -var-file=prod.tfvars
```

**Use case**: Develop safely without affecting production.

---

## Deployment Scenario 2: Multi-Client (Shared Project)

Use **separate service instances** per client:

```
┌──────────────────────────────────────────────────────────────┐
│               GCP Project: "RAG SaaS"                        │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  Client A                    Client B                        │
│  ┌──────────────────┐        ┌──────────────────┐           │
│  │ rag-ingestion-a  │        │ rag-ingestion-b  │           │
│  │ rag-retrieval-a  │        │ rag-retrieval-b  │           │
│  │ rag-synthesis-a  │        │ rag-synthesis-b  │           │
│  │ rag-frontend-a   │        │ rag-frontend-b   │           │
│  └──────────────────┘        └──────────────────┘           │
│          │                           │                       │
│          ▼                           ▼                       │
│  ┌──────────────────┐        ┌──────────────────┐           │
│  │ Pinecone:        │        │ Pinecone:        │           │
│  │ index-client-a   │        │ index-client-b   │           │
│  └──────────────────┘        └──────────────────┘           │
│                                                              │
│  Shared Resources:                                          │
│  ├─ rag-documents-a (GCS)                                   │
│  ├─ rag-documents-b (GCS)                                   │
│  ├─ Secret Manager (API keys)                               │
│  └─ Monitoring/Logging                                      │
│                                                              │
└──────────────────────────────────────────────────────────────┘

Terraform Deployment:
terraform apply -var="clients=[a,b,c]"

API Usage:
  https://rag-frontend-a.run.app/api/v1/query
  https://rag-frontend-b.run.app/api/v1/query
```

**Use case**: SaaS with separate instances per customer.

---

## Deployment Scenario 3: Geographic Regions

Deploy same services to multiple regions for latency:

```
┌────────────────────────────────────────────────────────────┐
│            GCP Organization (Multi-Region)                 │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  ┌─────────────────────────────────────────────────────┐  │
│  │ US Region: us-central1                              │  │
│  │ ├─ rag-ingestion (us-central1)                      │  │
│  │ ├─ rag-retrieval (us-central1)                      │  │
│  │ ├─ rag-synthesis (us-central1)                      │  │
│  │ └─ rag-frontend (us-central1)                       │  │
│  │    Latency: ~10ms from US                           │  │
│  └─────────────────────────────────────────────────────┘  │
│                                                            │
│  ┌─────────────────────────────────────────────────────┐  │
│  │ EU Region: europe-west1                             │  │
│  │ ├─ rag-ingestion (europe-west1)                     │  │
│  │ ├─ rag-retrieval (europe-west1)                     │  │
│  │ ├─ rag-synthesis (europe-west1)                     │  │
│  │ └─ rag-frontend (europe-west1)                      │  │
│  │    Latency: ~10ms from EU                           │  │
│  └─────────────────────────────────────────────────────┘  │
│                                                            │
│  Shared:                                                   │
│  ├─ Global GCS buckets (replicated)                       │
│  ├─ Multi-region Pinecone index                           │
│  └─ Cross-region Secret Manager                           │
│                                                            │
└────────────────────────────────────────────────────────────┘

Terraform Deployment:
for region in us-central1 europe-west1; do
  terraform apply -var="gcp_region=$region"
done
```

**Use case**: Global users need low latency.

---

## Scaling Patterns

### Pattern 1: Uneven Traffic

If you have bursty ingestion but steady queries:

```
┌─────────────────────────────────────────────────────────┐
│           Cloud Run Auto-Scaling Limits                 │
├─────────────────────────────────────────────────────────┤
│                                                         │
│ Ingestion:     max_instances = 50  (bursty uploads)   │
│ Retrieval:     max_instances = 10  (steady queries)    │
│ Synthesis:     max_instances = 10  (steady queries)    │
│ Frontend:      max_instances = 20  (user facing)       │
│                                                         │
│ Scenarios:                                              │
│ • 100 PDFs uploaded simultaneously                      │
│   → Ingestion scales to 50 instances                    │
│   → Other services unaffected                           │
│                                                         │
│ • 10K concurrent users querying                         │
│   → Frontend scales to 20 instances                     │
│   → Ingestion stays at 0 (no uploads)                   │
│   → Saves money!                                        │
│                                                         │
└─────────────────────────────────────────────────────────┘

Configuration in Terraform:
variable "max_instances_per_service" {
  type = map(number)
  default = {
    ingestion  = 50
    retrieval  = 10
    synthesis  = 10
    frontend   = 20
  }
}
```

### Pattern 2: Resource-Based Scaling

Different memory per service:

```
┌─────────────────────────────────────────────────────────┐
│           Service-Specific Resource Limits              │
├─────────────────────────────────────────────────────────┤
│                                                         │
│ Ingestion:   4GB memory (PDF processing intensive)     │
│ Retrieval:   2GB memory (holds search results)          │
│ Synthesis:   2GB memory (LLM context)                  │
│ Frontend:    1GB memory (lightweight proxy)             │
│                                                         │
│ Cost Impact:                                            │
│ • High memory = higher per-instance cost               │
│ • But fewer instances needed for same throughput      │
│ • Adjust based on your workload                        │
│                                                         │
└─────────────────────────────────────────────────────────┘

Configuration in Terraform:
variable "memory_per_service" {
  type = map(string)
  default = {
    ingestion  = "4Gi"
    retrieval  = "2Gi"
    synthesis  = "2Gi"
    frontend   = "1Gi"
  }
}
```

---

## Service Communication Patterns

### Pattern 1: Sync (Current - HTTP)

```
┌──────────┐  Request  ┌──────────┐
│ Frontend │ --------> │Synthesis │  Timeout: 5s
└──────────┘           └──────────┘
     ▲                       │
     │                       │ Request
     │                       ▼
     │                  ┌──────────┐
     │                  │Retrieval │  Timeout: 30s
     │                  └──────────┘
     └──────────────────────────────

Advantages:
• Simple request/response
• Easy debugging with HTTP
• Built-in error handling

Disadvantages:
• Blocking calls (server must wait)
• One failure blocks entire chain
• Long chains = higher latency
```

### Pattern 2: Async (Pub/Sub) - Future Enhancement

```
┌──────────┐
│ Frontend │──────┐
└──────────┘      │
                  ▼
             ┌─────────────┐
             │  Cloud      │
             │  Pub/Sub    │
             └─────────────┘
                  ▲
                  │
            ┌─────┴─────┬───────┐
            │           │       │
            ▼           ▼       ▼
       ┌─────────┐ ┌─────────┐ ┌────────┐
       │Synthesis│ │Retrieval│ │Logging │
       └─────────┘ └─────────┘ └────────┘

Advantages:
• Non-blocking (fire and forget)
• One service failure doesn't block others
• Better scalability
• Built-in retry logic

Disadvantages:
• More complex to implement
• Harder to debug
• Eventual consistency
```

---

## Monitoring & Observability

### What to Monitor

```
┌────────────────────────────────────────────────────────────┐
│              Cloud Monitoring Dashboard                   │
├────────────────────────────────────────────────────────────┤
│                                                            │
│ Per Service:                                              │
│ ├─ Request count (invocations)                            │
│ ├─ Request latency (p50, p95, p99)                        │
│ ├─ Error rate (5xx responses)                             │
│ ├─ Concurrent instances (scaling)                         │
│ └─ CPU/Memory usage                                       │
│                                                            │
│ System Level:                                              │
│ ├─ Total cost (GCP billing API)                           │
│ ├─ External API costs (OpenAI, Pinecone)                  │
│ ├─ Cold start latency (first request)                     │
│ └─ Availability (uptime%)                                 │
│                                                            │
│ Alerts:                                                    │
│ ├─ Error rate > 5% → Page on-call                         │
│ ├─ Latency p99 > 30s → Send alert                         │
│ ├─ Cost > $500/day → Investigate                          │
│ └─ Ingestion fails → Notify ops                           │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

---

## Disaster Recovery

### Backup Strategy

```
┌─────────────────────────────────────────────────────────────┐
│                    Backup Strategy                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ Daily Backup (Automated):                                  │
│ GCS Bucket                                                  │
│ ├─ Enable versioning (already done)                         │
│ ├─ Cross-region replication                                 │
│ ├─ Lifecycle: keep 30 days of old versions                  │
│ └─ Snapshot to separate bucket daily                        │
│                                                             │
│ Pinecone Index:                                             │
│ ├─ Export vectors to GCS weekly                             │
│ ├─ Test restore monthly                                     │
│ └─ Keep 3 months of exports                                 │
│                                                             │
│ Terraform State:                                            │
│ ├─ Store in GCS (not local)                                 │
│ ├─ Enable versioning                                        │
│ ├─ Enable GCS bucket logging                                │
│ └─ Test restore quarterly                                   │
│                                                             │
│ Disaster Scenarios:                                         │
│                                                             │
│ 1. Service crashes → Cloud Run auto-restarts               │
│ 2. Code bug → Redeploy previous version                     │
│ 3. Data corruption → Restore from GCS versions              │
│ 4. Region failure → Deploy to different region              │
│ 5. DDoS attack → Cloud Armor protects endpoints             │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Cost Optimization Matrix

```
┌──────────────────────────────────────────────────────────────┐
│         Choose optimization based on your needs              │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│         Low Traffic    Medium Traffic    High Traffic        │
│         (Dev)          (Staging)         (Prod)              │
│                                                              │
│ Memory    512MB         2GB                4GB                │
│ CPU       0.5           1                  2                  │
│ Max Inst. 1             5                  20                 │
│ Cost/mo   $10           $50                $200               │
│                                                              │
│ Optimizations:                                               │
│ ├─ Use spot instances (if available)                        │
│ ├─ Batch requests (reduce API calls)                        │
│ ├─ Cache results (avoid duplicate work)                     │
│ ├─ Compress data (reduce storage)                           │
│ └─ Schedule off-peak cleanup tasks                          │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

---

## Decision Tree: Choose Your Deployment Model

```
START
  │
  ├─ Single company using internally?
  │  YES → Scenario 1 (DEV/PROD split)
  │  NO  → Continue
  │
  ├─ Building SaaS for multiple customers?
  │  YES → Scenario 2 (Multi-Client)
  │  NO  → Continue
  │
  ├─ Global users needing low latency?
  │  YES → Scenario 3 (Multi-Region)
  │  NO  → Continue
  │
  └─ Simple single production deployment
     → Current setup (one environment)

OPTIMIZATION: After 6 months in production
  ├─ If costs too high
  │  → Reduce memory, use async where possible
  │
  ├─ If performance issues
  │  → Increase memory, add regions
  │
  └─ If managing many clients
     → Consider moving to dedicated per-client projects
```

---

## Migration Path: Monolith → Microservices

If you currently have a monolith, here's how to migrate:

```
Stage 1: Deploy as-is (1 Cloud Run service, all code)
  ├─ Create single image with all 4 endpoints
  └─ Works but doesn't scale independently

Stage 2: Extract Retrieval (high-traffic read)
  ├─ Move Retrieval to separate service
  ├─ Monolith calls it via HTTP
  └─ Reduces monolith load

Stage 3: Extract Synthesis (LLM intensive)
  ├─ Move to separate service
  ├─ Can scale independently
  └─ Faster iteration

Stage 4: Extract Ingestion (bursty workload)
  ├─ Move to separate service
  ├─ Scales independently during batch uploads
  └─ Frontend only calls other services

Stage 5: Extract Frontend (public API)
  ├─ Clean separation of concerns
  ├─ Each service can be maintained independently
  └─ Full benefits of microservices architecture
```

