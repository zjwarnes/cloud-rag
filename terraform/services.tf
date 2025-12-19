# Cloud Run Services for 4-Microservice RAG Architecture
#
# This file defines 4 independent Cloud Run services that can scale independently.
# Each service has its own configuration, environment variables, and IAM permissions.

# ============================================================================
# 1. INGESTION SERVICE (Port 8000)
# ============================================================================
# Purpose: PDF upload, text extraction, chunking, embedding generation
# Typical load: Bursty (users upload documents)
# Scaling: Can scale high during batch operations

resource "google_cloud_run_service" "ingestion" {
  name     = "${var.service_name_prefix}-ingestion"
  location = var.gcp_region

  template {
    spec {
      containers {
        image = "${var.docker_registry}/rag-ingestion:${var.docker_image_tag}"

        # Service-specific ports
        ports {
          container_port = 8000
        }

        # Environment variables
        env {
          name  = "ENVIRONMENT"
          value = var.environment
        }

        env {
          name  = "GCP_PROJECT_ID"
          value = var.gcp_project_id
        }

        env {
          name  = "PINECONE_INDEX_NAME"
          value = var.pinecone_index_name
        }

        # Secrets from Secret Manager
        env {
          name = "OPENAI_API_KEY"
          value_from {
            secret_key_ref {
              name = "${var.service_name_prefix}-openai-key"
              key  = "latest"
            }
          }
        }

        env {
          name = "PINECONE_API_KEY"
          value_from {
            secret_key_ref {
              name = "${var.service_name_prefix}-pinecone-key"
              key  = "latest"
            }
          }
        }

        # Resource allocation (higher memory for PDF processing)
        resources {
          limits = {
            cpu    = var.cpu_per_service
            memory = var.memory_per_service
          }
        }
      }

      service_account_name = google_service_account.rag_ingestion.email

      # Longer timeout for PDF uploads
      timeout_seconds = 300
    }

    metadata {
      annotations = {
        # Auto-scaling configuration
        "autoscaling.knative.dev/maxScale" = tostring(var.max_instances_per_service)
        "autoscaling.knative.dev/minScale" = "0"
      }
    }
  }

  traffic {
    percent         = 100
    latest_revision = true
  }

  depends_on = [
    google_secret_manager_secret_version.openai_key,
    google_secret_manager_secret_version.pinecone_key
  ]
}

# Allow public access to ingestion service
resource "google_cloud_run_service_iam_member" "ingestion_public" {
  service  = google_cloud_run_service.ingestion.name
  location = google_cloud_run_service.ingestion.location
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# Service account for ingestion
resource "google_service_account" "rag_ingestion" {
  account_id   = "${var.service_name_prefix}-ingestion-sa"
  display_name = "Service account for RAG Ingestion Service"
}

# IAM: GCS access for document storage
resource "google_project_iam_member" "ingestion_gcs_admin" {
  project = var.gcp_project_id
  role    = "roles/storage.objectAdmin"
  member  = "serviceAccount:${google_service_account.rag_ingestion.email}"
}

# IAM: Secret access for API keys
resource "google_secret_manager_secret_iam_member" "ingestion_openai_access" {
  secret_id = google_secret_manager_secret.openai_key.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.rag_ingestion.email}"
}

resource "google_secret_manager_secret_iam_member" "ingestion_pinecone_access" {
  secret_id = google_secret_manager_secret.pinecone_key.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.rag_ingestion.email}"
}


# ============================================================================
# 2. RETRIEVAL SERVICE (Port 8001)
# ============================================================================
# Purpose: Vector similarity search, ranking, deduplication
# Typical load: Steady (users querying)
# Scaling: Scales with query volume

resource "google_cloud_run_service" "retrieval" {
  name     = "${var.service_name_prefix}-retrieval"
  location = var.gcp_region

  template {
    spec {
      containers {
        image = "${var.docker_registry}/rag-retrieval:${var.docker_image_tag}"

        ports {
          container_port = 8001
        }

        env {
          name  = "ENVIRONMENT"
          value = var.environment
        }

        env {
          name  = "GCP_PROJECT_ID"
          value = var.gcp_project_id
        }

        env {
          name  = "PINECONE_INDEX_NAME"
          value = var.pinecone_index_name
        }

        env {
          name = "OPENAI_API_KEY"
          value_from {
            secret_key_ref {
              name = "${var.service_name_prefix}-openai-key"
              key  = "latest"
            }
          }
        }

        env {
          name = "PINECONE_API_KEY"
          value_from {
            secret_key_ref {
              name = "${var.service_name_prefix}-pinecone-key"
              key  = "latest"
            }
          }
        }

        resources {
          limits = {
            cpu    = var.cpu_per_service
            memory = var.memory_per_service
          }
        }
      }

      service_account_name = google_service_account.rag_retrieval.email

      # Shorter timeout for search operations
      timeout_seconds = 60
    }

    metadata {
      annotations = {
        "autoscaling.knative.dev/maxScale" = tostring(var.max_instances_per_service)
        "autoscaling.knative.dev/minScale" = "0"
      }
    }
  }

  traffic {
    percent         = 100
    latest_revision = true
  }

  depends_on = [
    google_secret_manager_secret_version.openai_key,
    google_secret_manager_secret_version.pinecone_key
  ]
}

# Allow internal Cloud Run service-to-service communication
resource "google_cloud_run_service_iam_member" "retrieval_invoker" {
  service  = google_cloud_run_service.retrieval.name
  location = google_cloud_run_service.retrieval.location
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.rag_synthesis.email}"
}

# Service account for retrieval
resource "google_service_account" "rag_retrieval" {
  account_id   = "${var.service_name_prefix}-retrieval-sa"
  display_name = "Service account for RAG Retrieval Service"
}

# IAM: Secret access for API keys
resource "google_secret_manager_secret_iam_member" "retrieval_openai_access" {
  secret_id = google_secret_manager_secret.openai_key.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.rag_retrieval.email}"
}

resource "google_secret_manager_secret_iam_member" "retrieval_pinecone_access" {
  secret_id = google_secret_manager_secret.pinecone_key.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.rag_retrieval.email}"
}


# ============================================================================
# 3. SYNTHESIS SERVICE (Port 8002)
# ============================================================================
# Purpose: Calls Retrieval service, orchestrates LLM, generates responses
# Typical load: Steady (users querying)
# Scaling: Scales with query volume

resource "google_cloud_run_service" "synthesis" {
  name     = "${var.service_name_prefix}-synthesis"
  location = var.gcp_region

  template {
    spec {
      containers {
        image = "${var.docker_registry}/rag-synthesis:${var.docker_image_tag}"

        ports {
          container_port = 8002
        }

        env {
          name  = "ENVIRONMENT"
          value = var.environment
        }

        env {
          name  = "GCP_PROJECT_ID"
          value = var.gcp_project_id
        }

        env {
          name  = "PINECONE_INDEX_NAME"
          value = var.pinecone_index_name
        }

        # Internal service-to-service URL for Retrieval
        env {
          name  = "RETRIEVAL_SERVICE_URL"
          value = "http://${google_cloud_run_service.retrieval.name}.run.app"
        }

        env {
          name = "OPENAI_API_KEY"
          value_from {
            secret_key_ref {
              name = "${var.service_name_prefix}-openai-key"
              key  = "latest"
            }
          }
        }

        env {
          name = "PINECONE_API_KEY"
          value_from {
            secret_key_ref {
              name = "${var.service_name_prefix}-pinecone-key"
              key  = "latest"
            }
          }
        }

        resources {
          limits = {
            cpu    = var.cpu_per_service
            memory = var.memory_per_service
          }
        }
      }

      service_account_name = google_service_account.rag_synthesis.email

      # Moderate timeout for LLM generation
      timeout_seconds = 120
    }

    metadata {
      annotations = {
        "autoscaling.knative.dev/maxScale" = tostring(var.max_instances_per_service)
        "autoscaling.knative.dev/minScale" = "0"
      }
    }
  }

  traffic {
    percent         = 100
    latest_revision = true
  }

  depends_on = [
    google_secret_manager_secret_version.openai_key,
    google_secret_manager_secret_version.pinecone_key
  ]
}

# Allow internal Cloud Run service-to-service communication
resource "google_cloud_run_service_iam_member" "synthesis_invoker" {
  service  = google_cloud_run_service.synthesis.name
  location = google_cloud_run_service.synthesis.location
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.rag_frontend.email}"
}

# Service account for synthesis
resource "google_service_account" "rag_synthesis" {
  account_id   = "${var.service_name_prefix}-synthesis-sa"
  display_name = "Service account for RAG Synthesis Service"
}

# IAM: Secret access for API keys
resource "google_secret_manager_secret_iam_member" "synthesis_openai_access" {
  secret_id = google_secret_manager_secret.openai_key.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.rag_synthesis.email}"
}

resource "google_secret_manager_secret_iam_member" "synthesis_pinecone_access" {
  secret_id = google_secret_manager_secret.pinecone_key.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.rag_synthesis.email}"
}


# ============================================================================
# 4. FRONTEND SERVICE (Port 8003)
# ============================================================================
# Purpose: Public-facing SSE streaming endpoint
# Typical load: Steady (user queries)
# Scaling: Scales with concurrent users

resource "google_cloud_run_service" "frontend" {
  name     = "${var.service_name_prefix}-frontend"
  location = var.gcp_region

  template {
    spec {
      containers {
        image = "${var.docker_registry}/rag-frontend:${var.docker_image_tag}"

        ports {
          container_port = 8003
        }

        env {
          name  = "ENVIRONMENT"
          value = var.environment
        }

        env {
          name  = "GCP_PROJECT_ID"
          value = var.gcp_project_id
        }

        # Internal service-to-service URL for Synthesis
        env {
          name  = "SYNTHESIS_SERVICE_URL"
          value = "http://${google_cloud_run_service.synthesis.name}.run.app"
        }

        resources {
          limits = {
            cpu    = var.cpu_per_service
            memory = var.memory_per_service
          }
        }
      }

      service_account_name = google_service_account.rag_frontend.email

      # Longer timeout for streaming responses
      timeout_seconds = 300
    }

    metadata {
      annotations = {
        "autoscaling.knative.dev/maxScale" = tostring(var.max_instances_per_service)
        "autoscaling.knative.dev/minScale" = "0"
      }
    }
  }

  traffic {
    percent         = 100
    latest_revision = true
  }
}

# Allow public access to frontend service
resource "google_cloud_run_service_iam_member" "frontend_public" {
  service  = google_cloud_run_service.frontend.name
  location = google_cloud_run_service.frontend.location
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# Service account for frontend
resource "google_service_account" "rag_frontend" {
  account_id   = "${var.service_name_prefix}-frontend-sa"
  display_name = "Service account for RAG Frontend Service"
}

# IAM: Cloud Logging for metrics
resource "google_project_iam_member" "frontend_logging" {
  project = var.gcp_project_id
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${google_service_account.rag_frontend.email}"
}
