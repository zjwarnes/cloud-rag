# Terraform Configuration for 4-Microservice RAG on GCP Cloud Run
#
# This configuration deploys 4 independent FastAPI services:
# 1. Ingestion (Port 8000) - PDF processing & embedding
# 2. Retrieval (Port 8001) - Vector search & ranking
# 3. Synthesis (Port 8002) - LLM response generation
# 4. Frontend (Port 8003) - SSE streaming endpoint
#
# File Organization:
# - main.tf (this file): Terraform provider configuration
# - services.tf: Defines the 4 Cloud Run services
# - secrets.tf: Manages API keys in Secret Manager
# - storage.tf: GCS bucket for PDF documents
# - networking.tf: VPC and firewall rules
# - monitoring.tf: Logging and alerting
# - outputs.tf: Output values for deployment
# - variables.tf: Input variable definitions

terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

provider "google" {
  project = var.gcp_project_id
  region  = var.gcp_region
}
