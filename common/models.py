"""
Common models shared across all RAG apps.

Used by:
- Ingestion: defines output models
- Retrieval: defines input/output models
- Synthesis: consumes retrieval output, produces final response
- Frontend: consumes synthesis streaming output
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


# ============================================================================
# Ingestion Models
# ============================================================================


class IngestRequest(BaseModel):
    """Request for document ingestion."""

    file_name: str = Field(..., description="Name of the file")
    user_id: str = Field(default="default", description="User ID for multi-tenancy")
    chunk_size: int = Field(default=512, description="Characters per chunk")
    overlap: int = Field(default=100, description="Overlap between chunks")


class IngestResponse(BaseModel):
    """Response from ingestion endpoint."""

    status: str = Field(description="Status: processing, complete, error")
    doc_id: str = Field(description="Document ID")
    chunks_created: int = Field(description="Number of chunks created")
    embedding_tokens: int = Field(description="Tokens used for embeddings")
    cost_estimate: float = Field(description="Estimated cost in USD")
    message: Optional[str] = Field(default=None, description="Status message")


# ============================================================================
# Retrieval Models
# ============================================================================


class RetrievalRequest(BaseModel):
    """Request for retrieval."""

    query: str = Field(..., description="User query")
    user_id: str = Field(default="default", description="User ID for filtering")
    top_k: int = Field(default=5, description="Number of results")
    filters: Optional[Dict[str, Any]] = Field(default=None, description="Metadata filters")


class RetrievedChunk(BaseModel):
    """A single retrieved chunk."""

    id: str = Field(description="Unique chunk ID")
    text: str = Field(description="Chunk text")
    doc_id: str = Field(description="Document ID")
    source_url: str = Field(description="Source URL")
    page: Optional[int] = Field(default=None, description="Page number")
    chunk_index: int = Field(description="Index within document")
    score: Optional[float] = Field(default=None, description="Similarity score")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class RetrievalResult(BaseModel):
    """Result from retrieval service."""

    query: str = Field(description="Original query")
    chunks: List[RetrievedChunk] = Field(description="Retrieved chunks")
    retrieval_latency_ms: float = Field(description="Time to retrieve")
    num_chunks_searched: int = Field(description="Total chunks in index")


# ============================================================================
# Synthesis Models
# ============================================================================


class SynthesisRequest(BaseModel):
    """Request for synthesis (takes retrieval output)."""

    query: str = Field(..., description="Original user query")
    retrieval_result: Optional[RetrievalResult] = Field(
        default=None, description="Result from retrieval service (fetched if not provided)"
    )
    user_id: str = Field(default="default", description="User ID")
    max_tokens: int = Field(default=1000, description="Max tokens in response")
    temperature: float = Field(default=0.7, description="LLM temperature")


class Citation(BaseModel):
    """Citation reference to a source."""

    chunk_id: str = Field(description="Chunk ID")
    doc_id: str = Field(description="Document ID")
    source_url: str = Field(description="Source URL")
    page: Optional[int] = Field(default=None, description="Page number")
    text_preview: Optional[str] = Field(default=None, description="Preview of chunk text")


class SynthesisResponse(BaseModel):
    """Response from synthesis service."""

    answer: str = Field(description="Generated answer")
    citations: List[Citation] = Field(description="Source citations")
    synthesis_latency_ms: float = Field(description="Time to synthesize")
    tokens_used: int = Field(description="Tokens used for generation")
    cost_estimate: float = Field(description="Estimated cost")


# ============================================================================
# Streaming Models
# ============================================================================


class StreamEvent(BaseModel):
    """A single event in the SSE stream."""

    event_type: str = Field(description="token, citation, done, error")
    data: str = Field(description="Event data (JSON string)")


class StreamingChunk(BaseModel):
    """Chunk of text in streaming response."""

    text: str = Field(description="Text fragment")


class StreamingCitation(BaseModel):
    """Citation in streaming response."""

    chunk_id: str
    doc_id: str
    source_url: str
    page: Optional[int] = None


# ============================================================================
# Frontend Models
# ============================================================================


class FrontendRequest(BaseModel):
    """Request from frontend (simple pass-through)."""

    query: str = Field(..., description="User query")
    user_id: str = Field(default="default", description="User ID")


class FrontendResponse(BaseModel):
    """Response shown in frontend."""

    query: str
    answer_text: str
    citations: List[Dict[str, Any]]
    total_latency_ms: float
    total_cost: float


# ============================================================================
# Health Check Models
# ============================================================================


class ComponentStatus(BaseModel):
    """Status of a system component."""

    name: str
    status: str  # healthy, degraded, error
    details: Optional[str] = None


class HealthCheckResponse(BaseModel):
    """Health check response."""

    status: str  # healthy, degraded, error
    timestamp: datetime
    components: Dict[str, str]
    message: Optional[str] = None


# ============================================================================
# Metrics Models
# ============================================================================


class QueryMetrics(BaseModel):
    """Metrics for a single query."""

    query_id: str
    timestamp: datetime
    user_id: str
    query: str
    latency_ms: float
    tokens_used: int
    cost: float
    num_retrieved: int
    success: bool
    error_message: Optional[str] = None


class AppMetrics(BaseModel):
    """Metrics for an app."""

    app_name: str
    total_requests: int
    total_latency_ms: float
    avg_latency_ms: float
    p50_latency_ms: float
    p99_latency_ms: float
    error_rate: float
