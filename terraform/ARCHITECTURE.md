# Terraform Architecture for 4-Microservice RAG

This document explains how the Terraform configuration implements the 4-microservice architecture on Google Cloud Run.

## File Organization

```
terraform/
├── main.tf                    # Provider configuration
├── variables.tf               # Input variables
├── services.tf               # 4 Cloud Run services (NEW)
├── secrets.tf                # Secret Manager
├── storage.tf                # GCS bucket
├── networking.tf             # VPC & firewall
├── monitoring.tf             # Cloud Logging
├── outputs.tf                # Output URLs
├── terraform.tfvars.example  # Example variables
├── README.md                 # Architecture overview
├── DEPLOYMENT_GUIDE.md       # Step-by-step guide
├── ARCHITECTURE.md           # This file
├── cloud_run.tf.old          # Deprecated (old monolithic)
└── .terraform/               # Generated (terraform init)
```

## Key Files Explained

### 1. services.tf (NEW - Core Architecture)

Defines all 4 Cloud Run services with detailed comments:

**Ingestion Service**
- Listens on port 8000
- Processes PDFs, generates embeddings
- Service account: `rag-ingestion-sa`
- IAM: GCS Admin, Secret access
- Timeout: 300s (long for uploads)
- Memory: 2GB (for PDF processing)

**Retrieval Service**
- Listens on port 8001
- Vector similarity search
- Service account: `rag-retrieval-sa`
- IAM: Secret access
- Timeout: 60s (fast searches)
- Called by Synthesis service

**Synthesis Service**
- Listens on port 8002
- LLM orchestration
- Service account: `rag-synthesis-sa`
- IAM: Secret access
- Timeout: 60s
- Calls Retrieval service (internal URL)

**Frontend Service**
- Listens on port 8003
- Public-facing endpoint
- Service account: `rag-frontend-sa`
- IAM: Cloud Logging
- Timeout: 300s (for SSE streaming)
- Calls Synthesis service (internal URL)

### 2. variables.tf (Configuration)

Defines all input variables with descriptions:

```hcl
# Required
gcp_project_id          # Your GCP project
openai_api_key          # OpenAI API key
pinecone_api_key        # Pinecone API key
gcs_bucket_name         # GCS bucket name

# Configuration
service_name_prefix     # "rag" → rag-ingestion, rag-retrieval, etc.
docker_image_tag        # "latest" or specific version
docker_registry         # "gcr.io" for Google Container Registry

# Resources
cpu_per_service         # 1 vCPU per service
memory_per_service      # 2GB per service
max_instances_per_service  # Auto-scaling limit (10)
```

### 3. secrets.tf (API Key Management)

Creates Secret Manager secrets (shared by all services):

```
rag-openai-key   → accessed by Ingestion, Retrieval, Synthesis
rag-pinecone-key → accessed by Ingestion, Retrieval, Synthesis
```

Each service has IAM permissions to access its needed secrets.

### 4. storage.tf (Document Storage)

Creates GCS bucket:

```
gs://YOUR_BUCKET_NAME/
├── pdfs/      → Uploaded PDF files
├── chunks/    → Extracted text chunks
└── metadata/  → Chunk metadata (JSON)
```

Accessed by Ingestion service (only) via IAM.

### 5. outputs.tf (Deployment Info)

Exports important values:

```hcl
ingestion_service_url  → https://rag-ingestion-xxx.run.app
retrieval_service_url  → https://rag-retrieval-xxx.run.app
synthesis_service_url  → https://rag-synthesis-xxx.run.app
frontend_service_url   → https://rag-frontend-xxx.run.app

service_urls           → JSON with all URLs and purposes
test_commands          → Example cURL commands
service_accounts       → Service account emails
```

## How Services Connect

### External Access

**Public endpoints (unauthenticated):**
- Frontend: `https://rag-frontend-xxx.run.app` (user entry point)
- Ingestion: `https://rag-ingestion-xxx.run.app` (PDF upload)

**Private endpoints (service-to-service):**
- Retrieval: Not directly exposed
- Synthesis: Not directly exposed

### Internal Service-to-Service Communication

Terraform enables internal communication by:

1. **Same VPC:** All services in same GCP region/VPC
2. **Service Accounts:** Each service has unique service account
3. **IAM Permissions:** Services granted `roles/run.invoker` to call each other

**Data Flow:**

```
Frontend
  ↓ (calls)
Synthesis (via http://rag-synthesis.run.app)
  ↓ (calls)
Retrieval (via http://rag-retrieval.run.app)
  ↓ (calls)
Pinecone (external REST API)
  ↓
Response back through chain
```

**URLs:**
- Frontend → Synthesis: `http://rag-synthesis.run.app`
- Synthesis → Retrieval: `http://rag-retrieval.run.app`

These internal URLs are resolved by Cloud Run's internal DNS and routed efficiently.

## Resource Dependencies

Terraform ensures correct deployment order:

```
1. Create secrets (openai-key, pinecone-key)
   ↓
2. Create service accounts (4x)
   ↓
3. Create Cloud Run services (4x)
   - Each service depends on its secrets
   - Each service has its service account
   ↓
4. Configure IAM permissions
   - Ingestion → GCS Admin
   - All → Secret Manager access
   - Synthesis ← allows Synthesis to be called by Frontend
   - Retrieval ← allows Retrieval to be called by Synthesis
   ↓
5. Create GCS bucket
```

Terraform automatically manages these dependencies using `depends_on` blocks.

## Scaling Configuration

Each service scales independently:

```hcl
max_instances_per_service = 10  # Each service can have 1-10 instances
```

Auto-scaling rules (Cloud Run defaults):

| Metric | Threshold | Action |
|--------|-----------|--------|
| CPU | 80% | Scale up |
| Memory | 80% | Scale up |
| Request concurrency | 80 | Scale up |
| Idle time | 15 min | Scale down to 0 |

**Cost Optimization:**
- Minimum instances = 0 (no cost when idle)
- Services scale independently (Ingestion spike doesn't affect Retrieval)
- Request-based billing (pay per request + compute time)

## Environment Variables

### How They're Set

Each service gets environment variables from:

1. **Static values** (hardcoded in terraform):
```hcl
env {
  name  = "ENVIRONMENT"
  value = var.environment  # "development"
}
```

2. **Secrets from Secret Manager** (resolved at runtime):
```hcl
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

3. **Service-to-service URLs** (generated by Terraform):
```hcl
env {
  name  = "RETRIEVAL_SERVICE_URL"
  value = "http://${google_cloud_run_service.retrieval.name}.run.app"
}
```

### Environment Variables per Service

**Ingestion:**
- `OPENAI_API_KEY` (from Secret Manager)
- `PINECONE_API_KEY` (from Secret Manager)
- `PINECONE_INDEX_NAME`
- `ENVIRONMENT`
- `GCP_PROJECT_ID`

**Retrieval:**
- `OPENAI_API_KEY` (from Secret Manager)
- `PINECONE_API_KEY` (from Secret Manager)
- `PINECONE_INDEX_NAME`
- `ENVIRONMENT`
- `GCP_PROJECT_ID`

**Synthesis:**
- `OPENAI_API_KEY` (from Secret Manager)
- `PINECONE_API_KEY` (from Secret Manager)
- `PINECONE_INDEX_NAME`
- `RETRIEVAL_SERVICE_URL` (set by Terraform)
- `ENVIRONMENT`
- `GCP_PROJECT_ID`

**Frontend:**
- `SYNTHESIS_SERVICE_URL` (set by Terraform)
- `ENVIRONMENT`
- `GCP_PROJECT_ID`

## Security Considerations

### API Keys

**Storage:**
- Secrets stored in Google Secret Manager
- Encrypted at rest
- Never exposed in code or logs
- Rotatable without redeployment

**Access Control:**
- Only services that need them can access
- Per-service IAM permissions
- Audit log available in Cloud Audit Logs

**Best Practice:**
Use environment variables (TF_VAR_*) instead of terraform.tfvars:
```bash
export TF_VAR_openai_api_key="sk-..."
export TF_VAR_pinecone_api_key="..."
terraform apply
```

### Service Accounts

**Least Privilege:**
- Ingestion: Only needs GCS access
- Retrieval: Only needs Secret access
- Synthesis: Only needs Secret access
- Frontend: Only needs Logging access

**Service-to-Service:**
- Frontend can call Synthesis (via IAM)
- Synthesis can call Retrieval (via IAM)
- No other cross-service permissions

### Network Security

- Services in same VPC
- Internal communication encrypted in transit
- Public endpoints (Ingestion, Frontend) available to internet
- No custom firewall rules needed (Cloud Run handles security)

## Cost Breakdown

### Compute (per service per month at 50% average utilization)

| Service | CPU | Memory | ~Cost |
|---------|-----|--------|-------|
| Ingestion | 1 vCPU | 2GB | $25 |
| Retrieval | 1 vCPU | 2GB | $25 |
| Synthesis | 1 vCPU | 2GB | $25 |
| Frontend | 1 vCPU | 2GB | $25 |
| **Subtotal** | | | **$100** |

### Storage & Networking

| Item | ~Cost |
|------|-------|
| GCS (documents) | $5 |
| Secret Manager | $5 |
| Cloud Logging | $10 |
| Data egress (internal) | $0 |
| **Subtotal** | **$20** |

### External APIs

| Service | Typical Monthly |
|---------|-----------------|
| OpenAI (embeddings + LLM) | $50-200 |
| Pinecone (vector storage) | $25-100 |
| **Subtotal** | **$75-300** |

**Total: $195-420 per month** (highly usage-dependent)

## Customization Examples

### Scale Up for Production

```hcl
# terraform.tfvars
cpu_per_service = "2"
memory_per_service = "4Gi"
max_instances_per_service = 20
```

### Regional Deployment

To deploy in different regions:

```bash
terraform apply -var="gcp_region=europe-west1"
```

### Different Container Registry

```hcl
# terraform.tfvars
docker_registry = "us.gcr.io"  # Multi-regional registry
```

## Debugging Terraform

### View Terraform State

```bash
terraform state show
terraform state list
```

### View Generated Plans

```bash
terraform plan -out=tfplan
# Review tfplan before applying
```

### Validate Configuration

```bash
terraform validate
terraform fmt  # Auto-format
```

## Migrating from Single Service

If migrating from old monolithic architecture:

1. **Old state:** Single `rag-api` service
2. **New state:** 4 services `rag-ingestion`, `rag-retrieval`, `rag-synthesis`, `rag-frontend`

To migrate:

```bash
# Destroy old service
terraform destroy  # Or manually delete old service

# Copy terraform.tfvars.example
cp terraform.tfvars.example terraform.tfvars

# Edit with new values

# Deploy new 4-service architecture
terraform apply
```

---

**Key Takeaway:**

The Terraform configuration in `services.tf` is the source of truth for the 4-microservice architecture. Each service is independently defined, scaled, and monitored, enabling efficient resource utilization and easy troubleshooting.
