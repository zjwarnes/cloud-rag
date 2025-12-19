# Terraform Variables for 4-Microservice RAG Deployment

# ============================================================================
# GCP Configuration
# ============================================================================

gcp_project_id = "cloud-rag-481707"
gcp_region     = "us-central1"

# ============================================================================
# Service Configuration
# ============================================================================

service_name_prefix = "rag"

# ============================================================================
# API Keys (IMPORTANT: Use environment variables or -var flag in production)
# ============================================================================

# OpenAI API key for embeddings and LLM
# Set via: export TF_VAR_openai_api_key="sk-..."
# openai_api_key = "your-openai-key-here"

# Pinecone API key for vector search
# Set via: export TF_VAR_pinecone_api_key="..."
# pinecone_api_key = "your-pinecone-key-here"

# Pinecone index name (must already exist in your Pinecone account)
pinecone_index_name = "rag-index"

# ============================================================================
# GCS Configuration
# ============================================================================

gcs_bucket_name = "rag-documents-481707"

# ============================================================================
# Docker Registry Configuration
# ============================================================================

docker_registry  = "gcr.io/cloud-rag-481707"
docker_image_tag = "latest"
