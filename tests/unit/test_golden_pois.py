"""Golden POI Corridor Fixture Cross-Validation Tests (Nov 2–8, Spec v3.1).

Validates that coords.cross_along_m() reproduces the ground-truth cross-track
and along-route distances from tests/fixtures/golden_pois.json within 1 m
tolerance, using the independent local equidistant plane projection method
(Coding Master Manual v3.1 § 5.7, Build Timeline v3.1 § 5.6 Dheer Oct 28–Nov 8).

Ground-truth source:
  tests/fixtures/golden_pois.json  — Synthetic corridor benchmark fixture file
  tests/fixtures/validation/demo_route_sol_corridor_*_10m.json

These tests verify that coords.py geometry functions (local_xy_m + cross_along_m)
reproduce the golden cross_along values within 1 m tolerance.

Run with:
    python3 -m pytest tests/unit/test_golden_pois.py -v
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pytest

from backend.app.services.coords import local_xy_m, cross_along_m

# ---------------------------------------------------------------------------
# Fixture paths
# ---------------------------------------------------------------------------

_FIXTURES_DIR = Path("tests/fixtures")
_VALIDATION_DIR = _FIXTURES_DIR / "validation"
_GOLDEN_POIS_PATH = _FIXTURES_DIR / "golden_pois.json"

# Synthetic Ground-Truth Test Anchors (per Issue #11 rights-compliant remediation)
_SYNTH_POI_1 = {"lon": 77.4635, "lat": 18.4600, "id": "SYNTH-POI-001"}
_SYNTH_POI_2 = {"lon": 77.4620, "lat": 18.4650, "id": "SYNTH-POI-002"}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_route_xy(fixture_path: Path):
    """Load a corridor fixture and build local XY plane from sample_points.

    Returns:
        route_xy: (N, 2) numpy array of projected (x, y) metres.
        lon0, lat0: Projection origin (first sample point).
    """
    with open(fixture_path) as f:
        data = json.load(f)
    pts = [(p["coordinates"][0], p["coordinates"][1]) for p in data["sample_points"]]
    lon0, lat0 = pts[0]
    route_xy = np.array([local_xy_m(lon, lat, lon0, lat0) for lon, lat in pts])
    return route_xy, lon0, lat0


def _poi_xy(lon: float, lat: float, lon0: float, lat0: float) -> np.ndarray:
    """Project a POI lon/lat into the local equidistant plane."""
    return np.array(local_xy_m(lon, lat, lon0, lat0))


# ---------------------------------------------------------------------------
# Golden POI Corridor Fixture: 100m corridor (SYNTH-POI-001 + SYNTH-POI-002)
# ---------------------------------------------------------------------------

class TestGoldenPoisCorridor100m:
    """Verify cross_along_m matches golden_pois.json for the 100m corridor fixture.

    Fixture: tests/fixtures/validation/demo_route_sol_corridor_100m_10m.json
    Buffer: 100m — both SYNTH-POI-001 and SYNTH-POI-002 are inside.
    Tolerance: 1.0 m for both cross-track and along-route distances.
    """

    @pytest.fixture(autouse=True)
    def load_route(self):
        fixture = _VALIDATION_DIR / "demo_route_sol_corridor_100m_10m.json"
        if not fixture.exists():
            pytest.skip(f"{fixture.name} not found in fixtures/validation/")
        self.route_xy, self.lon0, self.lat0 = _load_route_xy(fixture)

    def test_synth1_cross_track_within_1m(self):
        """SYNTH-POI-001 cross-track distance matches golden fixture within 1 m."""
        p = _poi_xy(_SYNTH_POI_1["lon"], _SYNTH_POI_1["lat"], self.lon0, self.lat0)
        cross, _ = cross_along_m(self.route_xy, p)
        # golden_pois.json: cross_track_m = 1.85
        assert cross == pytest.approx(1.85, abs=1.0), (
            f"SYNTH-POI-001 cross-track {cross:.3f} m is outside 1 m tolerance of 1.85 m"
        )

    def test_synth1_along_route_within_1m(self):
        """SYNTH-POI-001 along-route distance matches golden fixture within 1 m."""
        p = _poi_xy(_SYNTH_POI_1["lon"], _SYNTH_POI_1["lat"], self.lon0, self.lat0)
        _, along = cross_along_m(self.route_xy, p)
        # golden_pois.json: along_route_m = 119.73
        assert along == pytest.approx(119.73, abs=1.0), (
            f"SYNTH-POI-001 along-route {along:.3f} m is outside 1 m tolerance of 119.73 m"
        )

    def test_synth2_cross_track_within_1m(self):
        """SYNTH-POI-002 cross-track distance matches golden fixture within 1 m."""
        p = _poi_xy(_SYNTH_POI_2["lon"], _SYNTH_POI_2["lat"], self.lon0, self.lat0)
        cross, _ = cross_along_m(self.route_xy, p)
        # golden_pois.json: cross_track_m = 35.17
        assert cross == pytest.approx(35.17, abs=1.0), (
            f"SYNTH-POI-002 cross-track {cross:.3f} m is outside 1 m tolerance of 35.17 m"
        )

    def test_synth2_along_route_within_1m(self):
        """SYNTH-POI-002 along-route distance matches golden fixture within 1 m."""
        p = _poi_xy(_SYNTH_POI_2["lon"], _SYNTH_POI_2["lat"], self.lon0, self.lat0)
        _, along = cross_along_m(self.route_xy, p)
        # golden_pois.json: along_route_m = 425.62
        assert along == pytest.approx(425.62, abs=1.0), (
            f"SYNTH-POI-002 along-route {along:.3f} m is outside 1 m tolerance of 425.62 m"
        )

    def test_both_pois_inside_100m_buffer(self):
        """Both SYNTH-POI-001 and SYNTH-POI-002 must have cross-track <= 100m (inside corridor)."""
        for poi in (_SYNTH_POI_1, _SYNTH_POI_2):
            p = _poi_xy(poi["lon"], poi["lat"], self.lon0, self.lat0)
            cross, _ = cross_along_m(self.route_xy, p)
            assert cross <= 100.0 + 1.0, (
                f"{poi['id']} cross-track {cross:.2f} m exceeds 100m buffer"
            )


# ---------------------------------------------------------------------------
# Golden POI Corridor Fixture: 302m route — 250m boundary test
# ---------------------------------------------------------------------------

class TestGoldenPoisCorridor302mBoundary:
    """Boundary case: SYNTH-POI-001 is within 250m, SYNTH-POI-002 is outside (>250m).

    Fixture: tests/fixtures/validation/demo_route_sol_corridor_302m_10m.json
    Buffer: 250m — only SYNTH-POI-001 is within the buffer.
    Tolerance: 1.0 m.
    """

    @pytest.fixture(autouse=True)
    def load_route(self):
        fixture = _VALIDATION_DIR / "demo_route_sol_corridor_302m_10m.json"
        if not fixture.exists():
            pytest.skip(f"{fixture.name} not found in fixtures/validation/")
        self.route_xy, self.lon0, self.lat0 = _load_route_xy(fixture)

    def test_synth1_cross_track_within_250m_boundary(self):
        """SYNTH-POI-001 cross-track is within the 250m boundary distance."""
        p = _poi_xy(_SYNTH_POI_1["lon"], _SYNTH_POI_1["lat"], self.lon0, self.lat0)
        cross, _ = cross_along_m(self.route_xy, p)
        # golden_pois.json: cross_track_m = 236.95
        assert cross == pytest.approx(236.95, abs=1.0), (
            f"SYNTH-POI-001 cross-track {cross:.3f} m is outside 1 m tolerance of 236.95 m"
        )

    def test_synth1_along_route_within_1m(self):
        """SYNTH-POI-001 along-route distance matches golden fixture within 1 m."""
        p = _poi_xy(_SYNTH_POI_1["lon"], _SYNTH_POI_1["lat"], self.lon0, self.lat0)
        _, along = cross_along_m(self.route_xy, p)
        # golden_pois.json: along_route_m = 157.50
        assert along == pytest.approx(157.50, abs=1.0)

    def test_synth2_outside_250m_buffer(self):
        """SYNTH-POI-002 is outside the 250m buffer (cross-track > 250m)."""
        p = _poi_xy(_SYNTH_POI_2["lon"], _SYNTH_POI_2["lat"], self.lon0, self.lat0)
        cross, _ = cross_along_m(self.route_xy, p)
        # golden_pois.json for 302m_full_350m: cross_track_m = 273.98
        assert cross > 250.0, (
            f"SYNTH-POI-002 cross-track {cross:.2f} m should be > 250m for the 302m route"
        )


# ---------------------------------------------------------------------------
# Golden POI Corridor Fixture: 302m route — 350m full corridor
# ---------------------------------------------------------------------------

class TestGoldenPoisCorridor302mFull:
    """Full 350m buffer: both SYNTH-POI-001 and SYNTH-POI-002 captured on 302m route.

    Fixture: tests/fixtures/validation/demo_route_sol_corridor_302m_10m.json
    Buffer: 350m — both SYNTH-POI-001 (236.95m) and SYNTH-POI-002 (273.98m) are inside.
    Tolerance: 1.0 m.
    """

    @pytest.fixture(autouse=True)
    def load_route(self):
        fixture = _VALIDATION_DIR / "demo_route_sol_corridor_302m_10m.json"
        if not fixture.exists():
            pytest.skip(f"{fixture.name} not found in fixtures/validation/")
        self.route_xy, self.lon0, self.lat0 = _load_route_xy(fixture)

    def test_synth2_cross_track_within_1m(self):
        """SYNTH-POI-002 cross-track on 302m route matches golden fixture within 1 m."""
        p = _poi_xy(_SYNTH_POI_2["lon"], _SYNTH_POI_2["lat"], self.lon0, self.lat0)
        cross, _ = cross_along_m(self.route_xy, p)
        # golden_pois.json: cross_track_m = 273.98
        assert cross == pytest.approx(273.98, abs=1.0)

    def test_synth2_along_route_within_1m(self):
        """SYNTH-POI-002 along-route on 302m route matches golden fixture within 1 m."""
        p = _poi_xy(_SYNTH_POI_2["lon"], _SYNTH_POI_2["lat"], self.lon0, self.lat0)
        _, along = cross_along_m(self.route_xy, p)
        # golden_pois.json: along_route_m = 463.44
        assert along == pytest.approx(463.44, abs=1.0)

    def test_both_pois_inside_350m_buffer(self):
        """Both SYNTH-POI-001 and SYNTH-POI-002 must have cross-track <= 350m."""
        for poi in (_SYNTH_POI_1, _SYNTH_POI_2):
            p = _poi_xy(poi["lon"], poi["lat"], self.lon0, self.lat0)
            cross, _ = cross_along_m(self.route_xy, p)
            assert cross <= 350.0 + 1.0, (
                f"{poi['id']} cross-track {cross:.2f} m exceeds 350m buffer"
            )


# ---------------------------------------------------------------------------
# Golden POI Fixture File Integrity
# ---------------------------------------------------------------------------

class TestGoldenPoisFixtureIntegrity:
    """Verify golden_pois.json is well-formed and internally consistent."""

    def test_fixture_file_exists(self):
        """golden_pois.json must exist in tests/fixtures/."""
        assert _GOLDEN_POIS_PATH.exists(), (
            "tests/fixtures/golden_pois.json is missing."
        )

    def test_three_corridor_tests_present(self):
        """Exactly 3 corridor test entries must be present in golden_pois.json."""
        with open(_GOLDEN_POIS_PATH) as f:
            data = json.load(f)
        assert len(data["corridor_tests"]) == 3

    def test_synthetic_pois_are_sourced(self):
        """SYNTH-POI-001 and SYNTH-POI-002 POI IDs must appear across the corridor tests."""
        with open(_GOLDEN_POIS_PATH) as f:
            data = json.load(f)
        all_ids: set[str] = set()
        for ct in data["corridor_tests"]:
            for ep in ct["expected_pois"]:
                all_ids.add(ep["id"])
        assert "SYNTH-POI-001" in all_ids
        assert "SYNTH-POI-002" in all_ids

    def test_mars_radius_in_fixture_matches_spec(self):
        """Mars radius constant in golden_pois.json must equal MARS_RADIUS_M = 3,396,190 m."""
        with open(_GOLDEN_POIS_PATH) as f:
            data = json.load(f)
        assert data["mars_radius_m"] == pytest.approx(3_396_190.0, abs=1.0)

    def test_cross_track_values_non_negative(self):
        """All cross_track_m values in golden_pois.json must be non-negative."""
        with open(_GOLDEN_POIS_PATH) as f:
            data = json.load(f)
        for ct in data["corridor_tests"]:
            for ep in ct["expected_pois"]:
                assert ep["cross_track_m"] >= 0.0, (
                    f"Negative cross_track_m in test {ct['test_id']} for POI {ep['id']}"
                )

    def test_along_route_values_positive(self):
        """All along_route_m values must be positive (cannot be at route start)."""
        with open(_GOLDEN_POIS_PATH) as f:
            data = json.load(f)
        for ct in data["corridor_tests"]:
            for ep in ct["expected_pois"]:
                assert ep["along_route_m"] > 0.0, (
                    f"Non-positive along_route_m in test {ct['test_id']} for POI {ep['id']}"
                )
