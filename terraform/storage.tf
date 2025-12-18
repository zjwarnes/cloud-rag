# GCS bucket for documents
resource "google_storage_bucket" "documents" {
  name          = var.gcs_bucket_name
  location      = var.gcp_region
  force_destroy = false

  uniform_bucket_level_access = true

  lifecycle_rule {
    action {
      type = "Delete"
    }
    condition {
      age = 90 # Delete documents after 90 days
    }
  }

  versioning {
    enabled = true
  }
}

# IAM bindings for GCS access are configured in services.tf
# where each service account (ingestion, retrieval, synthesis, frontend)
# gets appropriate permissions
