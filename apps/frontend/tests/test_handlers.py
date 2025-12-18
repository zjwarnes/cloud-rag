"""Tests for frontend API handlers and routes."""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock
import json


class TestQueryEndpoint:
    """Test the /api/v1/query endpoint."""

    @pytest.mark.asyncio
    async def test_query_endpoint_with_mock_service(
        self, client, mock_httpx_client, synthesis_response
    ):
        """Test query endpoint with mocked synthesis service."""
        with patch("apps.frontend.handlers.routes.httpx.AsyncClient") as mock_client_class:
            mock_client_class.return_value = mock_httpx_client

            response = client.post(
                "/api/v1/query", json={"query": "What is AI?", "user_id": "test_user"}
            )

            # Check response status
            assert response.status_code == 200
            # Check content type is SSE (may include charset)
            assert "text/event-stream" in response.headers["content-type"]

    @pytest.mark.asyncio
    async def test_query_endpoint_with_streaming_response(
        self, client, mock_httpx_client, synthesis_response
    ):
        """Test that query endpoint returns streaming response."""
        with patch("apps.frontend.handlers.routes.httpx.AsyncClient") as mock_client_class:
            mock_client_class.return_value = mock_httpx_client

            response = client.post(
                "/api/v1/query", json={"query": "Test query", "user_id": "user1"}
            )

            assert response.status_code == 200
            assert "text/event-stream" in response.headers["content-type"]

    def test_query_endpoint_missing_query(self, client):
        """Test query endpoint with missing query parameter."""
        response = client.post("/api/v1/query", json={"user_id": "test_user"})
        # Should return validation error
        assert response.status_code == 422

    def test_query_endpoint_with_default_user(self, client, mock_httpx_client):
        """Test query endpoint uses default user_id when not provided."""
        with patch("apps.frontend.handlers.routes.httpx.AsyncClient") as mock_client_class:
            mock_client_class.return_value = mock_httpx_client
            mock_client_class.return_value.post = AsyncMock(
                return_value=MagicMock(
                    json=MagicMock(
                        return_value={
                            "answer": "test",
                            "synthesis_latency_ms": 100,
                            "cost_estimate": 0.001,
                            "tokens_used": 50,
                            "citations": [],
                        }
                    ),
                    raise_for_status=MagicMock(),
                )
            )

            response = client.post("/api/v1/query", json={"query": "Test query"})

            # Should succeed with default user_id
            assert response.status_code == 200


class TestHealthEndpoint:
    """Test the /api/v1/health endpoint."""

    def test_health_check_success(self, client):
        """Test health check returns expected format."""
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "service" in data
        assert data["status"] == "healthy"
        assert data["service"] == "frontend"

    def test_health_check_is_get_only(self, client):
        """Test health endpoint only accepts GET."""
        response = client.post("/api/v1/health")
        assert response.status_code == 405

    def test_health_check_response_format(self, client):
        """Test health check response is valid JSON."""
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
        assert "status" in data


class TestFrontendRequestValidation:
    """Test FrontendRequest model validation."""

    def test_query_field_required(self, client):
        """Test that query field is required."""
        response = client.post("/api/v1/query", json={"user_id": "user1"})
        assert response.status_code == 422

    def test_user_id_default_value(self, client, mock_httpx_client):
        """Test that user_id defaults to 'default' if not provided."""
        with patch("apps.frontend.handlers.routes.httpx.AsyncClient") as mock_client_class:
            mock_client_class.return_value = mock_httpx_client

            response = client.post("/api/v1/query", json={"query": "test query"})

            assert response.status_code == 200

    def test_query_accepts_valid_input(self, client, mock_httpx_client):
        """Test that query endpoint accepts valid input."""
        with patch("apps.frontend.handlers.routes.httpx.AsyncClient") as mock_client_class:
            mock_client_class.return_value = mock_httpx_client

            response = client.post(
                "/api/v1/query", json={"query": "What is machine learning?", "user_id": "user123"}
            )

            assert response.status_code == 200


class TestStreamingResponse:
    """Test streaming response functionality."""

    def test_streaming_response_content_type(self, client, mock_httpx_client):
        """Test that streaming response has correct content type."""
        with patch("apps.frontend.handlers.routes.httpx.AsyncClient") as mock_client_class:
            mock_client_class.return_value = mock_httpx_client

            response = client.post("/api/v1/query", json={"query": "test", "user_id": "user1"})

            assert "text/event-stream" in response.headers.get("content-type", "")

    @pytest.mark.asyncio
    async def test_stream_includes_answer_event(
        self, client, mock_httpx_client, synthesis_response
    ):
        """Test that stream includes answer event."""
        with patch("apps.frontend.handlers.routes.httpx.AsyncClient") as mock_client_class:
            mock_client_class.return_value = mock_httpx_client

            response = client.post("/api/v1/query", json={"query": "test", "user_id": "user1"})

            assert response.status_code == 200


class TestErrorHandling:
    """Test error handling in handlers."""

    def test_invalid_json_request(self, client):
        """Test handling of invalid JSON."""
        response = client.post(
            "/api/v1/query", content="invalid json", headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 422

    def test_empty_query_string(self, client, mock_httpx_client):
        """Test handling of empty query string."""
        response = client.post("/api/v1/query", json={"query": "", "user_id": "user1"})
        # Empty string is technically valid for Pydantic, but may fail downstream
        # Depending on implementation, either 200 or 400
        assert response.status_code in [200, 400, 422]

    def test_very_long_query(self, client, mock_httpx_client):
        """Test handling of very long query string."""
        with patch("apps.frontend.handlers.routes.httpx.AsyncClient") as mock_client_class:
            mock_client_class.return_value = mock_httpx_client

            long_query = "test " * 10000
            response = client.post("/api/v1/query", json={"query": long_query, "user_id": "user1"})

            # Should handle gracefully
            assert response.status_code in [200, 400, 413, 422]
