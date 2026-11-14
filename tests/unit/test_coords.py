"""Unit tests for VyomPath Coordinate Mathematics Service (coords.py).

Tests:
  - Mars reference radius constants.
  - Longitude normalization (scalar and array).
  - Haversine distance on Mars 2000 Sphere (scalar and array).
  - Local tangent plane conversion (local_xy_m).
  - Cross-track and along-track projections (cross_along_m).
"""

import math
import numpy as np
import pytest

from backend.app.services.coords import (
    MARS_RADIUS_M,
    MARS_CIRCUMFERENCE_M,
    normalize_longitude,
    haversine_m,
    surface_distance_3d_m,
    local_xy_m,
    cross_along_m,
)


class TestCoordsConstants:
    """Validate planetary geodetic constants."""

    def test_mars_radius(self):
        assert MARS_RADIUS_M == 3_396_190.0

    def test_mars_circumference(self):
        expected = 2.0 * math.pi * 3_396_190.0
        assert math.isclose(MARS_CIRCUMFERENCE_M, expected, rel_tol=1e-9)


class TestNormalizeLongitude:
    """Test longitude normalization to [-180, 180)."""

    def test_scalar_normalization(self):
        assert normalize_longitude(0.0) == 0.0
        assert normalize_longitude(180.0) == -180.0
        assert normalize_longitude(-180.0) == -180.0
        assert normalize_longitude(181.0) == pytest.approx(-179.0)
        assert normalize_longitude(-181.0) == pytest.approx(179.0)
        assert normalize_longitude(360.0) == 0.0

    def test_array_normalization(self):
        lons = np.array([-270.0, -180.0, 0.0, 180.0, 270.0])
        expected = np.array([90.0, -180.0, 0.0, -180.0, -90.0])
        result = normalize_longitude(lons)
        np.testing.assert_allclose(result, expected, atol=1e-9)


class TestHaversineCoords:
    """Test Haversine distance engine in coords.py."""

    def test_same_point_returns_zero(self):
        assert haversine_m(77.45, 18.44, 77.45, 18.44) == 0.0

    def test_equatorial_one_degree(self):
        # 1 degree at the equator on Mars 2000
        d = haversine_m(0.0, 0.0, 1.0, 0.0)
        expected = MARS_CIRCUMFERENCE_M / 360.0
        assert pytest.approx(d, rel=1e-6) == expected

    def test_antimeridian_wrap(self):
        # Traversal from 179° to -179° is 2 degrees, not 358 degrees
        d = haversine_m(179.0, 0.0, -179.0, 0.0)
        expected = (MARS_CIRCUMFERENCE_M / 360.0) * 2.0
        assert pytest.approx(d, rel=1e-5) == expected

    def test_vectorized_haversine(self):
        lon1 = np.array([0.0, 10.0, 77.0])
        lat1 = np.array([0.0, 0.0, 18.0])
        lon2 = np.array([1.0, 10.0, 77.0])
        lat2 = np.array([0.0, 1.0, 19.0])

        dists = haversine_m(lon1, lat1, lon2, lat2)
        assert isinstance(dists, np.ndarray)
        assert len(dists) == 3
        assert pytest.approx(dists[0], rel=1e-6) == MARS_CIRCUMFERENCE_M / 360.0
        assert pytest.approx(dists[1], rel=1e-6) == MARS_CIRCUMFERENCE_M / 360.0


class TestSurfaceDistance3D:
    """Test 3D along-ground surface distance calculation (v3.1)."""

    def test_flat_terrain_equals_2d_distance(self):
        # dz = 0 -> 3D distance equals 2D distance exactly
        d3d = surface_distance_3d_m(d2d_m=5.0, dz_m=0.0)
        assert pytest.approx(d3d, abs=1e-9) == 5.0

    def test_3d_pythagorean_step(self):
        # 3-4-5 right triangle: 2D step 4m, elevation rise 3m -> 3D distance 5m
        d3d = surface_distance_3d_m(d2d_m=4.0, dz_m=3.0)
        assert pytest.approx(d3d, abs=1e-9) == 5.0

    def test_negative_dz_loss_treated_identically(self):
        # Drop of 3m gives same 3D distance
        d3d = surface_distance_3d_m(d2d_m=4.0, dz_m=-3.0)
        assert pytest.approx(d3d, abs=1e-9) == 5.0

    def test_vectorized_surface_distance(self):
        d2d = np.array([3.0, 5.0, 12.0])
        dz = np.array([4.0, 12.0, 5.0])
        d3d = surface_distance_3d_m(d2d, dz)
        np.testing.assert_allclose(d3d, [5.0, 13.0, 13.0], atol=1e-9)



class TestLocalXY:
    """Test local tangent plane projection (local_xy_m)."""

    def test_origin_is_zero(self):
        x, y = local_xy_m(77.5, 18.3, lon0=77.5, lat0=18.3)
        assert pytest.approx(float(x), abs=1e-9) == 0.0
        assert pytest.approx(float(y), abs=1e-9) == 0.0

    def test_offset_north_and_east(self):
        lon0, lat0 = 77.5, 18.3
        # 1 degree north should be approx pi/180 * R
        _, y = local_xy_m(lon0, lat0 + 1.0, lon0=lon0, lat0=lat0)
        expected_y = math.radians(1.0) * MARS_RADIUS_M
        assert pytest.approx(float(y), rel=1e-6) == expected_y

        # 1 degree east should be approx pi/180 * cos(lat0) * R
        x, _ = local_xy_m(lon0 + 1.0, lat0, lon0=lon0, lat0=lat0)
        expected_x = math.radians(1.0) * math.cos(math.radians(lat0)) * MARS_RADIUS_M
        assert pytest.approx(float(x), rel=1e-6) == expected_x


class TestCrossAlongTrack:
    """Test cross_along_m projection helper."""

    def test_point_on_horizontal_segment(self):
        # Route along X axis from (0, 0) to (1000, 0)
        route = np.array([[0.0, 0.0], [1000.0, 0.0]])
        # Point at (400, 0) -> cross-track = 0, along-track = 400
        cross, along = cross_along_m(route, [400.0, 0.0])
        assert pytest.approx(cross, abs=1e-6) == 0.0
        assert pytest.approx(along, abs=1e-6) == 400.0

    def test_point_offset_perpendicular(self):
        route = np.array([[0.0, 0.0], [1000.0, 0.0]])
        # Point at (500, 50) -> cross-track = 50, along-track = 500
        cross, along = cross_along_m(route, [500.0, 50.0])
        assert pytest.approx(cross, abs=1e-6) == 50.0
        assert pytest.approx(along, abs=1e-6) == 500.0

    def test_multi_segment_route(self):
        # L-shaped route: (0,0) -> (100, 0) -> (100, 100)
        route = np.array([[0.0, 0.0], [100.0, 0.0], [100.0, 100.0]])
        # Point near second segment: (110, 40)
        # Closest point on route is (100, 40)
        # Cross distance is 10 m, along-route is 100 + 40 = 140 m
        cross, along = cross_along_m(route, [110.0, 40.0])
        assert pytest.approx(cross, abs=1e-6) == 10.0
        assert pytest.approx(along, abs=1e-6) == 140.0

    def test_clamped_projection_outside_endpoints(self):
        route = np.array([[0.0, 0.0], [100.0, 0.0]])
        # Point before start: (-20, 0) -> clamped to start (0, 0)
        cross, along = cross_along_m(route, [-20.0, 0.0])
        assert pytest.approx(cross, abs=1e-6) == 20.0
        assert pytest.approx(along, abs=1e-6) == 0.0

        # Point past end: (150, 0) -> clamped to end (100, 0)
        cross, along = cross_along_m(route, [150.0, 0.0])
        assert pytest.approx(cross, abs=1e-6) == 50.0
        assert pytest.approx(along, abs=1e-6) == 100.0

    def test_requires_at_least_two_points(self):
        with pytest.raises(ValueError, match="at least 2 vertices"):
            cross_along_m([[0.0, 0.0]], [10.0, 10.0])
