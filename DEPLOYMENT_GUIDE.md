# Complete GCP Deployment Guide

This guide walks through deploying your 4-microservice RAG system to Google Cloud Platform.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Step-by-Step Deployment](#step-by-step-deployment)
3. [Testing the Deployment](#testing-the-deployment)
4. [Troubleshooting](#troubleshooting)
5. [Cost Estimation](#cost-estimation)

---

## Prerequisites

### GCP Account & Project
- [ ] Google Cloud account created (https://cloud.google.com)
- [ ] GCP Project created
- [ ] Billing enabled on the project

### Required API Keys
- [ ] OpenAI API key (https://platform.openai.com/api-keys)
- [ ] Pinecone API key (https://app.pinecone.io)
- [ ] Pinecone index created with 1536 dimensions

### Local Environment
- [ ] `gcloud` CLI installed and authenticated
- [ ] `terraform` installed (v1.0+)
- [ ] `docker` installed and running
- [ ] `git` to clone/manage the repo

### Install Required Tools

**macOS (using Homebrew)**:
```bash
brew install google-cloud-sdk terraform docker
gcloud init
```

**Linux (Ubuntu/Debian)**:
```bash
# Google Cloud SDK
echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" | \
  sudo tee -a /etc/apt/sources.list.d/google-cloud-sdk.list
curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | \
  sudo apt-key --keyring /usr/share/keyrings/cloud.google.gpg add -

sudo apt-get update && sudo apt-get install google-cloud-sdk terraform docker.io
sudo usermod -aG docker $USER  # Allow docker without sudo

gcloud init
```

---

## Step-by-Step Deployment

### Phase 1: GCP Project Setup (One-time)

#### 1.1 Create GCP Project
```bash
# Set your project name
export PROJECT_NAME="rag-project"
export PROJECT_ID="rag-project-$(date +%s)"  # Unique ID

# Create project
gcloud projects create $PROJECT_ID --name=$PROJECT_NAME

# Set as default
gcloud config set project $PROJECT_ID

# Display confirmation
gcloud config list
```

**Expected output:**
```
[core]
project = rag-project-1702900000
```

---

#### 1.2 Enable Required APIs

```bash
# Enable all required APIs
gcloud services enable \
  cloudbuild.googleapis.com \
  run.googleapis.com \
  storage-api.googleapis.com \
  secretmanager.googleapis.com \
  logging.googleapis.com \
  monitoring.googleapis.com \
  compute.googleapis.com

# Verify they're enabled
gcloud services list --enabled | grep -E "run|storage|secret|logging|compute"
```

**Expected output:**
```
compute.googleapis.com
logging.googleapis.com
run.googleapis.com
secretmanager.googleapis.com
storage-api.googleapis.com
```

---

#### 1.3 Enable Artifact Registry & Push Docker Images

Create the Docker images and push to Google Container Registry:

```bash
# Get project ID
export PROJECT_ID=$(gcloud config get-value project)
export GCR_REPO="gcr.io/${PROJECT_ID}"

# Authenticate Docker to GCR
gcloud auth configure-docker

# Build and push each service
for service in ingestion retrieval synthesis frontend; do
  echo "Building rag-${service}..."

  docker build -t ${GCR_REPO}/rag-${service}:latest \
    -f apps/${service}/Dockerfile \
    .

  docker push ${GCR_REPO}/rag-${service}:latest

  echo "✓ Pushed ${GCR_REPO}/rag-${service}:latest"
done

# Verify images are in registry
gcloud container images list
```

**This will take 5-10 minutes depending on your internet speed.**

---

#### 1.4 Set Up Pinecone

1. Go to https://app.pinecone.io
2. Create new index:
   - **Name**: `portfolio-rag` (or whatever you choose)
   - **Dimension**: `1536` (OpenAI embedding size)
   - **Metric**: `cosine`
   - **Pod type**: Starter (free tier)
3. Wait for index to be created (~2 minutes)
4. Copy your **API Key** and **Environment** (e.g., `us-east1-aws`)

---

### Phase 2: Terraform Deployment

#### 2.1 Prepare Terraform Variables

```bash
cd terraform

# Copy example to actual file
cp terraform.tfvars.example terraform.tfvars

# Edit with your values
vi terraform.tfvars
```

Fill in these values:
```hcl
gcp_project_id        = "YOUR_PROJECT_ID"    # From step 1.1
gcp_region           = "us-central1"

openai_api_key       = "sk-..."              # From https://platform.openai.com/api-keys
pinecone_api_key     = "..."                 # From Pinecone console
pinecone_index_name  = "portfolio-rag"       # What you created in 1.4

gcs_bucket_name      = "rag-documents-${PROJECT_ID}"  # Must be globally unique

docker_registry      = "gcr.io"
docker_image_tag     = "latest"

service_name_prefix  = "rag"
environment          = "production"

cpu_per_service      = "1"
memory_per_service   = "2Gi"
max_instances_per_service = 10
```

**Important**: Don't commit `terraform.tfvars` to git (it contains secrets). Use `.gitignore`:
```bash
echo "terraform.tfvars" >> .gitignore
git add .gitignore
```

---

#### 2.2 Authenticate Terraform to GCP

```bash
# This creates credentials that Terraform will use
gcloud auth application-default login

# If you're in a container or CI/CD, use service account instead:
# gcloud auth activate-service-account --key-file=path/to/key.json
```

---

#### 2.3 Fix Terraform Bugs (CRITICAL)

Before deploying, you must fix 2 bugs in the Terraform code. See [TERRAFORM_BUGS.md](TERRAFORM_BUGS.md) for details.

Quick fix:
```bash
# Fix 1: networking.tf - replace var.service_name with var.service_name_prefix
sed -i 's/${var.service_name}/${var.service_name_prefix}/g' terraform/networking.tf

# Fix 2: storage.tf - remove or fix the rag_api reference
# (See TERRAFORM_BUGS.md for details on which option to choose)
```

---

#### 2.4 Initialize & Validate Terraform

```bash
# From terraform/ directory
terraform init

# Validate configuration
terraform validate
```

**Expected output for validate:**
```
Success! The configuration is valid.
```

---

#### 2.5 Preview Deployment

```bash
# See what will be created
terraform plan -out=tfplan

# This will output all resources to be created
# Review carefully before proceeding
```

**Should show something like:**
```
Plan: 28 to add, 0 to change, 0 to destroy.
```

---

#### 2.6 Deploy to GCP

```bash
# Deploy (this takes 5-10 minutes)
terraform apply tfplan

# Wait for all resources to be created...
```

**What you're waiting for:**
- ✓ Secret Manager secrets created
- ✓ GCS bucket created
- ✓ 4 Cloud Run services deployed
- ✓ IAM roles assigned
- ✓ Monitoring/logging configured

---

#### 2.7 Get Service URLs

After deployment completes:

```bash
# Display all service URLs and test commands
terraform output

# Or get specific outputs
terraform output ingestion_service_url
terraform output frontend_service_url
terraform output gcs_bucket_name
```

**Expected output:**
```
ingestion_service_url = "https://rag-ingestion-xyz123.a.run.app"
retrieval_service_url = "https://rag-retrieval-xyz456.a.run.app"
synthesis_service_url = "https://rag-synthesis-xyz789.a.run.app"
frontend_service_url  = "https://rag-frontend-abc000.a.run.app"
gcs_bucket_name       = "rag-documents-rag-project-1702900000"
```

---

### Phase 3: Create `.env` File for Local Testing

Create a file in your project root with the service URLs for easy reference:

```bash
cat > .env << 'EOF'
# GCP Deployment URLs
INGESTION_URL="https://rag-ingestion-xyz123.a.run.app"
RETRIEVAL_URL="https://rag-retrieval-xyz456.a.run.app"
SYNTHESIS_URL="https://rag-synthesis-xyz789.a.run.app"
FRONTEND_URL="https://rag-frontend-abc000.a.run.app"
GCS_BUCKET="rag-documents-rag-project-1702900000"

# API Keys
OPENAI_API_KEY="sk-..."
PINECONE_API_KEY="..."
EOF
```

---

## Testing the Deployment

### Test 1: Health Checks (All Services)

```bash
source .env

# Test Ingestion health
curl ${INGESTION_URL}/api/v1/health

# Test Retrieval health
curl ${RETRIEVAL_URL}/api/v1/health

# Test Synthesis health
curl ${SYNTHESIS_URL}/api/v1/health

# Test Frontend health
curl ${FRONTEND_URL}/api/v1/health
```

**Expected response:**
```json
{"status": "healthy"}
```

---

### Test 2: Upload a Document

Create a sample PDF or use an existing one:

```bash
# Upload using Ingestion service
curl -X POST ${INGESTION_URL}/api/v1/ingest \
  -F "file=@/path/to/document.pdf" \
  -F "user_id=test-user"
```

**Expected response:**
```json
{
  "status": "success",
  "chunks": 42,
  "vectors_stored": 42
}
```

---

### Test 3: Query the System

Query through the Frontend service (SSE streaming):

```bash
# Query and stream response
curl -N -X POST ${FRONTEND_URL}/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is this document about?",
    "user_id": "test-user"
  }'
```

**Expected response** (streaming):
```
data: {"token":"The"}
data: {"token":"document"}
data: {"token":"discusses"}
...
```

---

### Test 4: Direct Synthesis Call

Test the Synthesis service directly:

```bash
curl -X POST ${SYNTHESIS_URL}/api/v1/synthesize \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are the main topics?",
    "user_id": "test-user"
  }'
```

**Expected response:**
```json
{
  "response": "The main topics are...",
  "citations": [
    {
      "text": "quoted text",
      "source": "document.pdf",
      "page": 1
    }
  ]
}
```

---

### Test 5: View Logs

```bash
# View logs for all services
gcloud logging read "resource.type=cloud_run_revision" \
  --limit 50 \
  --format json

# Or view in Cloud Console
gcloud logging read resource.labels.service_name=rag-ingestion
gcloud logging read resource.labels.service_name=rag-retrieval
gcloud logging read resource.labels.service_name=rag-synthesis
gcloud logging read resource.labels.service_name=rag-frontend
```

---

## Troubleshooting

### Issue 1: "API not enabled" Error

**Error message:**
```
ERROR: (gcloud.services.enable) User does not have permission to enable APIs
```

**Solution**: Use a project where you have Editor role, or ask your GCP admin to enable the APIs.

---

### Issue 2: Docker Image Not Found

**Error message:**
```
ImagePullBackOff: Error response from daemon: manifest not found
```

**Solution**: Docker image wasn't pushed to GCR. Run:
```bash
docker push gcr.io/YOUR_PROJECT_ID/rag-ingestion:latest
```

---

### Issue 3: Terraform Error: "Undefined Variable"

**Error message**:
```
Error: Reference to undefined variable: var.service_name
```

**Solution**: You didn't fix the Terraform bugs. See [TERRAFORM_BUGS.md](TERRAFORM_BUGS.md).

---

### Issue 4: "Permission Denied" on Secret Access

**Error message**:
```
AccessDenied: Permission denied on secretmanager.secretAccessor
```

**Solution**: Service account doesn't have permission to read secrets. Wait 30 seconds for IAM propagation, then try again:
```bash
sleep 30
gcloud logging read resource.labels.service_name=rag-ingestion --limit 5 --format json
```

---

### Issue 5: High Latency or Timeout

**Problem**: Services are timing out (300s timeout exceeded)

**Possible causes:**
1. Insufficient memory: Increase `memory_per_service` to "4Gi"
2. Cold starts: Terraform deploy just finished, allow 1-2 minutes
3. External API slow: OpenAI or Pinecone API is slow

**Solution**:
```bash
# Update resources
terraform apply -var="memory_per_service=4Gi"

# Or wait for services to warm up
sleep 120 && curl ${FRONTEND_URL}/api/v1/health
```

---

### Issue 6: "Service account not found"

**Error during Terraform apply**:
```
Error: googleapi: Error 404: Service account ... not found
```

**Solution**: You may have run `terraform destroy` while secrets were still referencing the service account. Fix by:
```bash
terraform destroy -auto-approve
terraform apply
```

---

## Cost Estimation

### Monthly Cost Breakdown

Based on typical usage:

| Service | Resource | Cost/Month |
|---------|----------|-----------|
| Cloud Run (Ingestion) | 100K invocations × 2GB × 60s | ~$10 |
| Cloud Run (Retrieval) | 10K invocations × 2GB × 5s | ~$1 |
| Cloud Run (Synthesis) | 10K invocations × 2GB × 30s | ~$5 |
| Cloud Run (Frontend) | 10K invocations × 2GB × 60s | ~$10 |
| **Compute Subtotal** | | **~$26** |
| GCS Storage | 100 PDFs × 1MB avg = 100GB | ~$2 |
| Secret Manager | 2 secrets | ~$0 (free tier) |
| Cloud Logging | ~1GB logs | ~$0 (free tier) |
| **Storage Subtotal** | | **~$2** |
| **External APIs** | OpenAI embeddings + Pinecone | **~$50-500** |
| **TOTAL** | | **~$80-530/month** |

### Cost Optimization Tips

1. **Use Preemptible VMs?** Not available for Cloud Run
2. **Reduce memory**: 2GB → 512MB (only if not needed)
3. **Reduce max instances**: 10 → 3 (for dev/test)
4. **Use dev environment**: Lower resources for non-production
5. **Batch embeddings**: Reduces OpenAI API calls
6. **Cache vectors**: Reduces Pinecone queries

---

## Cleanup

To delete all GCP resources and stop billing:

```bash
cd terraform

# Remove all resources
terraform destroy

# Confirm by typing "yes"
```

**This will delete:**
- ✓ 4 Cloud Run services
- ✓ GCS bucket
- ✓ Service accounts
- ✓ Secrets
- ✓ Monitoring/logging

**This will NOT delete:**
- ✗ GCP Project (delete manually in Cloud Console)
- ✗ Pinecone index (delete manually in Pinecone console)

---

## Next Steps

1. ✅ Deploy to development environment
2. ✅ Test all services work together
3. ✅ Upload sample documents
4. ✅ Run test queries
5. ⬜ Set up monitoring/alerting
6. ⬜ Configure CI/CD pipeline
7. ⬜ Deploy to production environment
8. ⬜ Set up backup strategy

---

## Getting Help

### Check Service Logs
```bash
# Recent errors in any service
gcloud logging read --limit 50 --format short

# Service-specific logs
gcloud logging read "resource.labels.service_name=rag-ingestion" --limit 20
```

### Check Service Status
```bash
# List all Cloud Run services
gcloud run services list

# Detailed info about one service
gcloud run services describe rag-ingestion --region us-central1
```

### Debug Network Issues
```bash
# Test if you can reach external APIs
curl https://api.openai.com
curl https://api.pinecone.io
```

---

## Summary

| Step | Command | Time |
|------|---------|------|
| 1. Create project | `gcloud projects create` | 1 min |
| 2. Enable APIs | `gcloud services enable` | 2 min |
| 3. Build images | `docker build && docker push` | 5 min |
| 4. Setup Terraform | `cp terraform.tfvars.example terraform.tfvars` | 2 min |
| 5. Deploy | `terraform apply` | 10 min |
| 6. Test | `curl ${FRONTEND_URL}` | 5 min |
| **Total** | | **25 min** |

Once deployed, you'll have:
- ✅ 4 independent microservices running
- ✅ Automatic scaling based on traffic
- ✅ Secure API key management
- ✅ Document storage with versioning
- ✅ Monitoring and logging
- ✅ Public-facing API endpoint

