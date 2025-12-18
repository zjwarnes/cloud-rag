"""Retrieval app tests."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

import pytest
from unittest.mock import AsyncMock, patch, MagicMock


class TestEmbeddingService:
    """Test embedding service for retrieval."""

    def test_embed_query(self, mock_openai_client, mock_settings):
        """Test query embedding."""
        with patch("openai.OpenAI", return_value=mock_openai_client):
            from apps.retrieval.services.pipeline import EmbeddingService

            service = EmbeddingService()
            embedding = service.embed_query("What is your experience?")

            assert embedding is not None
            assert len(embedding) == 5
            assert embedding[0] == 0.1


class TestVectorSearchService:
    """Test vector search service."""

    def test_search_vectors(self, mock_pinecone_index, mock_settings):
        """Test vector search."""
        with patch("pinecone.Pinecone") as mock_pc:
            mock_instance = MagicMock()
            mock_instance.Index.return_value = mock_pinecone_index
            mock_pc.return_value = mock_instance

            from apps.retrieval.services.pipeline import VectorSearchService

            service = VectorSearchService()
            results = service.search(
                query_embedding=[0.1, 0.2, 0.3, 0.4, 0.5], top_k=5, user_id="test_user"
            )

            assert len(results) == 2
            assert results[0]["score"] == 0.95


class TestRankingService:
    """Test ranking service."""

    def test_rank_chunks(self, sample_retrieval_chunks):
        """Test chunk ranking."""
        from apps.retrieval.services.pipeline import RankingService

        # Convert models to dicts for ranking
        chunks_dict = [
            {
                "id": c.id,
                "text": c.text,
                "doc_id": c.doc_id,
                "source_url": c.source_url,
                "page": c.page,
                "chunk_index": c.chunk_index,
                "score": c.score,
            }
            for c in sample_retrieval_chunks
        ]

        service = RankingService()
        ranked = service.rank_chunks(chunks_dict)

        assert len(ranked) == 2
        assert ranked[0]["score"] >= ranked[1]["score"]

    def test_deduplicate_chunks(self, sample_retrieval_chunks):
        """Test chunk deduplication."""
        from apps.retrieval.services.pipeline import RankingService

        # Convert models to dicts
        chunks_dict = [
            {
                "id": c.id,
                "text": c.text,
                "doc_id": c.doc_id,
                "source_url": c.source_url,
                "page": c.page,
                "chunk_index": c.chunk_index,
                "score": c.score,
            }
            for c in sample_retrieval_chunks
        ]

        # Add duplicate
        duplicates = chunks_dict + [chunks_dict[0]]

        service = RankingService()
        deduped = service.deduplicate_chunks(duplicates)

        assert len(deduped) == 2


class TestRetrievalPipeline:
    """Test full retrieval pipeline."""

    def test_full_retrieval_pipeline(
        self, mock_settings, mock_openai_client, mock_pinecone_index, sample_retrieval_chunks
    ):
        """Test end-to-end retrieval pipeline."""
        with patch("openai.OpenAI", return_value=mock_openai_client):
            with patch("pinecone.Pinecone") as mock_pc:
                mock_instance = MagicMock()
                mock_instance.Index.return_value = mock_pinecone_index
                mock_pc.return_value = mock_instance

                from apps.retrieval.services.pipeline import RetrievalPipeline
                from common.models import RetrievalRequest

                pipeline = RetrievalPipeline()
                request = RetrievalRequest(
                    query="What is your experience?", user_id="test", top_k=5
                )
                result = pipeline.retrieve(request)

                assert result.query == "What is your experience?"
                assert len(result.chunks) > 0
                assert result.retrieval_latency_ms > 0
