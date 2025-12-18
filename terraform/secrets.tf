# Secret for OpenAI API key
resource "google_secret_manager_secret" "openai_key" {
  secret_id = "${var.service_name_prefix}-openai-key"

  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "openai_key" {
  secret      = google_secret_manager_secret.openai_key.id
  secret_data = var.openai_api_key
}

# Secret for Pinecone API key
resource "google_secret_manager_secret" "pinecone_key" {
  secret_id = "${var.service_name_prefix}-pinecone-key"

  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "pinecone_key" {
  secret      = google_secret_manager_secret.pinecone_key.id
  secret_data = var.pinecone_api_key
}

# Note: IAM bindings for secret access are configured in services.tf
# where each service account gets permission to access the secrets it needs
