# Terraform Configuration for 4-Microservice RAG Architecture

This directory contains Infrastructure-as-Code (IaC) for deploying the RAG system to Google Cloud Platform (GCP).

## Architecture Overview

The configuration deploys **4 independent FastAPI microservices** to Cloud Run:

```
┌─────────────────────────────────────────────────────────┐
│                  GCP Cloud Run                          │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │ Ingestion    │  │ Retrieval    │  │ Synthesis    │ │
│  │ Port 8000    │  │ Port 8001    │  │ Port 8002    │ │
│  │ 2GB Memory   │  │ 2GB Memory   │  │ 2GB Memory   │ │
│  │ 1 CPU        │  │ 1 CPU        │  │ 1 CPU        │ │
│  └──────────────┘  └──────────────┘  └──────────────┘ │
│                                                         │
│  ┌──────────────────────────────────────────────────┐  │
│  │ Frontend (SSE Streaming)                         │  │
│  │ Port 8003 | 2GB Memory | 1 CPU                  │  │
│  └──────────────────────────────────────────────────┘  │
│                                                         │
└─────────────────────────────────────────────────────────┘
                          ↓
            ┌─────────────────────────────┐
            │   Shared Services           │
            ├─────────────────────────────┤
            │ • Secret Manager (API keys) │
            │ • Cloud Storage (Documents) │
            │ • Cloud Logging (Telemetry)│
            │ • Cloud Monitoring (Alerts) │
            └─────────────────────────────┘
```

## File Structure

| File | Purpose |
|------|---------|
| `main.tf` | Provider configuration, shared variables |
| `services.tf` | **NEW** - 4 Cloud Run service definitions |
| `secrets.tf` | Secret Manager for API keys |
| `storage.tf` | GCS bucket for PDF documents |
| `networking.tf` | VPC and firewall rules |
| `monitoring.tf` | Cloud Logging and Monitoring |
| `outputs.tf` | Output values (service URLs, etc.) |
| `variables.tf` | Input variables |
| `terraform.tfvars.example` | Example variable values |

## Services Deployment Details

### 1. Ingestion Service (Port 8000)
**Purpose:** PDF upload, text extraction, chunking, embedding generation

**Key Configuration:**
- **Cloud Run Service:** `rag-ingestion`
- **Memory:** 2GB (for PDF processing)
- **CPU:** 1 vCPU
- **Timeout:** 300 seconds (long for PDF uploads)
- **Max Instances:** 10 (auto-scales)
- **Endpoint:** `/api/v1/ingest` (POST)

**Environment Variables:**
- `OPENAI_API_KEY` (from Secret Manager)
- `PINECONE_API_KEY` (from Secret Manager)
- `PINECONE_INDEX_NAME`
- `GCP_PROJECT_ID`

**IAM Permissions:**
- GCS Object Admin (read/write documents)
- Secret Manager Secret Accessor

---

### 2. Retrieval Service (Port 8001)
**Purpose:** Vector similarity search, ranking, deduplication

**Key Configuration:**
- **Cloud Run Service:** `rag-retrieval`
- **Memory:** 2GB (for holding retrieved chunks)
- **CPU:** 1 vCPU
- **Timeout:** 60 seconds (fast search)
- **Max Instances:** 10 (auto-scales)
- **Endpoint:** `/api/v1/retrieve` (POST)

**Environment Variables:**
- `OPENAI_API_KEY` (from Secret Manager)
- `PINECONE_API_KEY` (from Secret Manager)
- `PINECONE_INDEX_NAME`

**IAM Permissions:**
- Secret Manager Secret Accessor

---

### 3. Synthesis Service (Port 8002)
**Purpose:** LLM orchestration, prompt building, citation extraction

**Key Configuration:**
- **Cloud Run Service:** `rag-synthesis`
- **Memory:** 2GB (for LLM context)
- **CPU:** 1 vCPU
- **Timeout:** 60 seconds (LLM response time)
- **Max Instances:** 10 (auto-scales)
- **Endpoint:** `/api/v1/synthesize` (POST)

**Environment Variables:**
- `OPENAI_API_KEY` (from Secret Manager)
- `PINECONE_API_KEY` (from Secret Manager)
- `RETRIEVAL_SERVICE_URL` (internal: `http://rag-retrieval:8001`)

**Internal Service Calls:**
- Calls Retrieval Service (port 8001) via VPC

**IAM Permissions:**
- Secret Manager Secret Accessor

---

### 4. Frontend Service (Port 8003)
**Purpose:** Consumer-facing SSE streaming API

**Key Configuration:**
- **Cloud Run Service:** `rag-frontend`
- **Memory:** 2GB
- **CPU:** 1 vCPU
- **Timeout:** 300 seconds (long for streaming)
- **Max Instances:** 10 (auto-scales)
- **Endpoint:** `/api/v1/query` (POST, SSE streaming)

**Environment Variables:**
- `SYNTHESIS_SERVICE_URL` (internal: `http://rag-synthesis:8002`)
- `GCP_PROJECT_ID`

**Internal Service Calls:**
- Calls Synthesis Service (port 8002) via VPC

**IAM Permissions:**
- Cloud Logging API (for metrics)

---

## Shared Resources

### Secrets (Secret Manager)
```
rag-openai-key        → OpenAI API key (shared by all 4 services)
rag-pinecone-key      → Pinecone API key (shared by all 4 services)
```

### Storage (GCS)
```
gs://[project-id]-rag-documents/
├── pdfs/              → Uploaded PDF files
├── chunks/            → Extracted text chunks
└── metadata/          → Chunk metadata (JSON)
```

### Networking (VPC)
```
default VPC with:
- Cloud Run services running in same region
- Service-to-service communication via internal URLs
- Firewall rules allowing ingress from internet (frontend only)
```

### Monitoring (Cloud Logging)
```
- Per-service logs to Cloud Logging
- JSON structured logging
- Query metrics available in GCP Logs
```

## Deployment Workflow

### 1. Build Docker Images
```bash
# From project root, build each service image
for service in ingestion retrieval synthesis frontend; do
  docker build -t gcr.io/[PROJECT_ID]/rag-${service}:latest \
    apps/${service}/
  docker push gcr.io/[PROJECT_ID]/rag-${service}:latest
done
```

### 2. Prepare Terraform Variables
```bash
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with:
# - gcp_project_id
# - gcp_region
# - openai_api_key
# - pinecone_api_key
# - pinecone_index_name
# - gcs_bucket_name
# - docker_image_tag (e.g., "latest")
```

### 3. Deploy Infrastructure
```bash
cd terraform/

# Initialize Terraform (first time only)
terraform init

# Preview changes
terraform plan

# Deploy all 4 services
terraform apply
```

### 4. Verify Deployment
```bash
# Get service URLs
terraform output service_urls

# Test Ingestion Service
curl https://[ingestion-url]/api/v1/health

# Test Frontend Service (SSE)
curl https://[frontend-url]/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query":"test"}'
```

## Service-to-Service Communication

Services communicate via **Cloud Run internal URLs** in the same VPC:

```
Frontend (Port 8003)
    ↓
    calls Synthesis at: http://rag-synthesis:8002
    ↓
Synthesis (Port 8002)
    ↓
    calls Retrieval at: http://rag-retrieval:8001
    ↓
Retrieval (Port 8001)
    ↓
    queries Pinecone
```

**No external HTTP calls needed** - all internal VPC traffic is private and fast.

## Scaling Behavior

Each service **auto-scales independently**:

| Service | Min Instances | Max Instances | Scaling Metric |
|---------|---------------|---------------|-----------------|
| Ingestion | 0 | 10 | Request rate / CPU |
| Retrieval | 0 | 10 | Request rate / CPU |
| Synthesis | 0 | 10 | Request rate / CPU |
| Frontend | 0 | 10 | Request rate / CPU |

**Benefits:**
- Only pay for what you use
- Ingestion spikes don't affect retrieval performance
- Each service scales based on its own load

## Cost Estimates

**Per-service per month (estimated at moderate usage):**

| Service | CPU | Memory | Est. Cost |
|---------|-----|--------|-----------|
| Ingestion | 1 vCPU | 2GB | $25-40 |
| Retrieval | 1 vCPU | 2GB | $25-40 |
| Synthesis | 1 vCPU | 2GB | $25-40 |
| Frontend | 1 vCPU | 2GB | $25-40 |
| **Shared** (Secrets, Storage, Logging) | - | - | $10-20 |
| **Total** | - | - | **$110-180** |

*Note: Excludes OpenAI and Pinecone API costs*

## Variables Reference

### Required Variables
```hcl
gcp_project_id          # Your GCP Project ID
openai_api_key          # OpenAI API key (sensitive)
pinecone_api_key        # Pinecone API key (sensitive)
gcs_bucket_name         # Name for GCS bucket (must be globally unique)
```

### Optional Variables (with defaults)
```hcl
gcp_region              # Default: "us-central1"
docker_image_tag        # Default: "latest"
cpu_per_service         # Default: "1" vCPU
memory_per_service      # Default: "2Gi"
max_instances_per_service  # Default: 10
```

## Troubleshooting

### Service fails to start
- Check Cloud Run logs: `gcloud run logs read [service-name]`
- Verify environment variables in Cloud Run console
- Ensure Docker image exists: `gcloud container images list`

### Service-to-service communication fails
- Verify services are in same VPC
- Check firewall rules
- Verify service account IAM permissions

### High memory usage
- Reduce `memory_per_service` in terraform.tfvars (currently 2GB)
- Monitor with Cloud Monitoring dashboard

### Costs higher than expected
- Review Cloud Run dashboard for idle instances
- Check OpenAI/Pinecone usage
- Reduce `max_instances_per_service` if needed

## Cleanup

To tear down all resources:

```bash
cd terraform/
terraform destroy
```

This removes all 4 services, secrets, storage, and networking resources.

---

**Last Updated:** January 2025
**Terraform Version:** >= 1.0
**Google Provider Version:** >= 5.0
