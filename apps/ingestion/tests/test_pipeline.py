"""Tests for ingestion pipeline."""

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from common.utils import chunk_text, clean_text, estimate_tokens


class TestTextProcessing:
    """Test text processing utilities."""

    def test_chunk_text(self):
        """Test text chunking."""
        text = "This is a sample text. " * 100  # Long text
        chunks = chunk_text(text, chunk_size=100, overlap=10)

        assert len(chunks) > 0
        assert all(len(c["text"]) > 0 for c in chunks)
        # Check overlap
        if len(chunks) > 1:
            chunk1 = chunks[0]["text"]
            chunk2 = chunks[1]["text"]
            # There should be some overlap
            assert len(set(chunk1) & set(chunk2)) > 0

    def test_clean_text(self):
        """Test text cleaning."""
        dirty_text = "This  has   extra\n\nspaces\t\tand tabs"
        clean = clean_text(dirty_text)

        assert "  " not in clean
        assert "\n\n" not in clean
        assert "\t" not in clean

    def test_estimate_tokens(self):
        """Test token estimation."""
        text = "a" * 400  # 400 chars
        tokens = estimate_tokens(text)

        # Should be approximately 100 tokens
        assert 80 < tokens < 120


class TestPipelineServices:
    """Test ingestion pipeline services."""

    def test_pdf_extractor_init(self, mock_settings):
        """Test PDF extractor initialization."""
        from apps.ingestion.services.pipeline import PDFExtractor

        extractor = PDFExtractor()
        assert extractor is not None

    def test_embedding_service_init(self, mock_settings, mock_openai_client):
        """Test embedding service initialization."""
        from apps.ingestion.services.pipeline import EmbeddingService

        service = EmbeddingService()
        assert service.model == "text-embedding-3-small"
        assert service.batch_size == 20

    def test_vector_store_init(self, mock_settings, mock_pinecone_index):
        """Test vector store initialization."""
        from apps.ingestion.services.pipeline import VectorStoreService

        store = VectorStoreService()
        # Verify lazy initialization - index should be None until _ensure_connected is called
        assert store.pc is None
        assert store.index is None


class TestIngestionPipeline:
    """Test full ingestion pipeline."""

    def test_ingest_success(
        self, mock_settings, mock_openai_client, mock_pinecone_index, sample_pdf_path
    ):
        """Test successful ingestion."""
        from apps.ingestion.services.pipeline import IngestionPipeline

        pipeline = IngestionPipeline()
        result = pipeline.ingest(sample_pdf_path)

        assert result.status == "complete"
        assert result.doc_id is not None
        assert result.chunks_created > 0
        assert result.embedding_tokens > 0
        assert result.cost_estimate >= 0
