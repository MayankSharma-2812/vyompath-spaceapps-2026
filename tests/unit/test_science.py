"""Unit tests for the Science POI corridor-buffer service and coords module.

Covers:
- coords.py: MARS_RADIUS_M = 3,396,190 m, haversine_m, local_xy_m, cross_along_m
- Catalogue loading and validation (missing files, bad entries, dual path)
- Corridor buffer algorithm (on-route, inside, outside, boundary cases)
- Multi-segment routes and along-route ordering
- Jezero AOI demo route detection
- Edge cases (empty catalogue, single coordinate, malformed entries)

Owner: Dheer | NASA Space Apps Challenge 2026
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pytest

from backend.app.schemas import Coordinate
from backend.app.services.coords import (
    MARS_RADIUS_M,
    cross_along_m,
    haversine_m,
    local_xy_m,
)
from backend.app.services.science import (
    _MARS_RADIUS_M,
    _load_catalogue,
    _m_per_deg_lat,
    nearby_pois,
    nearby_points,
)


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------

def _write_catalogue(tmp_path: Path, entries: list[dict]) -> Path:
    """Write a temporary science_points.json and return its path."""
    path = tmp_path / "science_points.json"
    path.write_text(json.dumps(entries), encoding="utf-8")
    return path


def _make_poi(
    poi_id: str = "test-poi",
    name: str = "Test POI",
    lon: float = 0.0,
    lat: float = 0.0,
    mission: str = "Test Mission",
    source_url: str = "https://example.com",
    significance: str = "Test significance",
) -> dict:
    """Create a single POI dict with sensible defaults."""
    return {
        "id": poi_id,
        "name": name,
        "lon": lon,
        "lat": lat,
        "mission": mission,
        "source_url": source_url,
        "significance": significance,
    }


# ---------------------------------------------------------------------------
# coords.py unit tests
# ---------------------------------------------------------------------------

class TestCoordsModule:
    """Tests for the shared coords.py functions."""

    def test_mars_radius_constant(self):
        """Standard radius must match Mars 2000 sphere R = 3,396,190.0 m (Decision D4)."""
        assert MARS_RADIUS_M == 3_396_190.0
        assert _MARS_RADIUS_M == 3_396_190.0

    def test_haversine_equator(self):
        """1 degree of latitude should be approx ~59,275 m."""
        dist = haversine_m(0.0, 0.0, 0.0, 1.0)
        expected = MARS_RADIUS_M * math.radians(1.0)
        assert dist == pytest.approx(expected, abs=0.5)

    def test_local_xy_m_projection(self):
        """Offset of (1 deg lon, 1 deg lat) relative to (0,0) at equator."""
        x, y = local_xy_m(1.0, 1.0, 0.0, 0.0)
        expected = MARS_RADIUS_M * math.radians(1.0)
        assert float(x) == pytest.approx(expected, abs=1.0)
        assert float(y) == pytest.approx(expected, abs=1.0)

    def test_cross_along_m_point_on_segment(self):
        """Point on straight line: cross-track is 0, along-route matches distance."""
        route_xy = np.array([[0.0, 0.0], [1000.0, 0.0]])
        p = np.array([300.0, 0.0])
        cross, along = cross_along_m(route_xy, p)
        assert cross == pytest.approx(0.0, abs=1e-3)
        assert along == pytest.approx(300.0, abs=1e-3)

    def test_cross_along_m_perpendicular_offset(self):
        """Point 50m north of segment midpoint."""
        route_xy = np.array([[0.0, 0.0], [1000.0, 0.0]])
        p = np.array([500.0, 50.0])
        cross, along = cross_along_m(route_xy, p)
        assert cross == pytest.approx(50.0, abs=1e-3)
        assert along == pytest.approx(500.0, abs=1e-3)


# ---------------------------------------------------------------------------
# Catalogue loading tests
# ---------------------------------------------------------------------------

class TestLoadCatalogue:
    """Tests for _load_catalogue validation and error handling."""

    def test_missing_file_returns_empty(self, tmp_path: Path):
        """A non-existent catalogue file should return []."""
        missing = tmp_path / "does_not_exist.json"
        assert _load_catalogue(missing) == []

    def test_empty_list(self, tmp_path: Path):
        """An empty JSON list should return []."""
        path = _write_catalogue(tmp_path, [])
        assert _load_catalogue(path) == []

    def test_valid_entries_are_returned(self, tmp_path: Path):
        """All well-formed entries should be loaded."""
        entries = [_make_poi("a"), _make_poi("b")]
        path = _write_catalogue(tmp_path, entries)
        result = _load_catalogue(path)
        assert len(result) == 2
        assert result[0]["id"] == "a"
        assert result[1]["id"] == "b"

    def test_entry_missing_field_is_skipped(self, tmp_path: Path):
        """An entry missing required fields should be silently skipped."""
        good = _make_poi("good")
        bad = {"id": "bad", "name": "No coords"}  # missing lon, lat, etc.
        path = _write_catalogue(tmp_path, [good, bad])
        result = _load_catalogue(path)
        assert len(result) == 1
        assert result[0]["id"] == "good"

    def test_non_numeric_coords_skipped(self, tmp_path: Path):
        """An entry with non-numeric lon/lat should be skipped."""
        bad = _make_poi("bad")
        bad["lon"] = "not_a_number"
        path = _write_catalogue(tmp_path, [bad])
        assert _load_catalogue(path) == []

    def test_non_list_json_returns_empty(self, tmp_path: Path):
        """A JSON file containing an object (not a list) should return []."""
        path = tmp_path / "science_points.json"
        path.write_text('{"not": "a list"}', encoding="utf-8")
        assert _load_catalogue(path) == []

    def test_non_dict_entries_skipped(self, tmp_path: Path):
        """Non-dict items inside the list should be skipped."""
        path = tmp_path / "science_points.json"
        path.write_text('[42, "string", null]', encoding="utf-8")
        assert _load_catalogue(path) == []

    def test_real_catalogue_loads(self):
        """The actual shipped catalogue should load 5 strictly sourced MMGIS POIs."""
        data = _load_catalogue()
        assert isinstance(data, list)
        assert len(data) == 5
        ids = {p["id"] for p in data}
        assert "POI-M20-SOL-386" in ids
        assert "POI-M20-SOL-387" in ids
        assert "POI-M20-SOL-013" in ids

    def test_catalogue_schema_support_both_formats(self, tmp_path: Path):
        """Service should load both dict-with-points schema and flat list schema."""
        schema_a = {
            "version": "1.0.0",
            "points": [
                {
                    "id": "A1",
                    "name": "Point A1",
                    "coordinates": [77.4, 18.4],
                    "mission": "Test",
                    "source_url": "https://example.com",
                    "significance": "A1 significance",
                }
            ],
        }
        path_a = tmp_path / "schema_a.json"
        path_a.write_text(json.dumps(schema_a), encoding="utf-8")
        loaded_a = _load_catalogue(path_a)
        assert len(loaded_a) == 1
        assert loaded_a[0]["id"] == "A1"
        assert loaded_a[0]["lon"] == 77.4
        assert loaded_a[0]["lat"] == 18.4


# ---------------------------------------------------------------------------
# Corridor buffer algorithm tests
# ---------------------------------------------------------------------------

class TestNearbyPoints:
    """Tests for the corridor-buffer search algorithm."""

    def test_point_directly_on_route(self, tmp_path: Path):
        """A POI on the route centreline should have cross_track_m ~ 0."""
        poi = _make_poi("on-route", lon=0.0, lat=0.0)
        cat = _write_catalogue(tmp_path, [poi])

        route = [Coordinate(lon=-1.0, lat=0.0), Coordinate(lon=1.0, lat=0.0)]
        result = nearby_pois(route, buffer_distance_m=500.0, catalogue_path=cat)

        assert len(result) == 1
        assert result[0].id == "on-route"
        assert result[0].cross_track_m == pytest.approx(0.0, abs=1.0)

    def test_point_inside_buffer(self, tmp_path: Path):
        """A POI 100 m from the route should be found in a 500 m buffer."""
        offset_deg = 100.0 / _m_per_deg_lat()
        poi = _make_poi("inside", lon=0.0, lat=offset_deg)
        cat = _write_catalogue(tmp_path, [poi])

        route = [Coordinate(lon=-1.0, lat=0.0), Coordinate(lon=1.0, lat=0.0)]
        result = nearby_pois(route, buffer_distance_m=500.0, catalogue_path=cat)

        assert len(result) == 1
        assert result[0].id == "inside"
        assert result[0].cross_track_m == pytest.approx(100.0, rel=0.05)

    def test_point_outside_buffer(self, tmp_path: Path):
        """A POI 1000 m from the route should NOT be in a 500 m buffer."""
        offset_deg = 1000.0 / _m_per_deg_lat()
        poi = _make_poi("outside", lon=0.0, lat=offset_deg)
        cat = _write_catalogue(tmp_path, [poi])

        route = [Coordinate(lon=-1.0, lat=0.0), Coordinate(lon=1.0, lat=0.0)]
        result = nearby_pois(route, buffer_distance_m=500.0, catalogue_path=cat)

        assert len(result) == 0

    def test_boundary_just_inside(self, tmp_path: Path):
        """A POI 240 m from the route should be found in a 250 m buffer."""
        offset_deg = 240.0 / _m_per_deg_lat()
        poi = _make_poi("boundary-in", lon=0.0, lat=offset_deg)
        cat = _write_catalogue(tmp_path, [poi])

        route = [Coordinate(lon=-1.0, lat=0.0), Coordinate(lon=1.0, lat=0.0)]
        result = nearby_pois(route, buffer_distance_m=250.0, catalogue_path=cat)

        assert len(result) == 1
        assert result[0].id == "boundary-in"

    def test_boundary_just_outside(self, tmp_path: Path):
        """A POI 260 m from the route should NOT be in a 250 m buffer."""
        offset_deg = 260.0 / _m_per_deg_lat()
        poi = _make_poi("boundary-out", lon=0.0, lat=offset_deg)
        cat = _write_catalogue(tmp_path, [poi])

        route = [Coordinate(lon=-1.0, lat=0.0), Coordinate(lon=1.0, lat=0.0)]
        result = nearby_pois(route, buffer_distance_m=250.0, catalogue_path=cat)

        assert len(result) == 0

    def test_multi_segment_route(self, tmp_path: Path):
        """POIs should be found along a route with 3+ waypoints."""
        poi1 = _make_poi("p1", lon=0.5, lat=0.0)
        poi2 = _make_poi("p2", lon=1.5, lat=0.0)
        cat = _write_catalogue(tmp_path, [poi1, poi2])

        route = [
            Coordinate(lon=0.0, lat=0.0),
            Coordinate(lon=1.0, lat=0.0),
            Coordinate(lon=2.0, lat=0.0),
        ]
        result = nearby_pois(route, buffer_distance_m=500.0, catalogue_path=cat)

        assert len(result) == 2
        ids = {r.id for r in result}
        assert ids == {"p1", "p2"}

    def test_results_sorted_by_along_route(self, tmp_path: Path):
        """Results must be ordered by along_route_m ascending."""
        poi_far = _make_poi("far", lon=1.5, lat=0.0)
        poi_near = _make_poi("near", lon=0.5, lat=0.0)
        cat = _write_catalogue(tmp_path, [poi_far, poi_near])

        route = [Coordinate(lon=0.0, lat=0.0), Coordinate(lon=2.0, lat=0.0)]
        result = nearby_pois(route, buffer_distance_m=500.0, catalogue_path=cat)

        assert len(result) == 2
        assert result[0].id == "near"
        assert result[1].id == "far"
        assert result[0].along_route_m < result[1].along_route_m

    def test_empty_catalogue_returns_empty(self, tmp_path: Path):
        """An empty catalogue should produce no results."""
        cat = _write_catalogue(tmp_path, [])
        route = [Coordinate(lon=0.0, lat=0.0), Coordinate(lon=1.0, lat=0.0)]
        assert nearby_pois(route, buffer_distance_m=500.0, catalogue_path=cat) == []

    def test_single_coordinate_returns_empty(self, tmp_path: Path):
        """A route with < 2 points cannot form a line; return []."""
        poi = _make_poi("p", lon=0.0, lat=0.0)
        cat = _write_catalogue(tmp_path, [poi])
        result = nearby_pois(
            [Coordinate(lon=0.0, lat=0.0)],
            buffer_distance_m=500.0,
            catalogue_path=cat,
        )
        assert result == []

    def test_malformed_entry_skipped_gracefully(self, tmp_path: Path):
        """A bad catalogue entry should be skipped; good ones still work."""
        good = _make_poi("good", lon=0.0, lat=0.0)
        bad = {"id": "bad"}
        cat = _write_catalogue(tmp_path, [good, bad])

        route = [Coordinate(lon=-1.0, lat=0.0), Coordinate(lon=1.0, lat=0.0)]
        result = nearby_pois(route, buffer_distance_m=500.0, catalogue_path=cat)

        assert len(result) == 1
        assert result[0].id == "good"

    def test_along_route_distance_is_plausible(self, tmp_path: Path):
        """along_route_m for a POI at the midpoint should be ~ half the total length."""
        poi = _make_poi("mid", lon=0.0, lat=0.0)
        cat = _write_catalogue(tmp_path, [poi])

        route = [Coordinate(lon=-1.0, lat=0.0), Coordinate(lon=1.0, lat=0.0)]
        result = nearby_pois(route, buffer_distance_m=500.0, catalogue_path=cat)

        assert len(result) == 1
        expected_half = 1.0 * _MARS_RADIUS_M * math.pi / 180.0
        assert result[0].along_route_m == pytest.approx(expected_half, rel=0.01)

    def test_missing_catalogue_file_returns_empty(self, tmp_path: Path):
        """If the catalogue file doesn't exist, return [] gracefully."""
        missing = tmp_path / "nonexistent.json"
        route = [Coordinate(lon=0.0, lat=0.0), Coordinate(lon=1.0, lat=0.0)]
        result = nearby_pois(route, buffer_distance_m=500.0, catalogue_path=missing)
        assert result == []

    def test_nearby_points_alias(self, tmp_path: Path):
        """nearby_points alias must return the identical result as nearby_pois."""
        poi = _make_poi("test", lon=0.0, lat=0.0)
        cat = _write_catalogue(tmp_path, [poi])
        route = [Coordinate(lon=-1.0, lat=0.0), Coordinate(lon=1.0, lat=0.0)]
        res1 = nearby_pois(route, buffer_distance_m=250.0, catalogue_path=cat)
        res2 = nearby_points(route, buffer_distance_m=250.0, catalogue_path=cat)
        assert res1 == res2

    def test_bundle_sol_corridor_100m(self):
        """Bundle demo route sol corridor 100m should find Sol 386 and Sol 387."""
        fixture_path = (
            Path(__file__).resolve().parent.parent
            / "fixtures"
            / "validation"
            / "demo_route_sol_corridor_100m_10m.json"
        )
        assert fixture_path.exists(), f"Missing fixture at {fixture_path}"

        with open(fixture_path, encoding="utf-8") as f:
            data = json.load(f)

        route = [
            Coordinate(lon=pt["coordinates"][0], lat=pt["coordinates"][1])
            for pt in data["sample_points"]
        ]
        results = nearby_pois(route, buffer_distance_m=100.0)

        assert len(results) == 2
        p386 = next(r for r in results if r.id == "POI-M20-SOL-386")
        p387 = next(r for r in results if r.id == "POI-M20-SOL-387")

        # Analytical values from bundle: 11.2m cross-track, 169.28m along-route
        assert p386.cross_track_m == pytest.approx(11.20, abs=0.5)
        assert p386.along_route_m == pytest.approx(169.28, abs=0.5)

        # Analytical values from bundle: 63.38m cross-track, 398.65m along-route
        assert p387.cross_track_m == pytest.approx(63.38, abs=0.5)
        assert p387.along_route_m == pytest.approx(398.65, abs=0.5)

    def test_bundle_sol_386_boundary_condition(self):
        """Sol 386 sits at exactly 250.00 m cross-track on the 302 m route.
        At buffer_distance_m=250.0, it MUST be included.
        At buffer_distance_m=249.0, it MUST be excluded.
        """
        fixture_path = (
            Path(__file__).resolve().parent.parent
            / "fixtures"
            / "validation"
            / "demo_route_sol_corridor_302m_10m.json"
        )
        assert fixture_path.exists(), f"Missing fixture at {fixture_path}"

        with open(fixture_path, encoding="utf-8") as f:
            data = json.load(f)

        route = [
            Coordinate(lon=pt["coordinates"][0], lat=pt["coordinates"][1])
            for pt in data["sample_points"]
        ]

        # 250.0m buffer: Sol 386 is on boundary (included)
        res_250 = nearby_pois(route, buffer_distance_m=250.0)
        assert any(r.id == "POI-M20-SOL-386" for r in res_250)
        assert not any(r.id == "POI-M20-SOL-387" for r in res_250)

        # 249.0m buffer: Sol 386 is excluded
        res_249 = nearby_pois(route, buffer_distance_m=249.0)
        assert not any(r.id == "POI-M20-SOL-386" for r in res_249)

        # 350.0m buffer: both Sol 386 and Sol 387 included
        res_350 = nearby_pois(route, buffer_distance_m=350.0)
        assert len(res_350) == 2


# ---------------------------------------------------------------------------
# Golden Fixture tests (Definition of Done: matches within 1 m)
# ---------------------------------------------------------------------------

class TestGoldenPOIFixtures:
    """Verifies that nearby_pois() reproduces golden reference fixtures within 1 m."""

    def test_golden_fixtures_match_within_one_meter(self):
        fixtures_path = (
            Path(__file__).resolve().parent.parent / "fixtures" / "golden_pois.json"
        )
        assert fixtures_path.exists(), f"Missing fixtures file at {fixtures_path}"

        repo_root = Path(__file__).resolve().parents[2]

        with open(fixtures_path, encoding="utf-8") as f:
            data = json.load(f)

        for case in data["corridor_tests"]:
            fixture_rel = case["route_fixture_path"]
            route_file = repo_root / fixture_rel
            assert route_file.exists(), f"Missing route fixture file: {route_file}"

            with open(route_file, encoding="utf-8") as rf:
                route_data = json.load(rf)

            route = [
                Coordinate(lon=pt["coordinates"][0], lat=pt["coordinates"][1])
                for pt in route_data["sample_points"]
            ]

            buffer_m = case["buffer_distance_m"]
            results = nearby_pois(route, buffer_distance_m=buffer_m)

            expected_list = case["expected_pois"]
            assert len(results) == len(
                expected_list
            ), f"Case '{case['test_id']}': expected {len(expected_list)} POIs, got {len(results)}"

            for actual, expected in zip(results, expected_list):
                assert actual.id == expected["id"]
                assert actual.cross_track_m == pytest.approx(
                    expected["cross_track_m"], abs=1.0
                ), f"Case '{case['test_id']}' POI {actual.id} cross_track mismatch: {actual.cross_track_m} vs {expected['cross_track_m']}"
                assert actual.along_route_m == pytest.approx(
                    expected["along_route_m"], abs=1.0
                ), f"Case '{case['test_id']}' POI {actual.id} along_route mismatch: {actual.along_route_m} vs {expected['along_route_m']}"


