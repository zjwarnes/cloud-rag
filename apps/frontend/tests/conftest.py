"""Pytest configuration and fixtures for frontend tests."""

import sys
import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from apps.frontend.app import app
from common.models import FrontendRequest


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def frontend_request():
    """Create a sample frontend request."""
    return FrontendRequest(query="What is machine learning?", user_id="test_user")


@pytest.fixture
def synthesis_response():
    """Create a sample synthesis response."""
    return {
        "answer": "Machine learning is a subset of artificial intelligence...",
        "synthesis_latency_ms": 245.5,
        "cost_estimate": 0.0025,
        "tokens_used": 145,
        "citations": [
            {
                "chunk_id": "chunk_1",
                "doc_id": "doc_1",
                "source_url": "https://example.com/ml",
                "text": "Machine learning...",
            }
        ],
    }


@pytest.fixture
def mock_httpx_client(synthesis_response):
    """Mock httpx AsyncClient for external API calls."""
    mock_response = MagicMock()
    mock_response.json.return_value = synthesis_response
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None
    mock_client.post = AsyncMock(return_value=mock_response)

    return mock_client


@pytest.fixture
def mock_settings():
    """Mock frontend settings."""
    mock = MagicMock()
    mock.synthesis_service_url = "http://localhost:8002"
    return mock
