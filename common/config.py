"""
Shared configuration for all apps.
"""

from functools import lru_cache
from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional


class CommonSettings(BaseSettings):
    """Settings shared across all apps."""

    # Environment
    environment: str = "development"
    log_level: str = "INFO"

    # APIs
    openai_api_key: Optional[str] = None
    openai_embedding_model: str = "text-embedding-3-small"
    openai_llm_model: str = "gpt-4-turbo-preview"

    # Pinecone
    pinecone_api_key: Optional[str] = None
    pinecone_environment: str = "us-west1-gcp"
    pinecone_index_name: str = "rag-index"

    # GCP
    gcs_bucket_name: Optional[str] = None
    gcp_project_id: Optional[str] = None

    # Metrics
    enable_metrics: bool = True

    class Config:
        env_file = ".env"
        case_sensitive = False


class IngestionSettings(CommonSettings):
    """Ingestion app specific settings."""

    embedding_batch_size: int = 20
    chunk_size: int = 512
    chunk_overlap: int = 100
    max_file_size_mb: int = 100


class RetrievalSettings(CommonSettings):
    """Retrieval app specific settings."""

    query_top_k: int = 5
    context_budget_tokens: int = 2000
    enable_reranking: bool = False


class SynthesisSettings(CommonSettings):
    """Synthesis app specific settings."""

    max_response_tokens: int = 1000
    temperature: float = 0.7

    # Service URLs (for calling other services)
    retrieval_service_url: str = Field(
        default="http://localhost:8001", alias="RETRIEVAL_SERVICE_URL"
    )

    class Config(CommonSettings.Config):
        case_sensitive = False
        populate_by_name = True


class FrontendSettings(CommonSettings):
    """Frontend app specific settings."""

    # Service URLs
    synthesis_service_url: str = Field(
        default="http://localhost:8002", alias="SYNTHESIS_SERVICE_URL"
    )
    streaming_buffer_size: int = 1024

    class Config(CommonSettings.Config):
        case_sensitive = False
        populate_by_name = True


# Cached getters for each app
@lru_cache()
def get_ingestion_settings() -> IngestionSettings:
    return IngestionSettings()


@lru_cache()
def get_retrieval_settings() -> RetrievalSettings:
    return RetrievalSettings()


@lru_cache()
def get_synthesis_settings() -> SynthesisSettings:
    return SynthesisSettings()


@lru_cache()
def get_frontend_settings() -> FrontendSettings:
    return FrontendSettings()
