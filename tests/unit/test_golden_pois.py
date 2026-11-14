"""Golden POI Corridor Fixture Cross-Validation Tests (Nov 2–8, Spec v3.1).

Validates that coords.cross_along_m() reproduces the ground-truth cross-track
and along-route distances from tests/fixtures/golden_pois.json within 1 m
tolerance, using the independent local equidistant plane projection method
(Coding Master Manual v3.1 § 5.7, Build Timeline v3.1 § 5.6 Dheer Oct 28–Nov 8).

Ground-truth source:
  tests/fixtures/golden_pois.json  — Shyam+Dheer corridor fixture file
  tests/fixtures/validation/demo_route_sol_corridor_*_10m.json

These tests are the Pranav-side counterpart verifying that coords.py geometry
functions (local_xy_m + cross_along_m) reproduce the golden cross_along values
that Dheer's nearby_pois() must also match, closing the rule-to-test traceability
loop required by Build Timeline v3.1 § 5.5 (Nov 9–13 Dheer handoff).

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

# SOL coordinates from docs/terrain-spec.md § 6 (Ground-Truth Test Anchors)
_SOL_386 = {"lon": 77.46313311, "lat": 18.4607914, "id": "POI-M20-SOL-386"}
_SOL_387 = {"lon": 77.46157944, "lat": 18.46447597, "id": "POI-M20-SOL-387"}

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
# Golden POI Corridor Fixture: 100m corridor (Sol 386 + 387)
# ---------------------------------------------------------------------------

class TestGoldenPoisCorridor100m:
    """Verify cross_along_m matches golden_pois.json for the 100m corridor fixture.

    Fixture: tests/fixtures/validation/demo_route_sol_corridor_100m_10m.json
    Buffer: 100m — both Sol 386 and Sol 387 are inside.
    Tolerance: 1.0 m for both cross-track and along-route distances.
    """

    @pytest.fixture(autouse=True)
    def load_route(self):
        fixture = _VALIDATION_DIR / "demo_route_sol_corridor_100m_10m.json"
        if not fixture.exists():
            pytest.skip(f"{fixture.name} not found in fixtures/validation/")
        self.route_xy, self.lon0, self.lat0 = _load_route_xy(fixture)

    def test_sol386_cross_track_within_1m(self):
        """Sol 386 cross-track distance matches golden fixture within 1 m."""
        p = _poi_xy(_SOL_386["lon"], _SOL_386["lat"], self.lon0, self.lat0)
        cross, _ = cross_along_m(self.route_xy, p)
        # golden_pois.json: cross_track_m = 11.20
        assert cross == pytest.approx(11.20, abs=1.0), (
            f"Sol 386 cross-track {cross:.3f} m is outside 1 m tolerance of 11.20 m"
        )

    def test_sol386_along_route_within_1m(self):
        """Sol 386 along-route distance matches golden fixture within 1 m."""
        p = _poi_xy(_SOL_386["lon"], _SOL_386["lat"], self.lon0, self.lat0)
        _, along = cross_along_m(self.route_xy, p)
        # golden_pois.json: along_route_m = 169.28
        assert along == pytest.approx(169.28, abs=1.0), (
            f"Sol 386 along-route {along:.3f} m is outside 1 m tolerance of 169.28 m"
        )

    def test_sol387_cross_track_within_1m(self):
        """Sol 387 cross-track distance matches golden fixture within 1 m."""
        p = _poi_xy(_SOL_387["lon"], _SOL_387["lat"], self.lon0, self.lat0)
        cross, _ = cross_along_m(self.route_xy, p)
        # golden_pois.json: cross_track_m = 63.38
        assert cross == pytest.approx(63.38, abs=1.0), (
            f"Sol 387 cross-track {cross:.3f} m is outside 1 m tolerance of 63.38 m"
        )

    def test_sol387_along_route_within_1m(self):
        """Sol 387 along-route distance matches golden fixture within 1 m."""
        p = _poi_xy(_SOL_387["lon"], _SOL_387["lat"], self.lon0, self.lat0)
        _, along = cross_along_m(self.route_xy, p)
        # golden_pois.json: along_route_m = 398.65
        assert along == pytest.approx(398.65, abs=1.0), (
            f"Sol 387 along-route {along:.3f} m is outside 1 m tolerance of 398.65 m"
        )

    def test_both_pois_inside_100m_buffer(self):
        """Both Sol 386 and Sol 387 must have cross-track <= 100m (inside corridor)."""
        for sol in (_SOL_386, _SOL_387):
            p = _poi_xy(sol["lon"], sol["lat"], self.lon0, self.lat0)
            cross, _ = cross_along_m(self.route_xy, p)
            assert cross <= 100.0 + 1.0, (
                f"{sol['id']} cross-track {cross:.2f} m exceeds 100m buffer"
            )


# ---------------------------------------------------------------------------
# Golden POI Corridor Fixture: 302m route — 250m boundary test
# ---------------------------------------------------------------------------

class TestGoldenPoisCorridor302mBoundary:
    """Boundary case: Sol 386 is at the 250m boundary, Sol 387 is outside (>250m).

    Fixture: tests/fixtures/validation/demo_route_sol_corridor_302m_10m.json
    Buffer: 250m — only Sol 386 is within the buffer.
    Tolerance: 1.0 m.
    """

    @pytest.fixture(autouse=True)
    def load_route(self):
        fixture = _VALIDATION_DIR / "demo_route_sol_corridor_302m_10m.json"
        if not fixture.exists():
            pytest.skip(f"{fixture.name} not found in fixtures/validation/")
        self.route_xy, self.lon0, self.lat0 = _load_route_xy(fixture)

    def test_sol386_cross_track_at_250m_boundary(self):
        """Sol 386 cross-track matches the 250m boundary distance within 1 m."""
        p = _poi_xy(_SOL_386["lon"], _SOL_386["lat"], self.lon0, self.lat0)
        cross, _ = cross_along_m(self.route_xy, p)
        # golden_pois.json: cross_track_m = 250.00
        assert cross == pytest.approx(250.0, abs=1.0), (
            f"Sol 386 cross-track {cross:.3f} m is outside 1 m tolerance of 250.00 m"
        )

    def test_sol386_along_route_within_1m(self):
        """Sol 386 along-route distance matches golden fixture within 1 m."""
        p = _poi_xy(_SOL_386["lon"], _SOL_386["lat"], self.lon0, self.lat0)
        _, along = cross_along_m(self.route_xy, p)
        # golden_pois.json: along_route_m = 206.92
        assert along == pytest.approx(206.92, abs=1.0)

    def test_sol387_outside_250m_buffer(self):
        """Sol 387 is outside the 250m buffer (cross-track > 250m)."""
        p = _poi_xy(_SOL_387["lon"], _SOL_387["lat"], self.lon0, self.lat0)
        cross, _ = cross_along_m(self.route_xy, p)
        # golden_pois.json for 302m_full_350m: cross_track_m = 302.18
        assert cross > 250.0, (
            f"Sol 387 cross-track {cross:.2f} m should be > 250m for the 302m route"
        )


# ---------------------------------------------------------------------------
# Golden POI Corridor Fixture: 302m route — 350m full corridor
# ---------------------------------------------------------------------------

class TestGoldenPoisCorridor302mFull:
    """Full 350m buffer: both Sol 386 and Sol 387 captured on 302m route.

    Fixture: tests/fixtures/validation/demo_route_sol_corridor_302m_10m.json
    Buffer: 350m — both Sol 386 (250m) and Sol 387 (302m) are inside.
    Tolerance: 1.0 m.
    """

    @pytest.fixture(autouse=True)
    def load_route(self):
        fixture = _VALIDATION_DIR / "demo_route_sol_corridor_302m_10m.json"
        if not fixture.exists():
            pytest.skip(f"{fixture.name} not found in fixtures/validation/")
        self.route_xy, self.lon0, self.lat0 = _load_route_xy(fixture)

    def test_sol387_cross_track_within_1m(self):
        """Sol 387 cross-track on 302m route matches golden fixture within 1 m."""
        p = _poi_xy(_SOL_387["lon"], _SOL_387["lat"], self.lon0, self.lat0)
        cross, _ = cross_along_m(self.route_xy, p)
        # golden_pois.json: cross_track_m = 302.18
        assert cross == pytest.approx(302.18, abs=1.0)

    def test_sol387_along_route_within_1m(self):
        """Sol 387 along-route on 302m route matches golden fixture within 1 m."""
        p = _poi_xy(_SOL_387["lon"], _SOL_387["lat"], self.lon0, self.lat0)
        _, along = cross_along_m(self.route_xy, p)
        # golden_pois.json: along_route_m = 436.45
        assert along == pytest.approx(436.45, abs=1.0)

    def test_both_pois_inside_350m_buffer(self):
        """Both Sol 386 and Sol 387 must have cross-track <= 350m."""
        for sol in (_SOL_386, _SOL_387):
            p = _poi_xy(sol["lon"], sol["lat"], self.lon0, self.lat0)
            cross, _ = cross_along_m(self.route_xy, p)
            assert cross <= 350.0 + 1.0, (
                f"{sol['id']} cross-track {cross:.2f} m exceeds 350m buffer"
            )


# ---------------------------------------------------------------------------
# Golden POI Fixture File Integrity
# ---------------------------------------------------------------------------

class TestGoldenPoisFixtureIntegrity:
    """Verify golden_pois.json is well-formed and internally consistent."""

    def test_fixture_file_exists(self):
        """golden_pois.json must exist in tests/fixtures/."""
        assert _GOLDEN_POIS_PATH.exists(), (
            "tests/fixtures/golden_pois.json is missing. "
            "Run Dheer/Shyam's golden POI corridor generation task."
        )

    def test_three_corridor_tests_present(self):
        """Exactly 3 corridor test entries must be present in golden_pois.json."""
        with open(_GOLDEN_POIS_PATH) as f:
            data = json.load(f)
        assert len(data["corridor_tests"]) == 3

    def test_sol386_and_sol387_are_sourced(self):
        """Sol 386 and Sol 387 POI IDs must appear across the corridor tests."""
        with open(_GOLDEN_POIS_PATH) as f:
            data = json.load(f)
        all_ids: set[str] = set()
        for ct in data["corridor_tests"]:
            for ep in ct["expected_pois"]:
                all_ids.add(ep["id"])
        assert "POI-M20-SOL-386" in all_ids
        assert "POI-M20-SOL-387" in all_ids

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
