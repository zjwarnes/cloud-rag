"""Conftest for ingestion tests."""

import pytest
import sys
import os

# Add parent directories to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))


@pytest.fixture
def mock_settings(monkeypatch):
    """Mock settings for testing."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("PINECONE_API_KEY", "test-key")
    monkeypatch.setenv("GCS_BUCKET_NAME", "test-bucket")
    monkeypatch.setenv("GCP_PROJECT_ID", "test-project")
    monkeypatch.setenv("PINECONE_INDEX_NAME", "test-index")


@pytest.fixture
def mock_openai_client(monkeypatch):
    """Mock OpenAI client."""

    class MockEmbeddingResponse:
        def __init__(self):
            self.embedding = [0.1] * 1536

    class MockEmbeddingsCreate:
        def __init__(self, *args, **kwargs):
            pass

        def create(self, *args, **kwargs):
            class Response:
                data = [MockEmbeddingResponse()]

            return Response()

    class MockOpenAI:
        def __init__(self, *args, **kwargs):
            self.embeddings = MockEmbeddingsCreate()

    monkeypatch.setattr("openai.OpenAI", MockOpenAI)


@pytest.fixture
def mock_pinecone_index(monkeypatch):
    """Mock Pinecone index."""

    class MockIndex:
        def upsert(self, vectors):
            pass

    class MockPinecone:
        def __init__(self, *args, **kwargs):
            pass

        def Index(self, name):
            return MockIndex()

    monkeypatch.setattr("pinecone.Pinecone", MockPinecone)


@pytest.fixture
def sample_pdf_path(tmp_path):
    """Create a sample PDF for testing."""
    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter

        pdf_path = tmp_path / "sample.pdf"
        c = canvas.Canvas(str(pdf_path), pagesize=letter)
        c.setFont("Helvetica", 12)
        c.drawString(50, 750, "This is a test document")
        c.drawString(50, 730, "It contains some sample text")
        c.drawString(50, 710, "For testing the ingestion pipeline")
        c.save()
        return str(pdf_path)
    except ImportError:
        pytest.skip("reportlab not installed")
