"""Tests for the isolated health-only entry point (backend/app/health_only.py).

Verifies that the isolated liveness probe exposes strictly `GET /api/health`
and does NOT expose:
- /api/layers
- /api/routes/analyze
- /docs
- /redoc
- /openapi.json
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.app.health_only import app as health_only_app
from backend.app.main import app as product_app


@pytest.fixture(scope="module")
def client() -> TestClient:
    """Test client bound exclusively to the health-only application."""
    return TestClient(health_only_app)


class TestHealthOnlyIsolation:
    """Verify strict isolation of the health-only entry point."""

    def test_health_check_returns_200(self, client: TestClient) -> None:
        """GET /api/health returns HTTP 200 with standard liveness payload."""
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["service"] == "vyompath-api"
        assert data["mode"] == "development/mock"
        assert "timestamp_utc" in data
        assert "notes" in data

    @pytest.mark.parametrize(
        "method,path",
        [
            ("GET", "/api/layers"),
            ("GET", "/api/layers/mola-colorhillshade"),
            ("POST", "/api/routes/analyze"),
            ("GET", "/api/routes/analyze"),
        ],
    )
    def test_product_routes_return_404(
        self, client: TestClient, method: str, path: str
    ) -> None:
        """Product endpoints must return 404 on the health-only application."""
        response = client.request(method, path)
        assert response.status_code == 404, (
            f"Expected 404 for unmounted product endpoint {method} {path}, "
            f"got {response.status_code}"
        )

    @pytest.mark.parametrize(
        "doc_path",
        [
            "/docs",
            "/redoc",
            "/openapi.json",
        ],
    )
    def test_docs_and_openapi_disabled(
        self, client: TestClient, doc_path: str
    ) -> None:
        """Interactive documentation and OpenAPI schema must be disabled (404)."""
        response = client.get(doc_path)
        assert response.status_code == 404, (
            f"Expected 404 for disabled docs endpoint {doc_path}, "
            f"got {response.status_code}"
        )

    def test_product_app_remains_intact(self) -> None:
        """The main product application must retain its full router set."""
        prod_client = TestClient(product_app)
        assert prod_client.get("/api/health").status_code == 200
        assert prod_client.get("/api/layers").status_code == 200
        assert prod_client.get("/openapi.json").status_code == 200
