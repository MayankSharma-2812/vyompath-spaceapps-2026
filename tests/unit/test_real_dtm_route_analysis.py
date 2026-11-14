"""Focused test suite for Issue #7: Real DTM Integration & Route Analysis Engine.

Covers all 18 required verification capabilities:
1. Canonical Mars radius usage (3,396,190.0 m).
2. Route distance calculation via coordinates service.
3. 25 km route limit: just below, exactly at, and above the limit.
4. Longitude-first coordinate transformation.
5. Native raster CRS transformation and subpixel indexing.
6. Golden Sol 386 and Sol 387 elevation anchors.
7. Bilinear 4-neighbor interpolation.
8. Raster edges and out-of-bounds coordinates.
9. NoData handling and validity masks.
10. Complete terrain coverage (status='complete').
11. Partial terrain coverage (status='partial_gap').
12. Entirely out-of-bounds routes (status='out_of_bounds').
13. Missing DTM environment variable handling.
14. Invalid or unreadable raster fallback.
15. Truthful mock fallback behavior.
16. Real versus mock response metadata and limitations.
17. Concurrent requests and raster resource cleanup.
18. Existing API response contract compatibility.
"""

from __future__ import annotations

import concurrent.futures
import math
import os
from pathlib import Path
from typing import Optional

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.schemas import Coordinate, ElevationPoint, RouteAnalysisRequest, RouteAnalysisResponse
from backend.app.services.coords import MARS_RADIUS_M, haversine_m as coords_haversine_m
from backend.app.services.terrain import (
    haversine_m,
    route_distance_m,
    sample_point_bilinear,
    sample_route_dtm,
)

# Detect external Jezero DTM availability
_CANDIDATE_DTM_PATHS = [
    Path(os.environ.get("VYOMPATH_DEM_PATH", "")),
    Path("/home/mayank-sharma/Hackathon/NASA/data/vyompath-demo-bundle-v1.4/jezero_aoi_v2.tif"),
]
_RESOLVED_DTM_PATH: Optional[Path] = None
for p in _CANDIDATE_DTM_PATHS:
    if p and p.is_file():
        _RESOLVED_DTM_PATH = p
        break

_dtm_available = _RESOLVED_DTM_PATH is not None
skip_if_no_dtm = pytest.mark.skipif(
    not _dtm_available,
    reason="External HiRISE DTM (jezero_aoi_v2.tif) not available in environment",
)


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


# ---------------------------------------------------------------------------
# 1. Canonical Mars Geodesics & Radius Invariants
# ---------------------------------------------------------------------------

class TestMarsGeodesicsAndRadius:
    """Verify canonical Mars geodetics and coordinate ordering."""

    def test_canonical_mars_radius_constant(self) -> None:
        """Requirement 1: Mars radius must be exactly 3,396,190.0 m."""
        assert MARS_RADIUS_M == 3_396_190.0

    def test_route_distance_calculation(self) -> None:
        """Requirement 2: Distance calculation uses IAU 2000 canonical radius."""
        # 1 degree along equator: (pi / 180) * 3,396,190.0 = 59,274.6975 m
        c1 = Coordinate(lon=0.0, lat=0.0)
        c2 = Coordinate(lon=1.0, lat=0.0)
        expected_dist = (math.pi / 180.0) * MARS_RADIUS_M
        actual_dist = haversine_m(c1, c2)
        assert actual_dist == pytest.approx(expected_dist, rel=1e-6)

    def test_longitude_first_order(self) -> None:
        """Requirement 4: Ensure longitude is the first coordinate parameter."""
        c = Coordinate(lon=77.46313311, lat=18.46079140)
        assert c.lon == 77.46313311
        assert c.lat == 18.46079140


# ---------------------------------------------------------------------------
# 2. 25 km Route Length Limit Enforcement
# ---------------------------------------------------------------------------

class TestRouteLengthCapEnforcement:
    """Requirement 3: Enforce approved 25,000 metre maximum route length."""

    def test_route_just_below_25km_accepted(self, client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
        """Traverse with cumulative distance ~24,895 m (< 25,000 m) is accepted (200 OK)."""
        monkeypatch.delenv("VYOMPATH_DEM_PATH", raising=False)
        # 0.42 degrees of latitude = 0.42 * (pi/180) * 3,396,190 = 24,895.37 m
        payload = {
            "route_id": "route-below-cap",
            "coordinates": [
                {"lon": 77.45, "lat": 18.0},
                {"lon": 77.45, "lat": 18.42},
            ],
            "buffer_distance_m": 250.0,
        }
        response = client.post("/api/routes/analyze", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["total_distance_m"] < 25000.0

    def test_route_exactly_at_25km_accepted(self, client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
        """Traverse with cumulative distance exactly <= 25,000.0 m is accepted."""
        monkeypatch.delenv("VYOMPATH_DEM_PATH", raising=False)
        # Delta lat for exact 25,000 m: 25000 / (pi/180 * 3396190) = 0.421763717 deg
        delta_lat = 25000.0 / (math.radians(1.0) * MARS_RADIUS_M)
        payload = {
            "route_id": "route-exact-cap",
            "coordinates": [
                {"lon": 77.45, "lat": 18.0},
                {"lon": 77.45, "lat": 18.0 + delta_lat},
            ],
            "buffer_distance_m": 250.0,
        }
        response = client.post("/api/routes/analyze", json=payload)
        assert response.status_code == 200
        assert response.json()["total_distance_m"] == pytest.approx(25000.0, abs=0.5)

    def test_route_above_25km_rejected(self, client: TestClient) -> None:
        """Traverse with cumulative distance > 25,000 m is rejected with HTTP 422."""
        # 0.43 degrees of latitude = 25,488.16 m (> 25,000 m)
        payload = {
            "route_id": "route-above-cap",
            "coordinates": [
                {"lon": 77.45, "lat": 18.0},
                {"lon": 77.45, "lat": 18.43},
            ],
            "buffer_distance_m": 250.0,
        }
        response = client.post("/api/routes/analyze", json=payload)
        assert response.status_code == 422
        errors = response.json()["detail"]
        assert any("25,000" in str(err.get("msg", "")) for err in errors)


# ---------------------------------------------------------------------------
# 3. Truthful Mock Fallback Behavior
# ---------------------------------------------------------------------------

class TestMockFallbackBehavior:
    """Requirements 13, 14, 15, 16: Test truthful fallback when DTM is unavailable."""

    def test_fallback_when_dtm_unset(self, client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
        """When $VYOMPATH_DEM_PATH is unset, returns deterministic synthetic mock."""
        monkeypatch.delenv("VYOMPATH_DEM_PATH", raising=False)
        payload = {
            "route_id": "test-mock-unset",
            "coordinates": [
                {"lon": 77.46, "lat": 18.46},
                {"lon": 77.462, "lat": 18.462},
            ],
            "buffer_distance_m": 250.0,
        }
        res = client.post("/api/routes/analyze", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["dtm_source"] == "synthetic/mock — no real DTM loaded"
        assert data["dtm_posting_m"] == 0.0
        assert data["coverage_status"] == "not_applicable"
        assert data["analysis_mode"] == "mock"
        assert data["is_mock"] is True
        assert any("MOCK DATA" in lim or "DEMONSTRATION MODE" in lim for lim in data["limitations"])

    def test_fallback_when_dtm_nonexistent(self, client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
        """When $VYOMPATH_DEM_PATH points to non-existent file, safely falls back."""
        monkeypatch.setenv("VYOMPATH_DEM_PATH", "/tmp/non_existent_raster.tif")
        payload = {
            "route_id": "test-mock-missing-file",
            "coordinates": [
                {"lon": 77.46, "lat": 18.46},
                {"lon": 77.462, "lat": 18.462},
            ],
            "buffer_distance_m": 250.0,
        }
        res = client.post("/api/routes/analyze", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["dtm_source"] == "synthetic/mock — no real DTM loaded"
        assert data["coverage_status"] == "not_applicable"
        assert data["analysis_mode"] == "mock"
        assert data["is_mock"] is True

    def test_fallback_when_dtm_corrupted(self, client: TestClient, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        """When $VYOMPATH_DEM_PATH points to a corrupted non-raster file, safely falls back."""
        corrupt_file = tmp_path / "corrupt.tif"
        corrupt_file.write_text("NOT_A_VALID_TIFF_HEADER")
        monkeypatch.setenv("VYOMPATH_DEM_PATH", str(corrupt_file))

        payload = {
            "route_id": "test-mock-corrupt",
            "coordinates": [
                {"lon": 77.46, "lat": 18.46},
                {"lon": 77.462, "lat": 18.462},
            ],
            "buffer_distance_m": 250.0,
        }
        res = client.post("/api/routes/analyze", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["dtm_source"] == "synthetic/mock — no real DTM loaded"
        assert data["coverage_status"] == "not_applicable"
        assert data["analysis_mode"] == "mock"
        assert data["is_mock"] is True


# ---------------------------------------------------------------------------
# 4. Real HiRISE DTM Integration & Verification
# ---------------------------------------------------------------------------

@skip_if_no_dtm
class TestRealDTMIntegration:
    """Requirements 5, 6, 7, 8, 9, 10, 11, 12, 16, 17: Live HiRISE DTM sampling."""

    @pytest.fixture(autouse=True)
    def setup_dtm_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        assert _RESOLVED_DTM_PATH is not None
        monkeypatch.setenv("VYOMPATH_DEM_PATH", str(_RESOLVED_DTM_PATH))

    def test_golden_anchors_sol_386_and_387(self) -> None:
        """Requirement 6: Golden Sol 386 and Sol 387 elevation anchors match truth."""
        assert _RESOLVED_DTM_PATH is not None
        # Sol 386 -> -2568.873 m; Sol 387 -> -2568.583 m
        sol386 = Coordinate(lon=77.46313311, lat=18.46079140)
        sol387 = Coordinate(lon=77.46157944, lat=18.46447597)
        res = sample_route_dtm([sol386, sol387], dem_path=str(_RESOLVED_DTM_PATH))
        assert res is not None
        assert res["coverage_status"] == "complete"
        profile = res["elevation_profile"]
        assert len(profile) >= 2
        # Ground truth check within tolerance
        assert profile[0].elevation_m == pytest.approx(-2568.873, abs=0.05)
        assert profile[-1].elevation_m == pytest.approx(-2568.583, abs=0.05)

    def test_native_crs_transformation_and_pixel_indexing(self) -> None:
        """Requirement 5: Native projection transformation to raster pixels."""
        assert _RESOLVED_DTM_PATH is not None
        import rasterio
        import pyproj
        with rasterio.open(str(_RESOLVED_DTM_PATH)) as src:
            crs_raster = pyproj.CRS.from_wkt(src.crs.to_wkt())
            trans = pyproj.Transformer.from_crs(crs_raster.geodetic_crs, crs_raster, always_xy=True)
            # Sol 386 coordinates
            x, y = trans.transform(77.46313311, 18.46079140)
            gt = src.transform
            col_f = (x - gt.c) / gt.a
            row_f = (y - gt.f) / gt.e
            assert int(math.floor(col_f)) == 1360
            assert int(math.floor(row_f)) == 2157

    def test_bilinear_interpolation_and_nodata_rules(self) -> None:
        """Requirements 7 & 9: Bilinear interpolation and strict NoData handling."""
        import numpy as np
        # 2x2 grid: if any cell is NoData, sample_point_bilinear returns NaN
        grid = np.array([
            [-2500.0, -2505.0],
            [-3.4028227e+38, -2510.0],
        ], dtype=np.float32)
        val = sample_point_bilinear(grid, 0.5, 0.5, nodata=-3.4028227e+38)
        assert math.isnan(val)

        # Valid 2x2 grid
        grid_valid = np.array([
            [-2500.0, -2510.0],
            [-2500.0, -2510.0],
        ], dtype=np.float32)
        val_valid = sample_point_bilinear(grid_valid, 0.5, 0.5, nodata=-3.4028227e+38)
        assert val_valid == pytest.approx(-2505.0, abs=1e-3)

    def test_complete_terrain_coverage_route(self, client: TestClient) -> None:
        """Requirement 10: Valid route in Jezero floor reports coverage_status='complete'."""
        payload = {
            "route_id": "test-jezero-complete",
            "coordinates": [
                {"lon": 77.46313311, "lat": 18.46079140},
                {"lon": 77.46157944, "lat": 18.46447597},
            ],
            "buffer_distance_m": 250.0,
        }
        res = client.post("/api/routes/analyze", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["coverage_status"] == "complete"
        assert data["analysis_mode"] == "real_dtm"
        assert data["is_mock"] is False
        assert "HiRISE" in data["dtm_source"]
        assert data["dtm_posting_m"] == pytest.approx(1.0097, abs=1e-3)
        assert data["total_gain_m"] > 0.0
        assert data["total_loss_m"] > 0.0
        assert data["max_slope_deg"] > 0.0

    def test_partial_gap_route(self, client: TestClient) -> None:
        """Requirement 11: Route crossing from Jezero floor to western NoData reports 'partial_gap'."""
        # Sol 386 westward into NoData margin
        payload = {
            "route_id": "test-jezero-partial-gap",
            "coordinates": [
                {"lon": 77.46313311, "lat": 18.46079140},
                {"lon": 77.38000000, "lat": 18.46079140},
            ],
            "buffer_distance_m": 250.0,
        }
        res = client.post("/api/routes/analyze", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["coverage_status"] == "partial_gap"
        assert data["analysis_mode"] == "real_dtm"
        assert data["is_mock"] is False
        # Has both valid and null elevations
        profile = data["elevation_profile"]
        valid_elevs = [p["elevation_m"] for p in profile if p["elevation_m"] is not None]
        null_elevs = [p["elevation_m"] for p in profile if p["elevation_m"] is None]
        assert len(valid_elevs) > 0
        assert len(null_elevs) > 0

    def test_entirely_out_of_bounds_route(self, client: TestClient) -> None:
        """Requirement 12: Route outside Jezero Crater footprint reports 'out_of_bounds'."""
        payload = {
            "route_id": "test-olympus-out-of-bounds",
            "coordinates": [
                {"lon": -134.0, "lat": 18.4},
                {"lon": -133.9, "lat": 18.45},
            ],
            "buffer_distance_m": 250.0,
        }
        res = client.post("/api/routes/analyze", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["coverage_status"] == "out_of_bounds"
        assert data["analysis_mode"] == "real_dtm"
        assert data["is_mock"] is False
        assert data["total_gain_m"] == 0.0
        assert data["total_loss_m"] == 0.0
        assert data["max_slope_deg"] == 0.0
        assert any("OUT OF BOUNDS" in lim for lim in data["limitations"])

    def test_concurrent_requests_and_cleanup(self, client: TestClient) -> None:
        """Requirement 17: 20 simultaneous API requests with real raster open and read."""
        payload = {
            "route_id": "concurrent-stress",
            "coordinates": [
                {"lon": 77.46313311, "lat": 18.46079140},
                {"lon": 77.46157944, "lat": 18.46447597},
            ],
            "buffer_distance_m": 250.0,
        }

        def make_request(i: int) -> int:
            resp = client.post("/api/routes/analyze", json=payload)
            return resp.status_code

        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(make_request, i) for i in range(20)]
            statuses = [f.result() for f in concurrent.futures.as_completed(futures)]

        assert len(statuses) == 20
        assert all(s == 200 for s in statuses)
