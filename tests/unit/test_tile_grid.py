"""Unit tests for Mars 2000 Equirectangular Tile Grid & Regional Tile Generator.

Covers:
  - Master Coding Manual v3.1 § 5.4 tile index formulas:
      tile_index(77.45, 18.44, 15) -> (15, 46867, 13027)
      tile_index(0.0, 0.0, 0) -> (0, 1, 0)
  - Tile bounds calculation & centroid round-trip stability.
  - Automated cross-validation against tests/fixtures/tile_indices.json.
  - Cross-module consistency between scripts/build_regional_tiles.py and scripts/arya/tile_index.py.
  - TileJSON metadata schema validation.

Run with:
    python3 -m pytest tests/unit/test_tile_grid.py -v
"""

from __future__ import annotations

import json
import math
import pathlib
import pytest

from scripts.build_regional_tiles import (
    HX,
    HY,
    MARS_RADIUS_M,
    RES0,
    generate_tiles_json,
    get_tile_range_for_bounds,
    tile_bounds_lonlat,
    tile_bounds_projected,
    tile_index,
)
from scripts.arya.tile_index import (
    tile_index as arya_tile_index,
    tile_bounds as arya_tile_bounds,
)

FIXTURES_DIR = pathlib.Path(__file__).parent.parent / "fixtures"
TILE_INDICES_FIXTURE = FIXTURES_DIR / "tile_indices.json"


class TestTileIndexFormulas:
    """Validate core mathematical formulas against Master Manual § 5.4."""

    def test_golden_perseverance_claim(self):
        """Manual test claim: tile_index(77.45, 18.44, 15) -> (15, 46867, 13027)."""
        z, x, y = tile_index(77.45, 18.44, 15)
        assert z == 15
        assert x == 46867
        assert y == 13027

    def test_prime_meridian_equator_zoom_0(self):
        """Prime meridian at equator: (0, 0) at zoom 0 must be in right column (x=1, y=0)."""
        z, x, y = tile_index(0.0, 0.0, 0)
        assert z == 0
        assert x == 1
        assert y == 0

    def test_top_left_origin_zoom_0(self):
        """Top-left origin (-180, +90) at zoom 0 is tile (0, 0, 0)."""
        z, x, y = tile_index(-180.0, 90.0, 0)
        assert z == 0
        assert x == 0
        assert y == 0

    def test_bottom_right_corner_zoom_0(self):
        """Bottom-right extreme (+180, -90) at zoom 0 is clamped to (0, 1, 0)."""
        z, x, y = tile_index(180.0, -90.0, 0)
        assert z == 0
        assert x == 1
        assert y == 0

    def test_zoom_0_dimensions_are_two_by_one(self):
        """Zoom 0 has 2 columns (x=0, 1) and 1 row (y=0)."""
        # West hemisphere (-90, 0)
        assert tile_index(-90.0, 0.0, 0) == (0, 0, 0)
        # East hemisphere (+90, 0)
        assert tile_index(90.0, 0.0, 0) == (0, 1, 0)


class TestTileBoundsAndCentroidRoundTrip:
    """Validate that bounding boxes round-trip cleanly to tile indices."""

    @pytest.mark.parametrize("z,x,y", [
        (0, 0, 0),
        (0, 1, 0),
        (1, 2, 1),
        (12, 5858, 1627),
        (15, 46867, 13027),
    ])
    def test_centroid_round_trip(self, z: int, x: int, y: int):
        """The centroid of any tile's bounding box must index back to that exact tile."""
        min_lon, min_lat, max_lon, max_lat = tile_bounds_lonlat(z, x, y)
        mid_lon = (min_lon + max_lon) / 2.0
        mid_lat = (min_lat + max_lat) / 2.0

        res_z, res_x, res_y = tile_index(mid_lon, mid_lat, z)
        assert res_z == z
        assert res_x == x
        assert res_y == y

    def test_tile_bounds_projected_dimensions(self):
        """Projected width and height of each tile must equal 256 * resolution."""
        z = 15
        expected_span = 256.0 * RES0 / (2.0 ** z)
        min_x, min_y, max_x, max_y = tile_bounds_projected(z, 46867, 13027)
        assert pytest.approx(max_x - min_x, abs=1e-6) == expected_span
        assert pytest.approx(max_y - min_y, abs=1e-6) == expected_span


class TestCrossModuleConsistencyWithArya:
    """Assert build_regional_tiles.py produces identical numbers to scripts/arya/tile_index.py."""

    @pytest.mark.parametrize("lon,lat,z", [
        (77.45, 18.44, 15),
        (77.46313311, 18.4607914, 15),  # Sol 386
        (77.46157944, 18.46447597, 15),  # Sol 387
        (0.0, 0.0, 0),
        (-180.0, 90.0, 10),
        (179.99, -89.99, 12),
    ])
    def test_index_matches_arya_tooling(self, lon: float, lat: float, z: int):
        our_result = tile_index(lon, lat, z)
        arya_result = arya_tile_index(lon, lat, z)
        assert our_result == arya_result

    def test_bounds_matches_arya_tooling(self):
        our_bounds = tile_bounds_lonlat(15, 46867, 13027)
        arya_bounds = arya_tile_bounds(15, 46867, 13027)
        # Both return (min_lon, min_lat, max_lon, max_lat)
        for val_our, val_arya in zip(our_bounds, arya_bounds):
            assert pytest.approx(val_our, abs=1e-6) == val_arya


class TestTileIndicesFixtureVerification:
    """Validate all landmark coordinates recorded in tests/fixtures/tile_indices.json."""

    @pytest.mark.skipif(not TILE_INDICES_FIXTURE.exists(), reason="tile_indices.json not present")
    def test_all_fixture_points_match_computed_indices(self):
        with open(TILE_INDICES_FIXTURE) as f:
            data = json.load(f)

        points = data.get("points", [])
        assert len(points) >= 10, "Fixture must test at least 10 landmark points"

        for p in points:
            lon = p["lon"]
            lat = p["lat"]
            z = p["z"]
            expected = tuple(p.get("expected") or p.get("expected_index"))

            computed = tile_index(lon, lat, z)
            assert computed == expected, (
                f"Landmark {p.get('name', 'unnamed')} ({lon}, {lat}) at z={z}: "
                f"computed {computed} != expected {expected}"
            )


class TestTilesJsonGenerator:
    """Validate TileJSON metadata generator."""

    def test_tiles_json_structure(self):
        meta = generate_tiles_json(
            name="Jezero Test",
            description="Test tiles",
            version="1.0.0",
            min_zoom=10,
            max_zoom=15,
            bounds_lonlat=(77.4, 18.3, 77.6, 18.5),
            center_lonlat_zoom=(77.5, 18.4, 12),
            tiles_url_template="/tiles/{z}/{x}/{y}.png",
        )
        assert meta["tilejson"] == "3.0.0"
        assert meta["scheme"] == "xyz"
        assert meta["minzoom"] == 10
        assert meta["maxzoom"] == 15
        assert meta["bounds"] == [77.4, 18.3, 77.6, 18.5]
        assert meta["center"] == [77.5, 18.4, 12]
        assert meta["format"] == "png"
