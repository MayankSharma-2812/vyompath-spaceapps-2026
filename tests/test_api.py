"""Cross-platform integration tests for VyomPath FastAPI API.

Runs cleanly on Linux, Windows, and macOS without external dependencies.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


# ---------------------------------------------------------------------------
# 1. Health Endpoint Tests
# ---------------------------------------------------------------------------

def test_health_check_status_and_mode(client: TestClient) -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "vyompath-api"
    assert data["mode"] == "development/mock"
    assert "timestamp_utc" in data
    assert "notes" in data


def test_health_check_live_dtm_mode(monkeypatch, client: TestClient, tmp_path: Path) -> None:
    fake_dem = tmp_path / "jezero_test.tif"
    fake_dem.write_bytes(b"mock-geotiff-header")

    monkeypatch.setenv("VYOMPATH_DEM_PATH", str(fake_dem))
    res_live = client.get("/api/health")
    assert res_live.status_code == 200
    data_live = res_live.json()
    assert data_live["mode"] == "production/live"
    assert "Real Jezero HiRISE stereo DTM is mounted" in data_live["notes"]

    monkeypatch.delenv("VYOMPATH_DEM_PATH", raising=False)
    res_mock = client.get("/api/health")
    assert res_mock.status_code == 200
    data_mock = res_mock.json()
    assert data_mock["mode"] == "development/mock"


# ---------------------------------------------------------------------------
# 2. Layer Catalogue Tests
# ---------------------------------------------------------------------------

def test_layers_fallback_catalogue(client: TestClient) -> None:
    response = client.get("/api/layers")
    assert response.status_code == 200
    data = response.json()
    assert "count" in data
    assert "layers" in data
    assert data["count"] == len(data["layers"])
    assert data["count"] >= 1

    # Verify layer structure
    layer_ids = [l["id"] for l in data["layers"]]
    assert "mola-colorhillshade" in layer_ids


# ---------------------------------------------------------------------------
# 3. Route Analysis Tests
# ---------------------------------------------------------------------------

def test_route_analysis_valid_route(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("VYOMPATH_DEM_PATH", raising=False)
    payload = {
        "route_id": "test-olympus-traverse",
        "coordinates": [
            {"lon": -134.0, "lat": 18.4},
            {"lon": -133.9, "lat": 18.45},
            {"lon": -133.8, "lat": 18.5},
        ],
        "buffer_distance_m": 500.0,
    }
    response = client.post("/api/routes/analyze", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["route_id"] == "test-olympus-traverse"
    assert abs(data["total_distance_m"] - 12712.13) < 1.0
    assert len(data["elevation_profile"]) >= 2
    assert data["coverage_status"] == "complete"
    assert data["dtm_source"] == "synthetic/mock — no real DTM loaded"
    assert data["is_mock"] is True
    assert data["nearby_pois"] == []
    assert len(data["limitations"]) >= 1

    # Internal consistency check
    profile = data["elevation_profile"]
    assert profile[0]["distance_m"] == 0.0
    assert abs(profile[-1]["distance_m"] - data["total_distance_m"]) < 1.0


def test_route_analysis_exceeds_25km_rejected(client: TestClient) -> None:
    payload = {
        "route_id": "test-olympus-too-long",
        "coordinates": [
            {"lon": -134.0, "lat": 18.4},
            {"lon": -133.5, "lat": 18.6},
            {"lon": -133.0, "lat": 18.8},
        ],
        "buffer_distance_m": 500.0,
    }
    response = client.post("/api/routes/analyze", json=payload)
    assert response.status_code == 422
    assert any("25,000" in err.get("msg", "") for err in response.json()["detail"])


def test_route_analysis_determinism(client: TestClient) -> None:
    payload = {
        "route_id": "determinism-check",
        "coordinates": [
            {"lon": 0.0, "lat": 0.0},
            {"lon": 1.0, "lat": 1.0},
        ],
        "buffer_distance_m": 250.0,
    }
    res1 = client.post("/api/routes/analyze", json=payload).json()
    res2 = client.post("/api/routes/analyze", json=payload).json()
    assert res1 == res2


# ---------------------------------------------------------------------------
# 4. Input Validation & Edge Case Tests
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "invalid_payload,expected_loc",
    [
        (
            {"route_id": "bad", "coordinates": [{"lon": 999.0, "lat": 0.0}, {"lon": 0.0, "lat": 0.0}]},
            "lon",
        ),
        (
            {"route_id": "bad", "coordinates": [{"lon": 0.0, "lat": -95.0}, {"lon": 0.0, "lat": 0.0}]},
            "lat",
        ),
        (
            {"route_id": "bad", "coordinates": [{"lon": 0.0, "lat": 0.0}]},
            "coordinates",
        ),
        (
            {
                "route_id": "bad",
                "coordinates": [{"lon": 0.0, "lat": 0.0}, {"lon": 1.0, "lat": 1.0}],
                "buffer_distance_m": 10.0,
            },
            "buffer_distance_m",
        ),
        (
            {
                "route_id": "bad",
                "coordinates": [{"lon": 0.0, "lat": 0.0}, {"lon": 1.0, "lat": 1.0}],
                "buffer_distance_m": 5000.0,
            },
            "buffer_distance_m",
        ),
        (
            {"route_id": "", "coordinates": [{"lon": 0.0, "lat": 0.0}, {"lon": 1.0, "lat": 1.0}]},
            "route_id",
        ),
        (
            {"route_id": "a" * 65, "coordinates": [{"lon": 0.0, "lat": 0.0}, {"lon": 1.0, "lat": 1.0}]},
            "route_id",
        ),
        (
            {"route_id": "bad", "coordinates": [{"lon": 0.0, "lat": 0.0}] * 501},
            "coordinates",
        ),
    ],
)
def test_route_analysis_validation_errors(
    client: TestClient, invalid_payload: dict, expected_loc: str
) -> None:
    response = client.post("/api/routes/analyze", json=invalid_payload)
    assert response.status_code == 422
    err_locs = [str(err["loc"][-1]) for err in response.json()["detail"]]
    assert expected_loc in err_locs


# ---------------------------------------------------------------------------
# 5. CORS Header Tests
# ---------------------------------------------------------------------------

def test_cors_preflight(client: TestClient) -> None:
    headers = {
        "Origin": "http://localhost:5173",
        "Access-Control-Request-Method": "GET",
    }
    response = client.options("/api/health", headers=headers)
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"


def test_cors_resolve_origins_default_on_empty() -> None:
    from backend.app.main import DEFAULT_CORS_ORIGINS, _resolve_cors_origins

    origins, creds = _resolve_cors_origins(None)
    assert origins == DEFAULT_CORS_ORIGINS
    assert creds is True

    origins, creds = _resolve_cors_origins("   ")
    assert origins == DEFAULT_CORS_ORIGINS
    assert creds is True

    origins, creds = _resolve_cors_origins(" , , ")
    assert origins == DEFAULT_CORS_ORIGINS
    assert creds is True


def test_cors_resolve_origins_custom_csv_and_trimming() -> None:
    from backend.app.main import _resolve_cors_origins

    raw = " https://vyompath.pages.dev , http://localhost:3000 "
    origins, creds = _resolve_cors_origins(raw)
    assert origins == ["https://vyompath.pages.dev", "http://localhost:3000"]
    assert creds is True


def test_cors_resolve_origins_wildcard_disables_credentials() -> None:
    from backend.app.main import _resolve_cors_origins

    origins, creds = _resolve_cors_origins("*")
    assert origins == ["*"]
    assert creds is False

    origins, creds = _resolve_cors_origins("http://localhost:5173, *")
    assert "*" in origins
    assert creds is False
