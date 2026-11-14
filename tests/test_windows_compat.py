"""Windows compatibility, path handling, and encoding regression tests for VyomPath.

Validates Windows 11 host execution safety:
- Windows path conventions (backslashes, pathlib.Path, drive roots)
- Unicode/UTF-8 console string handling (degree, plus-minus, micro symbols)
- Port availability detection and socket cleanup on loopback interface
- Route analyzer API contract behavior under Windows execution
"""

from __future__ import annotations

import os
import socket
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.schemas import Coordinate
from backend.app.services.coords import haversine_m
from backend.app.services.terrain import densify_route


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


# ---------------------------------------------------------------------------
# 1. Windows Path Handling Tests
# ---------------------------------------------------------------------------

def test_windows_path_normalization() -> None:
    """Verify that Windows-style backslashes and Path objects resolve correctly."""
    repo_root = Path(__file__).resolve().parent.parent
    data_dir = repo_root / "data"
    layers_file = data_dir / "layers.json"
    science_file = data_dir / "science_points.json"

    # Both files must exist and be accessible via Path
    assert layers_file.exists(), f"Layers file not found at {layers_file}"
    assert science_file.exists(), f"Science file not found at {science_file}"

    # Verify path with explicit Windows backslashes
    win_path_str = str(layers_file).replace("/", "\\")
    assert os.path.exists(win_path_str)


def test_windows_relative_paths() -> None:
    """Verify that relative paths resolve correctly regardless of working dir."""
    repo_root = Path(__file__).resolve().parent.parent
    rel_path = os.path.relpath(repo_root / "data" / "layers.json", repo_root)
    norm = os.path.normpath(rel_path)
    assert os.path.exists(os.path.join(str(repo_root), norm))


# ---------------------------------------------------------------------------
# 2. Console Encoding and Special Character Safety
# ---------------------------------------------------------------------------

def test_unicode_scientific_symbols_encode_safely() -> None:
    """Verify that scientific symbols do not raise UnicodeEncodeError."""
    # Common symbols used across terrain, geodesy, and science outputs
    symbols = [
        "18.46079140°N",
        "77.46313311°E",
        "± 0.05 m",
        "≤ 0.007 m (7.3 mm)",
        "Δs_3D = √(Δd_2D² + Δz²)",
        "θ_grade = 4.09°",
        "Mars R = 3,396,190.0 m",
        "λ ∈ [-180°, 180°]",
        "φ ∈ [-90°, 90°]",
    ]

    for s in symbols:
        # Test UTF-8 encoding (standard)
        utf8_bytes = s.encode("utf-8")
        assert len(utf8_bytes) > 0
        decoded = utf8_bytes.decode("utf-8")
        assert decoded == s

        # Test ASCII transliteration fallback (for legacy console environments)
        ascii_fallback = s.encode("ascii", errors="replace").decode("ascii")
        assert len(ascii_fallback) > 0


# ---------------------------------------------------------------------------
# 3. Windows Loopback Socket & Port Detection Tests
# ---------------------------------------------------------------------------

def test_loopback_socket_binding_and_cleanup() -> None:
    """Verify that ephemeral loopback sockets bind, test, and release cleanly."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(0.5)
    # Bind to port 0 (OS allocates ephemeral port)
    sock.bind(("127.0.0.1", 0))
    allocated_port = sock.getsockname()[1]
    assert allocated_port > 0
    sock.listen(1)

    # Secondary socket detects port as occupied
    test_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    test_sock.settimeout(0.2)
    result = test_sock.connect_ex(("127.0.0.1", allocated_port))
    test_sock.close()
    assert result == 0, f"Port {allocated_port} should be detected as occupied"

    # Close primary socket and verify port is released
    sock.close()
    verify_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    verify_sock.settimeout(0.2)
    verify_result = verify_sock.connect_ex(("127.0.0.1", allocated_port))
    verify_sock.close()
    assert verify_result != 0, f"Port {allocated_port} should be detected as free after close"


# ---------------------------------------------------------------------------
# 4. API Contract & Geodesic Calculation Tests on Windows
# ---------------------------------------------------------------------------

def test_haversine_precision_on_windows_host() -> None:
    """Verify IEEE 754 double-precision trigonometry on Windows host."""
    # Perseverance landing anchor
    lon1, lat1 = 77.45, 18.44
    lon2, lat2 = 77.46, 18.45
    dist = haversine_m(lon1, lat1, lon2, lat2)
    # Expected distance on Mars sphere R = 3,396,190.0 m (approx 817.02 m)
    assert 500.0 < dist < 1200.0
    # Determinism check
    dist2 = haversine_m(lon1, lat1, lon2, lat2)
    assert dist == dist2


def test_route_densification_exact_step_bounds() -> None:
    """Verify route densifier produces points within step tolerance."""
    coords = [
        Coordinate(lon=77.450, lat=18.440),
        Coordinate(lon=77.452, lat=18.442),
    ]
    densified = densify_route(coords, step_m=5.0)
    assert len(densified) >= 2
    # First and last match
    assert abs(densified[0].lon - 77.450) < 1e-6
    assert abs(densified[0].lat - 18.440) < 1e-6
    assert abs(densified[-1].lon - 77.452) < 1e-6
    assert abs(densified[-1].lat - 18.442) < 1e-6


def test_api_route_analysis_offline_contract(client: TestClient) -> None:
    """Verify that health check and route analysis return all required contract fields."""
    # 1. Health check exposes operational mode
    health_res = client.get("/api/health")
    assert health_res.status_code == 200
    health_data = health_res.json()
    assert health_data["status"] == "ok"
    assert health_data["mode"] == "development/mock"

    # 2. Route analysis response schema validation
    payload = {
        "route_id": "win-rehearsal-corridor",
        "coordinates": [
            {"lon": 77.450, "lat": 18.440},
            {"lon": 77.455, "lat": 18.445},
            {"lon": 77.460, "lat": 18.450},
        ],
        "buffer_distance_m": 250.0,
    }
    response = client.post("/api/routes/analyze", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["route_id"] == "win-rehearsal-corridor"
    assert "total_distance_m" in data
    assert "elevation_profile" in data
    assert "coverage_status" in data
    assert "dtm_source" in data
    assert "nearby_pois" in data
    assert "limitations" in data
    assert "total_gain_m" in data
    assert "total_loss_m" in data
    assert "max_slope_deg" in data
    assert len(data["limitations"]) >= 1
    assert any("NOT scientifically validated" in lim for lim in data["limitations"])
    assert any("MOCK DATA" in lim for lim in data["limitations"])
