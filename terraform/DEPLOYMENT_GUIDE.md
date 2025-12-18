# Cloud Run Deployment Guide

Complete step-by-step instructions for deploying the 4-microservice RAG architecture to Google Cloud Run.

## Prerequisites

Before starting, you need:

1. **GCP Account & Project**
   - Create a GCP account: https://cloud.google.com
   - Create a new GCP project
   - Enable billing

2. **API Keys**
   - OpenAI API key: https://platform.openai.com/api-keys
   - Pinecone API key: https://www.pinecone.io (create index named `portfolio-rag`)

3. **Tools**
   - Terraform: https://www.terraform.io/downloads.html
   - Google Cloud SDK: https://cloud.google.com/sdk/docs/install
   - Docker: https://www.docker.com/products/docker-desktop

4. **Authentication**
   - Log in to GCP: `gcloud auth login`
   - Set project: `gcloud config set project YOUR_PROJECT_ID`

## Step 1: Build Docker Images

Build 4 Docker images (one for each service) and push to Google Container Registry.

### 1a. Enable Container Registry API

```bash
gcloud services enable containerregistry.googleapis.com
gcloud services enable cloudbuild.googleapis.com
```

### 1b. Configure Docker Authentication

```bash
gcloud auth configure-docker
```

### 1c. Build and Push Each Service

Replace `YOUR_PROJECT_ID` with your actual GCP project ID.

**Ingestion Service:**
```bash
cd apps/ingestion
docker build -t gcr.io/YOUR_PROJECT_ID/rag-ingestion:latest .
docker push gcr.io/YOUR_PROJECT_ID/rag-ingestion:latest
cd ../..
```

**Retrieval Service:**
```bash
cd apps/retrieval
docker build -t gcr.io/YOUR_PROJECT_ID/rag-retrieval:latest .
docker push gcr.io/YOUR_PROJECT_ID/rag-retrieval:latest
cd ../..
```

**Synthesis Service:**
```bash
cd apps/synthesis
docker build -t gcr.io/YOUR_PROJECT_ID/rag-synthesis:latest .
docker push gcr.io/YOUR_PROJECT_ID/rag-synthesis:latest
cd ../..
```

**Frontend Service:**
```bash
cd apps/frontend
docker build -t gcr.io/YOUR_PROJECT_ID/rag-frontend:latest .
docker push gcr.io/YOUR_PROJECT_ID/rag-frontend:latest
cd ../..
```

**Verify Images:**
```bash
gcloud container images list
```

You should see 4 images:
- `gcr.io/YOUR_PROJECT_ID/rag-ingestion:latest`
- `gcr.io/YOUR_PROJECT_ID/rag-retrieval:latest`
- `gcr.io/YOUR_PROJECT_ID/rag-synthesis:latest`
- `gcr.io/YOUR_PROJECT_ID/rag-frontend:latest`

## Step 2: Prepare Terraform Configuration

### 2a. Copy Variables File

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
```

### 2b. Edit terraform.tfvars

```bash
nano terraform.tfvars
# or use your favorite editor
```

Update these values:

```hcl
gcp_project_id = "YOUR_PROJECT_ID"
gcp_region = "us-central1"
gcs_bucket_name = "YOUR_UNIQUE_BUCKET_NAME"  # Must be globally unique
docker_registry = "gcr.io"
docker_image_tag = "latest"
service_name_prefix = "rag"
```

**IMPORTANT:** For API keys, use environment variables instead of putting them in tfvars:

```bash
export TF_VAR_openai_api_key="sk-..."
export TF_VAR_pinecone_api_key="..."
```

### 2c. Verify Variables

```bash
terraform plan
```

This shows what will be created. Review the 4 Cloud Run services, 2 secrets, and 1 GCS bucket.

## Step 3: Deploy Infrastructure

### 3a. Initialize Terraform

```bash
terraform init
```

This downloads the Google Cloud provider plugin.

### 3b. Review Deployment Plan

```bash
terraform plan -out=tfplan
```

### 3c. Apply Configuration

```bash
terraform apply tfplan
```

**This will:**
- Create 4 Cloud Run services (ingestion, retrieval, synthesis, frontend)
- Create Secret Manager secrets for API keys
- Create a GCS bucket for PDFs
- Set up IAM permissions for each service
- Configure service-to-service communication

This typically takes 2-3 minutes.

### 3d. Get Service URLs

After deployment completes:

```bash
terraform output service_urls
```

You'll see:

```
{
  "frontend" = {
    "port" = 8003
    "purpose" = "Public-facing SSE streaming endpoint"
    "url" = "https://rag-frontend-abc123.run.app"
  }
  "ingestion" = {
    "port" = 8000
    "purpose" = "PDF upload, text extraction, embedding generation"
    "url" = "https://rag-ingestion-def456.run.app"
  }
  "retrieval" = {
    "port" = 8001
    "purpose" = "Vector similarity search, ranking, deduplication"
    "url" = "https://rag-retrieval-ghi789.run.app"
  }
  "synthesis" = {
    "port" = 8002
    "purpose" = "LLM orchestration, response generation, citations"
    "url" = "https://rag-synthesis-jkl012.run.app"
  }
}
```

## Step 4: Test Services

### 4a. Test Health Endpoints

Each service exposes `/api/v1/health`:

```bash
# Get URLs
INGESTION_URL=$(terraform output -json service_urls | jq -r '.ingestion.url')
FRONTEND_URL=$(terraform output -json service_urls | jq -r '.frontend.url')

# Test ingestion
curl $INGESTION_URL/api/v1/health

# Test frontend
curl $FRONTEND_URL/api/v1/health
```

### 4b. Test Full Pipeline

**Upload a PDF:**
```bash
curl -X POST -F "file=@sample.pdf" \
  $INGESTION_URL/api/v1/ingest
```

**Query with streaming:**
```bash
curl -N -X POST \
  -H "Content-Type: application/json" \
  -d '{"query":"Your question here"}' \
  $FRONTEND_URL/api/v1/query
```

### 4c. View Logs

Check logs for each service:

```bash
# Ingestion logs
gcloud run logs read rag-ingestion --limit=50

# Frontend logs
gcloud run logs read rag-frontend --limit=50
```

## Step 5: Verify Configuration

### 5a. Check Cloud Run Services

```bash
gcloud run services list
```

Should show 4 services:
- `rag-ingestion` (Port 8000)
- `rag-retrieval` (Port 8001)
- `rag-synthesis` (Port 8002)
- `rag-frontend` (Port 8003)

### 5b. Check Secrets

```bash
gcloud secrets list
```

Should show:
- `rag-openai-key`
- `rag-pinecone-key`

### 5c. Check GCS Bucket

```bash
gsutil ls
```

Should show your bucket (e.g., `gs://YOUR_BUCKET_NAME/`)

## Service Architecture on Cloud Run

### Data Flow

```
User Request
    ↓
Frontend (Cloud Run)
    ↓
Synthesis (Cloud Run)
    ↓
Retrieval (Cloud Run)
    ↓
Pinecone (External)
    ↓
Synthesis generates response
    ↓
Frontend streams response (SSE)
    ↓
User receives answer
```

### Service-to-Service Communication

Services call each other via internal Cloud Run URLs:

```
Frontend → Synthesis: http://rag-synthesis.run.app
Synthesis → Retrieval: http://rag-retrieval.run.app
Retrieval → Pinecone: External API
```

All internal communication is private and fast (same VPC).

### Scaling Behavior

Each service auto-scales independently:

| Service | Min | Max | Scales By |
|---------|-----|-----|-----------|
| Ingestion | 0 | 10 | Request rate |
| Retrieval | 0 | 10 | Request rate |
| Synthesis | 0 | 10 | Request rate |
| Frontend | 0 | 10 | Request rate |

**Cost Optimization:**
- Services only run when needed (min = 0)
- Each scales based on its own load
- No idle instances paying for nothing

## Configuration Changes

### Update Service Memory/CPU

Edit `terraform.tfvars`:

```hcl
cpu_per_service = "2"           # Increase CPU
memory_per_service = "4Gi"      # Increase memory
max_instances_per_service = 20  # Allow more instances
```

Apply changes:

```bash
terraform apply
```

### Update Docker Image

Build new image and push:

```bash
docker build -t gcr.io/YOUR_PROJECT_ID/rag-ingestion:v2.0 apps/ingestion/
docker push gcr.io/YOUR_PROJECT_ID/rag-ingestion:v2.0
```

Update `terraform.tfvars`:

```hcl
docker_image_tag = "v2.0"
```

Apply:

```bash
terraform apply
```

### Add/Remove Secrets

Update Secret Manager:

```bash
echo -n "new-api-key" | gcloud secrets versions add rag-openai-key --data-file=-
```

## Troubleshooting

### Service won't start

**Check logs:**
```bash
gcloud run logs read rag-ingestion --limit=100
```

**Common issues:**
- Image not found: Verify image exists in Container Registry
- Environment variables missing: Check Secret Manager has values
- Memory/CPU too low: Increase in terraform.tfvars

### Service-to-service calls failing

**Check firewall:**
```bash
gcloud compute firewall-rules list
```

**Check IAM:**
```bash
gcloud projects get-iam-policy YOUR_PROJECT_ID
```

### High memory usage

**Check metrics:**
```bash
gcloud monitoring dashboards list
```

**Solutions:**
- Reduce memory in terraform.tfvars
- Check for memory leaks in code
- Reduce max_instances_per_service

### Costs higher than expected

**Check Cloud Run metrics:**
- Go to Cloud Console → Cloud Run
- Review memory allocation and instance count
- Review OpenAI/Pinecone API usage

**Optimization:**
- Reduce CPU/memory per service
- Reduce max_instances_per_service
- Enable caching in Retrieval service

## Monitoring & Alerts

### View Metrics

```bash
# Cloud Console
gcloud compute instances list  # View instances

# Cloud Logging
gcloud logging read "resource.type=cloud_run_revision" --limit=50
```

### Set Up Alerts

In GCP Console:
1. Go to Monitoring → Alerting → Create Policy
2. Select metric: `cloud_run_revision/request_count`
3. Set threshold and notification channel

## Cleanup

To tear down all resources:

```bash
cd terraform
terraform destroy
```

This removes:
- 4 Cloud Run services
- 2 secrets
- GCS bucket (with all PDFs)
- Service accounts
- IAM permissions

**WARNING:** This is irreversible for the GCS bucket contents.

## Production Checklist

Before going to production:

- [ ] Enable Cloud Armor for DDoS protection
- [ ] Set up authentication (Cloud Identity-Aware Proxy)
- [ ] Configure rate limiting
- [ ] Enable audit logging
- [ ] Set up monitoring and alerts
- [ ] Use specific image tags (not "latest")
- [ ] Set up backup for GCS bucket
- [ ] Use production-grade database (currently Pinecone)
- [ ] Enable VPC Service Controls
- [ ] Set up disaster recovery plan

## Cost Analysis

**Estimated monthly costs (moderate usage):**

| Component | Cost |
|-----------|------|
| Cloud Run (4 services) | $80-120 |
| Secret Manager | $5 |
| GCS Storage | $5-10 |
| Cloud Logging | $5-10 |
| **Subtotal** | **$100-150** |
| OpenAI API | $20-100* |
| Pinecone | $25-100* |
| **TOTAL** | **$145-350** |

*Varies based on usage

## Next Steps

1. ✅ Deploy to GCP
2. ✅ Test all 4 services
3. ✅ Monitor metrics and costs
4. ⏭️ Add authentication
5. ⏭️ Set up custom domain (Cloud CDN)
6. ⏭️ Implement caching layer
7. ⏭️ Add request logging for analytics

---

**Need Help?**
- Terraform docs: https://www.terraform.io/docs
- GCP Cloud Run docs: https://cloud.google.com/run/docs
- GCP Terraform provider: https://registry.terraform.io/providers/hashicorp/google/latest
