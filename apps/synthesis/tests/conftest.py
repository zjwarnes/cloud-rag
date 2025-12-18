"""Synthesis app tests fixtures and configuration."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from common.models import RetrievedChunk, RetrievalResult


@pytest.fixture
def mock_settings(monkeypatch):
    """Mock synthesis settings."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    settings = Mock()
    settings.openai_api_key = "test-key"
    settings.llm_temperature = 0.7
    settings.llm_max_tokens = 1000
    settings.retrieval_service_url = "http://localhost:8001"
    settings.max_context_tokens = 2000
    settings.context_buffer_size = 100
    return settings


@pytest.fixture
def mock_openai_client(monkeypatch):
    """Mock OpenAI client."""

    class MockChoice:
        def __init__(self):
            self.message = Mock(content="Generated response about portfolio")

    class MockCompletion:
        def __init__(self):
            self.choices = [MockChoice()]
            self.usage = Mock(completion_tokens=100, total_tokens=150)

    class MockChat:
        def __init__(self):
            self.completions = Mock()
            self.completions.create = Mock(return_value=MockCompletion())

    class MockOpenAI:
        def __init__(self, *args, **kwargs):
            self.chat = MockChat()

    monkeypatch.setattr("openai.OpenAI", MockOpenAI)

    client = MagicMock()
    client.chat.completions.create = MagicMock(
        return_value=Mock(
            choices=[Mock(message=Mock(content="Generated response about portfolio"))],
            usage=Mock(completion_tokens=100, total_tokens=150),
        )
    )
    return client


@pytest.fixture
def mock_retrieval_result():
    """Mock retrieval result."""
    return RetrievalResult(
        query="What is your experience?",
        chunks=[
            RetrievedChunk(
                id="chunk_1",
                text="I have 5 years of Python experience",
                doc_id="doc_1",
                source_url="https://example.com",
                page=1,
                chunk_index=0,
                score=0.95,
            )
        ],
        retrieval_latency_ms=45,
        num_chunks_searched=100,
    )


@pytest.fixture
def sample_synthesis_request():
    """Sample synthesis request."""
    from common.models import SynthesisRequest, RetrievalResult

    return SynthesisRequest(
        query="What is your experience?",
        user_id="test_user",
        retrieval_result=RetrievalResult(
            query="What is your experience?",
            chunks=[],
            retrieval_latency_ms=0,
            num_chunks_searched=0,
        ),
    )
