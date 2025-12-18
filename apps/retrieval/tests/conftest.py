"""Retrieval app tests fixtures and configuration."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from common.models import RetrievedChunk, RetrievalResult


@pytest.fixture
def mock_settings(monkeypatch):
    """Mock retrieval settings."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("PINECONE_API_KEY", "test-pinecone-key")
    monkeypatch.setenv("PINECONE_INDEX_NAME", "test-index")

    settings = Mock()
    settings.openai_api_key = "test-key"
    settings.pinecone_api_key = "test-pinecone-key"
    settings.pinecone_index_name = "test-index"
    settings.pinecone_namespace = "test"
    settings.query_top_k = 5
    settings.openai_embedding_model = "text-embedding-3-small"
    return settings


@pytest.fixture
def mock_openai_client(monkeypatch):
    """Mock OpenAI client."""

    class MockEmbeddingResponse:
        def __init__(self):
            self.embedding = [0.1, 0.2, 0.3, 0.4, 0.5]

    class MockEmbeddingsCreate:
        def create(self, *args, **kwargs):
            class Response:
                data = [MockEmbeddingResponse()]

            return Response()

    class MockOpenAI:
        def __init__(self, *args, **kwargs):
            self.embeddings = MockEmbeddingsCreate()

    monkeypatch.setattr("openai.OpenAI", MockOpenAI)

    # Return a mock client that works synchronously
    client = MagicMock()
    client.embeddings.create = MagicMock(
        return_value=MagicMock(data=[MagicMock(embedding=[0.1, 0.2, 0.3, 0.4, 0.5])])
    )
    return client


@pytest.fixture
def mock_pinecone_index(monkeypatch):
    """Mock Pinecone index."""

    class MockMatch:
        def __init__(self, id, score, metadata):
            self.id = id
            self.score = score
            self.metadata = metadata

    class MockQueryResult:
        def __init__(self):
            self.matches = [
                MockMatch(
                    id="chunk_1",
                    score=0.95,
                    metadata={
                        "doc_id": "doc_1",
                        "chunk_index": 0,
                        "text": "Sample portfolio text",
                        "source_url": "https://example.com",
                        "page": 1,
                    },
                ),
                MockMatch(
                    id="chunk_2",
                    score=0.87,
                    metadata={
                        "doc_id": "doc_1",
                        "chunk_index": 0,
                        "text": "Another portfolio text",
                        "source_url": "https://example.com",
                        "page": 1,
                    },
                ),
            ]

    class MockIndex:
        def query(self, *args, **kwargs):
            return MockQueryResult()

    class MockPinecone:
        def __init__(self, *args, **kwargs):
            pass

        def Index(self, name):
            return MockIndex()

    monkeypatch.setattr("pinecone.Pinecone", MockPinecone)

    index = Mock()
    index.query = Mock(return_value=MockQueryResult())
    return index


@pytest.fixture
def sample_retrieval_chunks():
    """Sample retrieval chunks."""
    return [
        RetrievedChunk(
            id="chunk_1",
            text="Portfolio experience in Python",
            doc_id="doc_1",
            source_url="https://example.com",
            page=1,
            chunk_index=0,
            score=0.95,
        ),
        RetrievedChunk(
            id="chunk_2",
            text="Machine learning projects",
            doc_id="doc_2",
            source_url="https://example.com",
            page=2,
            chunk_index=1,
            score=0.87,
        ),
    ]
