# Outputs for 4-Microservice RAG Architecture
#
# These outputs display the URLs and connection details for all 4 services

# ============================================================================
# Service URLs (Public & Internal)
# ============================================================================

output "ingestion_service_url" {
  description = "Public URL for Ingestion service (PDF upload)"
  value       = google_cloud_run_service.ingestion.status[0].url
}

output "retrieval_service_url" {
  description = "Public URL for Retrieval service (Vector search)"
  value       = google_cloud_run_service.retrieval.status[0].url
}

output "synthesis_service_url" {
  description = "Public URL for Synthesis service (LLM generation)"
  value       = google_cloud_run_service.synthesis.status[0].url
}

output "frontend_service_url" {
  description = "Public URL for Frontend service (SSE streaming)"
  value       = google_cloud_run_service.frontend.status[0].url
}

# ============================================================================
# Service Connection Summary
# ============================================================================

output "service_urls" {
  description = "Summary of all service URLs"
  value = {
    ingestion = {
      url     = google_cloud_run_service.ingestion.status[0].url
      port    = 8000
      purpose = "PDF upload, text extraction, embedding generation"
    }
    retrieval = {
      url     = google_cloud_run_service.retrieval.status[0].url
      port    = 8001
      purpose = "Vector similarity search, ranking, deduplication"
    }
    synthesis = {
      url     = google_cloud_run_service.synthesis.status[0].url
      port    = 8002
      purpose = "LLM orchestration, response generation, citations"
    }
    frontend = {
      url     = google_cloud_run_service.frontend.status[0].url
      port    = 8003
      purpose = "Public-facing SSE streaming endpoint"
    }
  }
}

# ============================================================================
# Testing Commands
# ============================================================================

output "test_commands" {
  description = "Example cURL commands to test each service"
  value = {
    ingestion_health = "curl ${google_cloud_run_service.ingestion.status[0].url}/api/v1/health"
    retrieval_health = "curl ${google_cloud_run_service.retrieval.status[0].url}/api/v1/health"
    synthesis_health = "curl ${google_cloud_run_service.synthesis.status[0].url}/api/v1/health"
    frontend_health  = "curl ${google_cloud_run_service.frontend.status[0].url}/api/v1/health"
    frontend_query   = "curl -N ${google_cloud_run_service.frontend.status[0].url}/api/v1/query -H 'Content-Type: application/json' -d '{\"query\":\"test\"}'"
  }
}

# ============================================================================
# Service Account & IAM
# ============================================================================

output "service_accounts" {
  description = "Service accounts for each service"
  value = {
    ingestion = google_service_account.rag_ingestion.email
    retrieval = google_service_account.rag_retrieval.email
    synthesis = google_service_account.rag_synthesis.email
    frontend  = google_service_account.rag_frontend.email
  }
}

# ============================================================================
# Storage & Secrets
# ============================================================================

output "gcs_bucket_name" {
  description = "GCS bucket name for storing PDFs"
  value       = google_storage_bucket.documents.name
}

output "gcs_bucket_url" {
  description = "GCS bucket URL"
  value       = "gs://${google_storage_bucket.documents.name}"
}

output "secrets_created" {
  description = "Secrets created in Secret Manager"
  value = {
    openai_key   = google_secret_manager_secret.openai_key.id
    pinecone_key = google_secret_manager_secret.pinecone_key.id
  }
}
