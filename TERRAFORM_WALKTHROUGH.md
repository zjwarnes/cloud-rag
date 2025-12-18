# Terraform Walkthrough: Understanding Your 4-Microservice RAG Deployment

This guide walks through your Terraform configuration to help you understand the architecture, why each component is needed, and how to extend it for multi-environment deployments.

---

## Table of Contents

1. [High-Level Architecture](#high-level-architecture)
2. [What Each File Does](#what-each-file-does)
3. [The 4 Microservices](#the-4-microservices)
4. [GCP Setup Requirements](#gcp-setup-requirements)
5. [Why Each Resource Is Needed](#why-each-resource-is-needed)
6. [Extending for DEV/TEST/PROD](#extending-for-devtestprod)
7. [Extending for Client-Based Deployments](#extending-for-client-based-deployments)

---

## High-Level Architecture

Your system is a **4-tier microservice architecture** where each service handles one responsibility:

```
┌───────────────────────────────────────────────────────────┐
│                   INTERNET                                 │
│           (Users, Clients, External APIs)                 │
└────────────────┬────────────────────────────────────┬──────┘
                 │                                    │
          (PDF Upload)                         (Query/Stream)
                 │                                    │
                 ▼                                    ▼
        ┌──────────────────┐            ┌──────────────────┐
        │  INGESTION       │            │    FRONTEND      │
        │  Port 8000       │            │    Port 8003     │
        │  (Private/Public)│            │    (Public)      │
        └────────┬─────────┘            └────────┬─────────┘
                 │ Stores embeddings              │ Calls
                 │                                │ Synthesis
                 ▼                                ▼
          ┌─────────────┐              ┌─────────────────────┐
          │  GCS        │              │   SYNTHESIS         │
          │  Storage    │              │   Port 8002         │
          │  (PDFs)     │              │   (Private)         │
          └─────────────┘              └────────┬────────────┘
                 ▲                               │ Calls
                 │                               │ Retrieval
                 └───────────────────────────────┘
                           │
                           ▼
                  ┌──────────────────┐
                  │   RETRIEVAL      │
                  │   Port 8001      │
                  │   (Private)      │
                  └────────┬─────────┘
                           │ Queries
                           ▼
                  ┌──────────────────┐
                  │   PINECONE       │
                  │   Vector DB      │
                  │   (External)     │
                  └──────────────────┘
```

---

## What Each File Does

### 1. **variables.tf** - Input Parameters
Defines all configurable parameters for your deployment. These are like "function arguments" for Terraform.

**Key Variables:**
- `gcp_project_id` - Which GCP project to deploy to
- `gcp_region` - Where to deploy (e.g., us-central1)
- `openai_api_key` - Secret for embeddings/LLM
- `pinecone_api_key` - Secret for vector database
- `gcs_bucket_name` - Storage bucket for PDFs
- `cpu_per_service` - Resource allocation (1 CPU recommended)
- `memory_per_service` - Memory allocation (2GB recommended)
- `docker_image_tag` - Which image version to deploy

**Why this matters:** These variables let you have ONE Terraform code that deploys to different environments by changing input values.

---

### 2. **secrets.tf** - API Keys Management
Creates and manages sensitive credentials in GCP Secret Manager.

**What it does:**
```
Creates 2 secrets in Secret Manager:
├── rag-openai-key        (OpenAI API key)
└── rag-pinecone-key      (Pinecone API key)
```

**Why it's needed:**
- **Never hardcode API keys** in images or config files
- Secret Manager encrypts keys at rest and in transit
- Each service gets IAM permissions to access only its needed secrets
- Secrets can be rotated without redeploying services

**How it works:**
```terraform
resource "google_secret_manager_secret" "openai_key" {
  secret_id = "rag-openai-key"
  # Automatic replication across regions
  replication { automatic = true }
}

# Then each service references it:
env {
  name = "OPENAI_API_KEY"
  value_from {
    secret_key_ref {
      name = google_secret_manager_secret.openai_key.id
      key  = "latest"
    }
  }
}
```

---

### 3. **storage.tf** - GCS Bucket Configuration
Creates and configures your document storage.

**What it does:**
- Creates a GCS bucket with the name you specify
- Sets `uniform_bucket_level_access = true` (modern ACL model)
- Enables versioning (keeps old versions of files)
- Auto-deletes files after 90 days (cost optimization)

**Why it's needed:**
- The Ingestion service needs a place to store uploaded PDFs
- GCS is cheap, scalable, and integrates with GCP services
- Versioning protects against accidental deletion
- 90-day auto-delete prevents accumulating old test files

---

### 4. **networking.tf** - VPC & Firewall
Sets up network rules for your services.

**What it does:**
```
Creates:
├── google_compute_network - VPC network
└── google_compute_firewall - Allows outbound traffic to external APIs
    (OpenAI, Pinecone, etc.)
```

**Why it's needed:**
- Cloud Run services need to reach external APIs (OpenAI, Pinecone)
- Firewall rules allow egress on ports 80 (HTTP) and 443 (HTTPS)
- Keeps traffic organized and auditable

**Note:** Cloud Run has built-in inter-service communication, so services can call each other directly without explicit firewall rules.

---

### 5. **secrets.tf** (Second Part) - IAM Permissions for Secrets
Grants each service permission to read specific secrets.

**What it does:**
```
Grants each service access to secrets:
├── Ingestion → can read openai_key and pinecone_key
├── Retrieval → can read openai_key and pinecone_key
├── Synthesis → can read openai_key and pinecone_key
└── Frontend → (no secrets needed)
```

**Why it's needed:**
- Even though secrets exist, services need explicit permission to read them
- This is the "principle of least privilege" - each service gets only what it needs
- If a service is compromised, attacker can't access all secrets

---

### 6. **services.tf** - The 4 Cloud Run Services
The main file that defines your 4 microservices. This is where most of the deployment logic lives.

**Structure:**
```
Each service definition includes:
├── Container image (docker image to run)
├── Environment variables (config for the service)
├── Resource limits (CPU, memory)
├── Timeout settings (how long to wait for response)
├── Service account (which IAM identity runs the service)
├── IAM bindings (who can invoke this service)
└── Autoscaling config (how many copies to run)
```

**Details for each service:**

#### **A. Ingestion Service (Port 8000)**
- **Public Access**: Yes (`allUsers` can invoke)
- **Memory**: 2GB (PDF processing is memory-intensive)
- **Timeout**: 300 seconds (uploads can be slow)
- **Permissions**: GCS Object Admin (read/write PDFs)

#### **B. Retrieval Service (Port 8001)**
- **Public Access**: No (only called by Synthesis internally)
- **IAM**: Synthesis service account can invoke it
- **Memory**: 2GB (holds retrieved chunks in memory)
- **Timeout**: 60 seconds (searches are fast)

#### **C. Synthesis Service (Port 8002)**
- **Public Access**: No (only called by Frontend internally)
- **IAM**: Frontend service account can invoke it
- **Memory**: 2GB (for LLM context)
- **Timeout**: 60 seconds (LLM response time)
- **Special**: Gets RETRIEVAL_SERVICE_URL injected as environment variable

#### **D. Frontend Service (Port 8003)**
- **Public Access**: Yes (`allUsers` can invoke)
- **Memory**: 2GB
- **Timeout**: 300 seconds (SSE streaming needs long timeout)
- **Special**: Gets SYNTHESIS_SERVICE_URL injected as environment variable

**Why separate services?**
1. **Independent Scaling**: If you get a spike in queries, Synthesis/Retrieval scale without re-deploying Ingestion
2. **Fault Isolation**: Bug in Synthesis doesn't crash Retrieval
3. **Performance**: Ingestion (slow, bursty) doesn't block Retrieval (fast, steady)
4. **Team Ownership**: Different teams can own/maintain each service
5. **Cost**: You only pay for the resources actually needed by each service

---

### 7. **monitoring.tf** - Logging & Alerts
Sets up observability for your services.

**What it does:**
- Creates Cloud Logging sinks (stores service logs)
- Sets up alert policies for:
  - High error rates (5% threshold)
  - High latency (p99 > 10 seconds)

**Why it's needed:**
- Alerts notify you when something goes wrong
- Logs help you debug issues
- Metrics show performance trends

---

### 8. **outputs.tf** - Display Results
After deployment, Terraform outputs important information.

**What it outputs:**
```
├── Service URLs (the public endpoints you'll call)
├── Service accounts (for debugging IAM issues)
├── GCS bucket name (for uploading documents)
└── Test commands (cURL examples)
```

**Example output after `terraform apply`:**
```
ingestion_service_url = "https://rag-ingestion-xyz123.a.run.app"
frontend_service_url  = "https://rag-frontend-xyz456.a.run.app"
gcs_bucket_name       = "my-gcp-project-rag-documents"
```

---

### 9. **terraform.tfvars.example** - Configuration Template
Example file showing what variables you need to set.

**How to use:**
```bash
# 1. Copy the template
cp terraform/terraform.tfvars.example terraform/terraform.tfvars

# 2. Edit with your values
vi terraform/terraform.tfvars

# 3. Deploy
terraform apply
```

---

## The 4 Microservices

### Service 1: Ingestion (Port 8000)
**Job**: Take PDFs, extract text, break into chunks, generate embeddings, store in Pinecone

**Flow**:
```
User uploads PDF → FastAPI receives file → PyPDF2 extracts text →
Split into chunks (500 tokens, 100 overlap) → OpenAI embeddings API →
Batch send to Pinecone → Return success response
```

**Code Entry Point**: [apps/ingestion/app.py](apps/ingestion/app.py)

**Example Request**:
```bash
curl -X POST "https://rag-ingestion-xyz.run.app/api/v1/ingest" \
  -F "file=@document.pdf" \
  -F "user_id=user123"
```

**Why separate?**
- PDF processing is slow and memory-intensive
- Doesn't need to run constantly (bursty workload)
- Can scale independently when batch importing documents

---

### Service 2: Retrieval (Port 8001)
**Job**: Take a query, find similar chunks in Pinecone, return the most relevant ones

**Flow**:
```
Query arrives → OpenAI embedding API → Pinecone vector search →
Deduplicate & rank → Return top 10 chunks with scores
```

**Code Entry Point**: [apps/retrieval/app.py](apps/retrieval/app.py)

**Example Request**:
```bash
curl -X POST "http://rag-retrieval.run.app/api/v1/retrieve" \
  -H "Content-Type: application/json" \
  -d '{"query": "How do I deploy?", "user_id": "user123", "top_k": 10}'
```

**Why separate?**
- Pure search logic - can scale based on query volume
- Called by Synthesis but could be called by other services too
- Easier to update search ranking algorithm independently

---

### Service 3: Synthesis (Port 8002)
**Job**: Call Retrieval service, build a prompt, send to OpenAI LLM, return response

**Flow**:
```
Query arrives → Call Retrieval service → Get chunks →
Build prompt with context → OpenAI chat API →
Extract citations → Return response
```

**Code Entry Point**: [apps/synthesis/app.py](apps/synthesis/app.py)

**Internal Service Call**:
```python
# Synthesis calls Retrieval internally via HTTP
async with httpx.AsyncClient() as client:
    retrieval_response = await client.post(
        f"{settings.retrieval_service_url}/api/v1/retrieve",
        json={"query": query}
    )
```

**Example Request**:
```bash
curl -X POST "http://rag-synthesis.run.app/api/v1/synthesize" \
  -H "Content-Type: application/json" \
  -d '{"query": "How do I deploy?", "user_id": "user123"}'
```

**Why separate?**
- LLM orchestration logic is distinct from search logic
- If LLM fails, Retrieval still works
- Can swap out LLM provider (Claude, Gemini, etc.) without affecting others

---

### Service 4: Frontend (Port 8003)
**Job**: Public-facing endpoint that calls Synthesis and streams response using Server-Sent Events (SSE)

**Flow**:
```
User sends query → Call Synthesis service →
Stream response back to user in real-time (SSE)
```

**Code Entry Point**: [apps/frontend/app.py](apps/frontend/app.py)

**Example Request**:
```bash
curl -N "https://rag-frontend-xyz.run.app/api/v1/query" \
  -H "Content-Type: application/json" \
  -d '{"query": "How do I deploy?", "user_id": "user123"}'

# Response streams back in real-time:
# data: {"token":"The"}
# data: {"token":"deployment"}
# data: {"token":"process"}
```

**Why separate?**
- User-facing API - needs to be scalable and resilient
- Handles streaming (different technical requirements than request/response)
- Can handle authentication/rate-limiting at this layer

---

## GCP Setup Requirements

Before you can deploy with Terraform, you need these GCP resources set up:

### 1. **GCP Project Created**
```bash
# Create a new GCP project
gcloud projects create rag-project-name

# Set as default
gcloud config set project rag-project-name
```

### 2. **APIs Enabled**
```bash
# Enable required APIs
gcloud services enable \
  cloudbuild.googleapis.com \        # Build Docker images
  run.googleapis.com \               # Cloud Run (microservices)
  storage-api.googleapis.com \       # GCS (document storage)
  secretmanager.googleapis.com \     # Secret Manager (API keys)
  logging.googleapis.com \           # Cloud Logging
  monitoring.googleapis.com          # Cloud Monitoring
```

### 3. **Docker Images Built & Pushed to Container Registry**
```bash
# Build each service's Docker image
for service in ingestion retrieval synthesis frontend; do
  docker build -t gcr.io/YOUR_PROJECT_ID/rag-${service}:latest \
    apps/${service}/
  docker push gcr.io/YOUR_PROJECT_ID/rag-${service}:latest
done
```

### 4. **Pinecone Index Created**
- Go to Pinecone console
- Create an index named `portfolio-rag` (or whatever you specify in tfvars)
- Set dimension to 1536 (OpenAI embedding size)
- Note your API key

### 5. **API Keys Obtained**
- **OpenAI**: https://platform.openai.com/api-keys
- **Pinecone**: https://app.pinecone.io

### 6. **Terraform Authenticated to GCP**
```bash
gcloud auth application-default login
```

---

## Why Each Resource Is Needed

| Resource | Purpose | Cost Impact | Why Not Optional |
|----------|---------|-------------|-----------------|
| 4 Cloud Run Services | Run your 4 microservices | Pay per invocation + memory | This is your entire application |
| Secret Manager | Store API keys securely | Minimal (free tier: 6 secrets) | Exposes credentials to code otherwise |
| GCS Bucket | Store uploaded PDFs | Pay per GB stored + operations | Where would you store documents? |
| Service Accounts | IAM identity for each service | Free | Security: each service has minimal permissions |
| VPC Network | Network isolation | Free | Allows firewall rules |
| Firewall Rules | Allow outbound API calls | Free | Services can't reach OpenAI/Pinecone otherwise |
| Cloud Logging | Monitor service health | Minimal (free tier: 50GB/month) | Without logs, you're blind to issues |
| Cloud Monitoring | Alert on errors/latency | Minimal | Know when things break |

---

## Extending for DEV/TEST/PROD

Currently your Terraform deploys one environment. Here's how to support multiple:

### Option 1: Separate Terraform Directories (Recommended for teams)
```
terraform/
├── dev/
│   ├── main.tf
│   └── terraform.tfvars
├── test/
│   ├── main.tf
│   └── terraform.tfvars
└── prod/
    ├── main.tf
    └── terraform.tfvars

modules/
├── services.tf        (shared module)
├── secrets.tf         (shared module)
├── storage.tf         (shared module)
└── variables.tf       (shared module)
```

**Structure:**
```hcl
# dev/main.tf
module "rag" {
  source = "../modules"

  gcp_project_id = "my-project-dev"
  gcp_region = "us-central1"
  environment = "dev"
  memory_per_service = "512Mi"          # Cheaper for dev
  max_instances_per_service = 1         # Don't auto-scale in dev
}

# prod/main.tf
module "rag" {
  source = "../modules"

  gcp_project_id = "my-project-prod"
  gcp_region = "us-central1"
  environment = "prod"
  memory_per_service = "4Gi"            # More resources in prod
  max_instances_per_service = 20        # Auto-scale up to 20
}
```

**Deploy each environment:**
```bash
cd terraform/dev && terraform apply    # Deploy dev
cd terraform/prod && terraform apply   # Deploy prod
```

---

### Option 2: Workspace-Based (Simpler for solo projects)
```bash
# Create workspaces
terraform workspace new dev
terraform workspace new prod

# Deploy dev
terraform workspace select dev
terraform apply -var-file=dev.tfvars

# Deploy prod
terraform workspace select prod
terraform apply -var-file=prod.tfvars
```

**State separation:**
```
terraform.tfstate.d/
├── dev/
│   └── terraform.tfstate
└── prod/
    └── terraform.tfstate
```

---

### Option 3: Environment-Based Variable Overrides (Most flexible)
Keep one Terraform directory, but vary inputs:

```bash
# Deploy dev (low cost)
terraform apply \
  -var="environment=dev" \
  -var="memory_per_service=512Mi" \
  -var="max_instances_per_service=1" \
  -var="gcp_project_id=my-project-dev"

# Deploy prod (high performance)
terraform apply \
  -var="environment=prod" \
  -var="memory_per_service=4Gi" \
  -var="max_instances_per_service=20" \
  -var="gcp_project_id=my-project-prod"
```

---

### Environment-Specific Differences

**Development**
```hcl
memory_per_service = "512Mi"
max_instances_per_service = 1          # Single instance
docker_image_tag = "dev"               # Development branch
# Result: Cheap, fast to deploy, slow responses
```

**Test/Staging**
```hcl
memory_per_service = "2Gi"
max_instances_per_service = 3          # Small scaling
docker_image_tag = "staging"           # Staging branch
# Result: Medium cost, realistic performance testing
```

**Production**
```hcl
memory_per_service = "4Gi"
max_instances_per_service = 20         # Full auto-scaling
docker_image_tag = "v1.0.0"            # Release version
# Result: High cost, high performance, production-ready
```

---

## Extending for Client-Based Deployments

You can deploy separate instances per client with isolation:

### Option 1: Separate GCP Projects (Maximum Isolation)
```
GCP Organization
├── Client A Project
│   ├── rag-ingestion-a
│   ├── rag-retrieval-a
│   ├── rag-synthesis-a
│   ├── rag-frontend-a
│   └── client-a-documents (GCS bucket)
├── Client B Project
│   ├── rag-ingestion-b
│   ├── rag-retrieval-b
│   ├── rag-synthesis-b
│   ├── rag-frontend-b
│   └── client-b-documents (GCS bucket)
└── Client C Project
    └── ...
```

**Deploy per client:**
```bash
for client in a b c; do
  terraform apply \
    -var="gcp_project_id=my-org-client-${client}" \
    -var="service_name_prefix=rag-${client}" \
    -var="gcs_bucket_name=client-${client}-documents"
done
```

**Advantages:**
- Complete isolation (security, billing, compliance)
- Each client has their own Pinecone index
- Failure in one client doesn't affect others

**Disadvantages:**
- Higher operational complexity
- More GCP projects to manage
- Can't share infrastructure costs

---

### Option 2: Single Project, Separate Service Instances (Cost-efficient)
```
GCP Project (My Company)
├── rag-ingestion-client-a
├── rag-retrieval-client-a
├── rag-synthesis-client-a
├── rag-frontend-client-a
│
├── rag-ingestion-client-b
├── rag-retrieval-client-b
├── rag-synthesis-client-b
├── rag-frontend-client-b
│
└── GCS Buckets
    ├── client-a-documents
    ├── client-b-documents
    └── client-c-documents
```

**Terraform approach:**
```hcl
variable "clients" {
  default = ["a", "b", "c"]
}

resource "google_cloud_run_service" "ingestion" {
  for_each = toset(var.clients)

  name = "rag-ingestion-client-${each.key}"

  template {
    spec {
      containers {
        env {
          name  = "CLIENT_ID"
          value = each.key
        }
        env {
          name  = "GCS_BUCKET_NAME"
          value = "client-${each.key}-documents"
        }
      }
    }
  }
}
```

**Deploy all clients:**
```bash
terraform apply -var="clients=[a,b,c]"
```

**Advantages:**
- Shared infrastructure reduces costs
- Easier billing allocation
- Simpler operational model

**Disadvantages:**
- One client's spike affects others (noisy neighbor problem)
- Single point of failure
- Harder to enforce per-client resource limits

---

### Option 3: Single Service Fleet with Tenant Routing (Most advanced)
```
GCP Project
└── Cloud Run Service (single deployment)
    ├── Receives request with client_id header
    ├── Routes to client-specific Pinecone index
    ├── Reads from client-specific GCS bucket
    └── Returns response
```

**This is what your current code supports if you add:**
```hcl
env {
  name  = "PINECONE_INDEX_NAME"
  value = "${var.pinecone_index_name}-${var.client_id}"
}

env {
  name  = "GCS_BUCKET_PREFIX"
  value = "${var.client_id}/"
}
```

**Advantages:**
- Minimal infrastructure (4 services total)
- Easiest to manage
- Lowest cost

**Disadvantages:**
- One client can't scale independently
- All clients share resource limits
- Noisy neighbor problem worse than Option 2

---

### Recommended Approach for Clients

**For SaaS with multiple clients:**
1. Start with **Option 1** (separate projects)
   - Clean billing per client
   - Regulatory compliance easier
   - Security isolation

2. As you scale, move to **Option 2** (shared project, separate services)
   - When you have 10+ clients
   - When you need tighter cost control

3. Finally **Option 3** (multi-tenant)
   - When you have 50+ clients
   - When infrastructure coordination is critical

---

## Summary: Implementation Roadmap

### Current State
- ✅ 4 independent microservices
- ✅ Proper IAM/security practices
- ✅ Secret management
- ✅ Single environment deployment

### Next Steps (Recommended Priority)

**Phase 1: Confidence (No code changes)**
- [ ] Deploy to dev environment with lower resource limits
- [ ] Test all 4 services work together
- [ ] Document deployment manual steps

**Phase 2: Multi-Environment (Terraform refactor)**
- [ ] Move services to `modules/` directory
- [ ] Create `terraform/dev`, `terraform/test`, `terraform/prod` directories
- [ ] Test deploying to multiple environments
- [ ] Document per-environment differences

**Phase 3: Multi-Tenant (Optional)**
- [ ] Decide between separate projects vs. shared project
- [ ] If shared project: Parameterize client ID
- [ ] Update apps to support client-based Pinecone indices
- [ ] Add client ID to logging/monitoring

**Phase 4: Advanced**
- [ ] GitOps pipeline (auto-deploy on git push)
- [ ] Blue-green deployments (zero-downtime updates)
- [ ] Disaster recovery setup (backups, failover)

---

## Potential Issues & Fixes

### Issue 1: Networking Variable Reference
**Problem**: In `networking.tf` you're using `var.service_name` but it's not defined (should be `var.service_name_prefix`)

**Location**: [terraform/networking.tf](terraform/networking.tf)

**Fix**:
```terraform
# Change from:
name = "${var.service_name}-network"

# To:
name = "${var.service_name_prefix}-network"
```

### Issue 2: Storage IAM References Non-Existent Service Account
**Problem**: In `storage.tf` you reference `google_service_account.rag_api.email` but this service account isn't defined

**Location**: [terraform/storage.tf](terraform/storage.tf)

**Fix**: Either remove the IAM binding (not needed) or create the service account in `services.tf`.

---

## Quick Reference: Deployment Checklist

Before running `terraform apply`:

- [ ] GCP project created: `gcloud projects list`
- [ ] APIs enabled: `gcloud services list --enabled`
- [ ] Docker images built: `gcloud container images list`
- [ ] Pinecone index created: Check https://app.pinecone.io
- [ ] API keys obtained: OpenAI and Pinecone
- [ ] `terraform/terraform.tfvars` filled in
- [ ] Authenticated: `gcloud auth application-default login`

Deploy:
```bash
cd terraform
terraform init
terraform plan     # Review what will be created
terraform apply    # Create resources
terraform output   # See service URLs
```

---

## Key Takeaways

1. **Each microservice has a purpose**: Ingestion (storage), Retrieval (search), Synthesis (LLM), Frontend (API)
2. **Services scale independently**: Better performance than monolith
3. **Security by default**: Secrets encrypted, each service gets minimal IAM permissions
4. **Cost optimization**: You pay for what you use; can scale down in dev
5. **Multi-environment ready**: Current code supports dev/test/prod with variable overrides
6. **Multi-tenant ready**: Current design supports client-based deployments

