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
    assert data["analysis_mode"] == "mock"
    assert data["is_mock"] is True
    assert "timestamp_utc" in data
    assert "notes" in data


def test_health_check_live_dtm_mode(monkeypatch, client: TestClient, tmp_path: Path) -> None:
    from pathlib import Path
    # 1. Unreadable/invalid DTM -> must report mock mode
    fake_dem = tmp_path / "jezero_test.tif"
    fake_dem.write_bytes(b"mock-geotiff-header-not-a-real-tiff")

    monkeypatch.setenv("VYOMPATH_DEM_PATH", str(fake_dem))
    res_fake = client.get("/api/health")
    assert res_fake.status_code == 200
    data_fake = res_fake.json()
    assert data_fake["mode"] == "development/mock"
    assert data_fake["analysis_mode"] == "mock"
    assert data_fake["is_mock"] is True

    # 2. Unset DTM -> must report mock mode
    monkeypatch.delenv("VYOMPATH_DEM_PATH", raising=False)
    res_mock = client.get("/api/health")
    assert res_mock.status_code == 200
    data_mock = res_mock.json()
    assert data_mock["mode"] == "development/mock"
    assert data_mock["analysis_mode"] == "mock"
    assert data_mock["is_mock"] is True

    # 3. Real DTM if present
    real_dem = Path("/home/mayank-sharma/Hackathon/NASA/data/vyompath-demo-bundle-v1.4/jezero_aoi_v2.tif")
    if real_dem.is_file():
        monkeypatch.setenv("VYOMPATH_DEM_PATH", str(real_dem))
        res_live = client.get("/api/health")
        assert res_live.status_code == 200
        data_live = res_live.json()
        assert data_live["mode"] == "production/live"
        assert data_live["analysis_mode"] == "real_dtm"
        assert data_live["is_mock"] is False


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
    assert data["coverage_status"] == "not_applicable"
    assert data["analysis_mode"] == "mock"
    assert data["is_mock"] is True
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


# ---------------------------------------------------------------------------
# 5. Mission-Aware Traverse Intelligence Endpoint Tests
# ---------------------------------------------------------------------------

def test_evaluate_intelligence_api_endpoint(client: TestClient) -> None:
    # First obtain a valid route analysis for Route A
    coords_a = [{"lon": 77.4631, "lat": 18.4608}, {"lon": 77.4615, "lat": 18.4645}]
    res_a = client.post("/api/routes/analyze", json={"route_id": "test-a", "coordinates": coords_a})
    assert res_a.status_code == 200
    route_a_data = res_a.json()

    # Obtain Route B analysis
    coords_b = [{"lon": 77.5480, "lat": 18.4650}, {"lon": 77.5560, "lat": 18.4750}]
    res_b = client.post("/api/routes/analyze", json={"route_id": "test-b", "coordinates": coords_b})
    assert res_b.status_code == 200
    route_b_data = res_b.json()

    # 1. Single Route evaluation
    single_res = client.post(
        "/api/routes/evaluate-intelligence",
        json={"objective": "slope_conscious", "route_a": route_a_data},
    )
    assert single_res.status_code == 200
    single_json = single_res.json()
    assert single_json["recommendation"] == "single_route"
    assert single_json["route_a"] is not None
    assert single_json["route_b"] is None

    # 2. Comparative evaluation
    comp_res = client.post(
        "/api/routes/evaluate-intelligence",
        json={"objective": "slope_conscious", "route_a": route_a_data, "route_b": route_b_data},
    )
    assert comp_res.status_code == 200
    comp_json = comp_res.json()
    assert comp_json["recommendation"] in ("route_a", "route_b", "tie")
    assert comp_json["route_a"]["overall_score"] >= 0.0
    assert comp_json["route_b"]["overall_score"] >= 0.0
    assert "evidence_explanation" in comp_json
    assert len(comp_json["scientific_disclaimers"]) > 0
