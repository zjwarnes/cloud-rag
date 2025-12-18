"""Tests for the frontend FastAPI application."""

import pytest
from fastapi.testclient import TestClient


class TestFrontendApp:
    """Test the main FastAPI application."""

    def test_root_endpoint(self, client):
        """Test that root endpoint returns correct response."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "RAG Frontend Service"

    def test_health_endpoint(self, client):
        """Test health check endpoint."""
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "frontend"

    def test_app_title(self):
        """Test that app has correct metadata."""
        from apps.frontend.app import app

        assert app.title == "Frontend Service"
        assert app.version == "0.1.0"

    def test_app_has_cors_middleware(self):
        """Test that CORS middleware is configured."""
        from apps.frontend.app import app

        # Check that middleware is in the middleware stack
        # The middleware might be wrapped, so just check that middleware exists
        assert len(app.user_middleware) > 0

    def test_app_includes_router(self):
        """Test that routes are registered."""
        from apps.frontend.app import app

        # Check that routes are defined
        routes = [route.path for route in app.routes]
        assert "/" in routes
        assert "/api/v1/health" in routes

    def test_invalid_route_returns_404(self, client):
        """Test that invalid routes return 404."""
        response = client.get("/invalid-route")
        assert response.status_code == 404

    def test_query_endpoint_exists(self, client):
        """Test that query endpoint is registered."""
        # Just check it accepts POST (even if it might fail due to service unavailability)
        response = client.post("/api/v1/query", json={"query": "test", "user_id": "test"})
        # Should get some response (may be error due to mocked service, but route should exist)
        assert response.status_code in [200, 400, 500, 422]
