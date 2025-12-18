# Input Variables for 4-Microservice RAG Architecture
# 
# These variables control the deployment of 4 Cloud Run services:
# 1. Ingestion (Port 8000) - PDF processing
# 2. Retrieval (Port 8001) - Vector search
# 3. Synthesis (Port 8002) - LLM responses
# 4. Frontend (Port 8003) - SSE streaming
#
# See terraform.tfvars.example for example values.

# ============================================================================
# GCP Configuration
# ============================================================================

variable "gcp_project_id" {
  description = "GCP Project ID where resources will be deployed"
  type        = string
}

variable "gcp_region" {
  description = "GCP region for deployment (e.g., us-central1, europe-west1)"
  type        = string
  default     = "us-central1"
}

# ============================================================================
# API Keys & Authentication (Sensitive)
# ============================================================================

variable "openai_api_key" {
  description = "OpenAI API key for embeddings and LLM (shared by all services)"
  type        = string
  sensitive   = true
}

variable "pinecone_api_key" {
  description = "Pinecone API key for vector search (shared by all services)"
  type        = string
  sensitive   = true
}

variable "pinecone_index_name" {
  description = "Pinecone index name (must exist before deployment)"
  type        = string
  default     = "portfolio-rag"
}

# ============================================================================
# Storage Configuration
# ============================================================================

variable "gcs_bucket_name" {
  description = "GCS bucket name for storing PDFs (must be globally unique)"
  type        = string
}

# ============================================================================
# Docker Image Configuration
# ============================================================================

variable "docker_registry" {
  description = "Docker registry URL (e.g., gcr.io/[PROJECT_ID])"
  type        = string
  default     = "gcr.io"
}

variable "docker_image_tag" {
  description = "Docker image tag for all 4 services (e.g., latest, v1.0.0)"
  type        = string
  default     = "latest"
}

# ============================================================================
# Service Naming
# ============================================================================

variable "service_name_prefix" {
  description = "Prefix for Cloud Run service names (e.g., 'rag' → 'rag-ingestion', 'rag-retrieval', etc.)"
  type        = string
  default     = "rag"
}

variable "environment" {
  description = "Environment name (development, staging, production)"
  type        = string
  default     = "development"
}

# ============================================================================
# Cloud Run Resource Configuration (Applied to all 4 services)
# ============================================================================

variable "cpu_per_service" {
  description = "CPU allocation per Cloud Run service (1 = 1000m)"
  type        = string
  default     = "1"
}

variable "memory_per_service" {
  description = "Memory allocation per Cloud Run service"
  type        = string
  default     = "2Gi"
}

variable "max_instances_per_service" {
  description = "Maximum number of instances per Cloud Run service (auto-scaling limit)"
  type        = number
  default     = 10
}
