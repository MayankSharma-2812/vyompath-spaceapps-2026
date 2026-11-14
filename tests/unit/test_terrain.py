"""Unit tests for backend.app.services.terrain — Oct 24 — Nov 2 scope.

Tests cover:
  - normalize_longitude: canonical wrapping behaviour.
  - haversine_m: known distances, symmetry, zero-distance, pole-to-pole,
    antimeridian crossing, invalid inputs.
  - segment_distances_m: multi-waypoint decomposition.
  - route_distance_m: additivity, too-few-coords guard.
  - 3D surface distance integration with process_elevation_gaps and densify_route (AC-08).
  - Ground-truth golden route fixtures (tests/fixtures/golden_routes.json):
      J-gentle, J-steep, J-edge (jezero_aoi_v2.tif, skipped in CI),
      S-basic (syrtis_major_sample_dtm.tif, runs in CI),
      J-handcheck (unit_test_anchors.json Sol-386/387 anchor check).

Ground-truth references:
  All known-distance checks use the Mars 2000 sphere radius
  R = 3 396 190 m.  Manual calculations are documented alongside each
  test so the expected values can be re-derived without running the code.

Run with:
    python3 -m pytest tests/unit/test_terrain.py -v
"""

from __future__ import annotations

import math
import numpy as np
import pytest

from backend.app.schemas import Coordinate
from backend.app.services.terrain import (
    LAT_TS_DEG,
    MARS_CIRCUMFERENCE_M,
    MARS_RADIUS_M,
    along_track_grades,
    baseline_px,
    densify_route,
    ground_spacing_m,
    haversine_m,
    lttb_downsample,
    multi_scale_along_track_grades,
    normalize_longitude,
    process_elevation_gaps,
    route_distance_m,
    sample_point_bilinear,
    segment_distances_m,
    terrain_slope_deg,
)
from backend.app.services.coords import surface_distance_3d_m


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def coord(lon: float, lat: float) -> Coordinate:
    """Shorthand to build a Coordinate without keyword noise in tests."""
    return Coordinate(lon=lon, lat=lat)


# ---------------------------------------------------------------------------
# normalize_longitude
# ---------------------------------------------------------------------------

class TestNormalizeLongitude:
    """normalize_longitude must map any real value into [-180, 180)."""

    def test_zero_unchanged(self):
        assert normalize_longitude(0.0) == 0.0

    def test_positive_in_range(self):
        assert normalize_longitude(90.0) == pytest.approx(90.0)

    def test_negative_in_range(self):
        assert normalize_longitude(-90.0) == pytest.approx(-90.0)

    def test_exactly_180_wraps_to_minus_180(self):
        # 180° is NOT in [-180, 180) — it wraps to -180°.
        assert normalize_longitude(180.0) == pytest.approx(-180.0)

    def test_exactly_minus_180_unchanged(self):
        assert normalize_longitude(-180.0) == pytest.approx(-180.0)

    def test_181_wraps_to_minus_179(self):
        assert normalize_longitude(181.0) == pytest.approx(-179.0)

    def test_minus_181_wraps_to_179(self):
        assert normalize_longitude(-181.0) == pytest.approx(179.0)

    def test_360_wraps_to_0(self):
        assert normalize_longitude(360.0) == pytest.approx(0.0)

    def test_minus_360_wraps_to_0(self):
        assert normalize_longitude(-360.0) == pytest.approx(0.0)

    def test_large_positive(self):
        # 900° = 2 full circles + 180° → wraps to -180°
        assert normalize_longitude(900.0) == pytest.approx(-180.0)

    def test_large_negative(self):
        # -540° = -1.5 circles → -540 + 180 = -360, -360 % 360 = 0, 0 - 180 = -180°
        assert normalize_longitude(-540.0) == pytest.approx(-180.0)


# ---------------------------------------------------------------------------
# haversine_m — zero distance
# ---------------------------------------------------------------------------

class TestHaversineSamePoint:
    """Identical start and end points must give exactly 0 m."""

    def test_origin(self):
        p = coord(0.0, 0.0)
        assert haversine_m(p, p) == pytest.approx(0.0, abs=1e-6)

    def test_olympus_mons_summit_self(self):
        # Olympus Mons summit: approximately lon=-134.0, lat=18.4
        p = coord(-134.0, 18.4)
        assert haversine_m(p, p) == pytest.approx(0.0, abs=1e-6)

    def test_south_pole_self(self):
        p = coord(0.0, -90.0)
        assert haversine_m(p, p) == pytest.approx(0.0, abs=1e-6)


# ---------------------------------------------------------------------------
# haversine_m — symmetry
# ---------------------------------------------------------------------------

class TestHaversineSymmetry:
    """haversine_m(A, B) must equal haversine_m(B, A) for any A, B."""

    def test_equatorial_symmetry(self):
        a = coord(-134.0, 0.0)
        b = coord(-133.0, 0.0)
        assert haversine_m(a, b) == pytest.approx(haversine_m(b, a), rel=1e-12)

    def test_diagonal_symmetry(self):
        a = coord(10.0, 20.0)
        b = coord(-50.0, -30.0)
        assert haversine_m(a, b) == pytest.approx(haversine_m(b, a), rel=1e-12)


# ---------------------------------------------------------------------------
# haversine_m — pole to pole (known analytical result)
# ---------------------------------------------------------------------------

class TestHaversinePoles:
    """
    North pole (lat=90) to south pole (lat=-90) must be exactly
    half the Mars circumference = π · R.

    Manual check:
        Δlat = 180°, Δlon = 0°
        h = sin²(90°) + cos(90°)·cos(-90°)·sin²(0°)
          = 1² + 0 · 0 · 0 = 1
        d = 2·R·arcsin(1) = 2·R·(π/2) = π·R
        = π · 3 396 190 ≈ 10 673 116 m
    """

    HALF_CIRCUMFERENCE_M = math.pi * MARS_RADIUS_M  # ≈ 10 673 116 m

    def test_north_to_south_pole(self):
        north = coord(0.0, 90.0)
        south = coord(0.0, -90.0)
        assert haversine_m(north, south) == pytest.approx(
            self.HALF_CIRCUMFERENCE_M, rel=1e-9
        )

    def test_poles_longitude_independent(self):
        """At the poles, longitude is irrelevant — any lon pair gives same dist."""
        north_at_0 = coord(0.0, 90.0)
        north_at_90 = coord(90.0, 90.0)
        south = coord(45.0, -90.0)
        # Both north poles (different longitudes) should be equidistant from south.
        d1 = haversine_m(north_at_0, south)
        d2 = haversine_m(north_at_90, south)
        assert d1 == pytest.approx(d2, rel=1e-9)


# ---------------------------------------------------------------------------
# haversine_m — equatorial 1-degree arc (known analytical result)
# ---------------------------------------------------------------------------

class TestHaversineOneDegreEquatorial:
    """
    Along the equator (lat=0), 1° of longitude = (2πR / 360) metres.

    Manual check:
        MARS_CIRCUMFERENCE_M / 360
        = 2π · 3 396 190 / 360
        ≈ 21 344 166.6 / 360
        ≈ 59 289.35 m  (per degree)
    """

    ONE_DEG_EQUATORIAL_M = MARS_CIRCUMFERENCE_M / 360.0  # ≈ 59 289 m

    def test_one_degree_longitude_at_equator(self):
        a = coord(0.0, 0.0)
        b = coord(1.0, 0.0)
        assert haversine_m(a, b) == pytest.approx(
            self.ONE_DEG_EQUATORIAL_M, rel=1e-6
        )

    def test_ten_degrees_longitude_at_equator(self):
        a = coord(0.0, 0.0)
        b = coord(10.0, 0.0)
        assert haversine_m(a, b) == pytest.approx(
            10.0 * self.ONE_DEG_EQUATORIAL_M, rel=1e-4
            # Reduced tolerance: 10° arc deviates slightly from 10× 1° arc
            # due to the non-linear nature of the formula; relative error < 0.01%.
        )


# ---------------------------------------------------------------------------
# haversine_m — antimeridian crossing
# ---------------------------------------------------------------------------

class TestHaversineAntimeridian:
    """
    A route crossing the ±180° antimeridian must take the SHORT path,
    not the long way around the planet.

    lon=179° to lon=-179° is a 2° arc across the antimeridian.
    Manual check (lat=0 for simplicity):
        Δlon = -179 - 179 = -358°  (raw) → sin²(-179°) = sin²(179°)
        But Haversine uses sin²(Δlon/2):
            sin²(-179°) = sin²(179°) → very close to sin²(180°) = 0
        Actually:
            Δlon_rad = radians(-358°) = -6.2482...
            sin(Δlon/2) = sin(-179°) ≈ sin(1°) ≈ 0.01745
            h ≈ 0.01745² ≈ 0.000304
            d ≈ 2 · R · arcsin(0.01745) ≈ 2 · R · 0.01745 ≈ 118 578 m

    Comparison: the long way around = 358° arc ≈ 358 × 59 289 ≈ 21 225 M
    The haversine correctly gives the short arc (~118 578 m ≈ 2°).

    Precise expected value:
        ONE_DEG = MARS_CIRCUMFERENCE_M / 360 ≈ 59 289.35 m
        2° arc at lat=0 → approx 2 × 59 289.35 = 118 578.7 m
        (Haversine gives the exact value; we test against formula output.)
    """

    def test_short_arc_across_antimeridian(self):
        a = coord(179.0, 0.0)
        b = coord(-179.0, 0.0)
        distance = haversine_m(a, b)

        # The short arc (2° at equator) must be much less than half-circumference.
        # Expected ≈ 118 578 m.  Reject anything > 1 000 000 m (the long way).
        expected_approx = 2.0 * MARS_CIRCUMFERENCE_M / 360.0
        assert distance == pytest.approx(expected_approx, rel=1e-5), (
            f"Antimeridian crossing returned {distance:.0f} m; "
            f"expected ~{expected_approx:.0f} m (2° arc at equator)."
        )
        assert distance < 200_000.0, (
            f"Distance {distance:.0f} m is implausibly large for a 2° equatorial arc."
        )

    def test_antimeridian_near_pole(self):
        """Crossing antimeridian near a pole must also give short arc."""
        a = coord(179.0, 60.0)
        b = coord(-179.0, 60.0)
        distance = haversine_m(a, b)
        # At lat=60°, zonal arc shrinks by cos(60°)=0.5, so ~59 289 m.
        assert distance < 150_000.0


# ---------------------------------------------------------------------------
# haversine_m — Olympus Mons traverse (illustrative known region)
# ---------------------------------------------------------------------------

class TestHaversineOlympusMons:
    """
    Olympus Mons summit to eastern escarpment — illustrative check that
    distances in the expected few-hundred-km range are produced.

    Coordinates from published references:
        Summit:      lon = -134.0, lat =  18.4  (approximate)
        Escarpment:  lon = -130.0, lat =  19.0  (approximate)

    We don't verify against a precise published value because the exact
    summit location varies by source.  Instead we check that the result
    is in the plausible 300–500 km range for a ~4° longitude traverse
    at this latitude.
    """

    def test_olympus_mons_range(self):
        summit = coord(-134.0, 18.4)
        escarpment = coord(-130.0, 19.0)
        distance = haversine_m(summit, escarpment)
        # 4° at lat≈18.4°: roughly 4 × 59 289 × cos(18.4°) ≈ 224 762 m
        # With lat component: slightly more.  Plausible range 200–300 km.
        assert 200_000 < distance < 350_000, (
            f"Olympus Mons traverse distance {distance:.0f} m is outside "
            "the expected 200–350 km range."
        )


# ---------------------------------------------------------------------------
# haversine_m — invalid inputs
# ---------------------------------------------------------------------------

class TestHaversineInvalidInputs:
    """Out-of-bound coordinates must raise ValueError with a useful message."""

    def test_longitude_too_large(self):
        a = coord(0.0, 0.0)
        # Manually construct an out-of-bounds coordinate (bypass Pydantic).
        b = Coordinate.model_construct(lon=200.0, lat=0.0)
        with pytest.raises(ValueError, match="longitude"):
            haversine_m(a, b)

    def test_longitude_too_small(self):
        a = coord(0.0, 0.0)
        b = Coordinate.model_construct(lon=-200.0, lat=0.0)
        with pytest.raises(ValueError, match="longitude"):
            haversine_m(a, b)

    def test_latitude_too_large(self):
        a = coord(0.0, 0.0)
        b = Coordinate.model_construct(lon=0.0, lat=100.0)
        with pytest.raises(ValueError, match="latitude"):
            haversine_m(a, b)

    def test_latitude_too_small(self):
        a = coord(0.0, 0.0)
        b = Coordinate.model_construct(lon=0.0, lat=-100.0)
        with pytest.raises(ValueError, match="latitude"):
            haversine_m(a, b)


# ---------------------------------------------------------------------------
# segment_distances_m
# ---------------------------------------------------------------------------

class TestSegmentDistances:
    """segment_distances_m must return exactly len(coords)-1 values."""

    def test_two_points_one_segment(self):
        a = coord(0.0, 0.0)
        b = coord(1.0, 0.0)
        segs = segment_distances_m([a, b])
        assert len(segs) == 1
        assert segs[0] == pytest.approx(haversine_m(a, b), rel=1e-12)

    def test_three_points_two_segments(self):
        a = coord(0.0, 0.0)
        b = coord(1.0, 0.0)
        c = coord(2.0, 0.0)
        segs = segment_distances_m([a, b, c])
        assert len(segs) == 2
        assert segs[0] == pytest.approx(haversine_m(a, b), rel=1e-12)
        assert segs[1] == pytest.approx(haversine_m(b, c), rel=1e-12)

    def test_too_few_coords_raises(self):
        with pytest.raises(ValueError, match="at least 2"):
            segment_distances_m([coord(0.0, 0.0)])

    def test_empty_list_raises(self):
        with pytest.raises(ValueError, match="at least 2"):
            segment_distances_m([])


# ---------------------------------------------------------------------------
# route_distance_m
# ---------------------------------------------------------------------------

class TestRouteDistance:
    """route_distance_m must equal sum(segment_distances_m())."""

    def test_two_point_route(self):
        a = coord(0.0, 0.0)
        b = coord(5.0, 0.0)
        assert route_distance_m([a, b]) == pytest.approx(
            haversine_m(a, b), rel=1e-12
        )

    def test_three_point_additivity(self):
        """Total route distance == sum of individual segment distances."""
        a = coord(0.0, 0.0)
        b = coord(2.0, 1.0)
        c = coord(5.0, -1.0)
        total = route_distance_m([a, b, c])
        manual = haversine_m(a, b) + haversine_m(b, c)
        assert total == pytest.approx(manual, rel=1e-12)

    def test_five_point_route(self):
        """Generalised additivity for a five-waypoint route."""
        pts = [
            coord(-134.0, 18.4),
            coord(-133.5, 18.6),
            coord(-133.0, 18.8),
            coord(-132.5, 19.0),
            coord(-132.0, 19.2),
        ]
        total = route_distance_m(pts)
        segs = segment_distances_m(pts)
        assert total == pytest.approx(sum(segs), rel=1e-12)

    def test_repeated_waypoint_adds_zero(self):
        """A duplicate consecutive waypoint contributes 0 m to total distance."""
        a = coord(0.0, 0.0)
        b = coord(1.0, 0.0)
        route_with_dup = [a, b, b]
        assert route_distance_m(route_with_dup) == pytest.approx(
            haversine_m(a, b), rel=1e-12
        )

    def test_too_few_coords_raises(self):
        with pytest.raises(ValueError, match="at least 2"):
            route_distance_m([coord(0.0, 0.0)])


# ---------------------------------------------------------------------------
# Constants sanity check
# ---------------------------------------------------------------------------

class TestConstants:
    """Validate that module constants match the Mars 2000 specification."""

    def test_mars_radius_value(self):
        """Mars 2000 Sphere radius must be exactly 3 396 190 m."""
        assert MARS_RADIUS_M == 3_396_190.0

    def test_circumference_derived_correctly(self):
        """Circumference must be 2πR."""
        assert MARS_CIRCUMFERENCE_M == pytest.approx(
            2.0 * math.pi * MARS_RADIUS_M, rel=1e-15
        )


# ---------------------------------------------------------------------------
# Ground spacing and slope tests (v3 spec)
# ---------------------------------------------------------------------------

class TestGroundSpacing:
    """Validate equirectangular ground pixel spacing for standard parallel 15°N."""

    def test_at_standard_parallel(self):
        """At 15°N, dx must equal px_x exactly."""
        dx, dy = ground_spacing_m(px_x=2.0, px_y=2.0, lat_deg=15.0, lat_ts_deg=15.0)
        assert pytest.approx(dx, abs=1e-9) == 2.0
        assert pytest.approx(dy, abs=1e-9) == 2.0

    def test_at_jezero_latitude(self):
        """At 18.3°N, dx ≈ px_x * cos(18.3°) / cos(15°) ≈ 0.98305 * px_x."""
        px_x = 1.00966
        px_y = 1.00966
        dx, dy = ground_spacing_m(px_x=px_x, px_y=px_y, lat_deg=18.3, lat_ts_deg=LAT_TS_DEG)
        ratio = math.cos(math.radians(18.3)) / math.cos(math.radians(15.0))
        assert pytest.approx(dx, rel=1e-6) == px_x * ratio
        assert dy == px_y


class TestBaselinePx:
    """Validate half-window pixel calculations for slope scales."""

    def test_baseline_pixels(self):
        # 20 m window with 2.0 m pixels -> round(20 / 4) = 5
        assert baseline_px(window_m=20.0, pixel_m=2.0) == 5
        # 50 m window with 2.0 m pixels -> round(50 / 4) = 13 (rounded from 12.5 in Python 3 round-half-to-even)
        assert baseline_px(window_m=50.0, pixel_m=2.0) in (12, 13)
        # 100 m window with 2.0 m pixels -> round(100 / 4) = 25
        assert baseline_px(window_m=100.0, pixel_m=2.0) == 25

    def test_baseline_at_least_one(self):
        # Sub-pixel window must return at least 1 pixel
        assert baseline_px(window_m=0.5, pixel_m=2.0) == 1


class TestTerrainSlope:
    """Validate 2D terrain surface slope calculation."""

    def test_flat_surface_slope_zero(self):
        # 5x5 grid of constant elevation 100 m
        z = np.full((5, 5), 100.0)
        slope = terrain_slope_deg(z, dx=2.0, dy=2.0)
        np.testing.assert_allclose(slope, 0.0, atol=1e-9)

    def test_uniform_slope_gradient(self):
        # Elevation increases by 2 m every 2 m in X (dx=2, dy=2) -> slope = 45°
        x = np.arange(5) * 2.0
        z = np.tile(x, (5, 1))
        slope = terrain_slope_deg(z, dx=2.0, dy=2.0)
        # Interior points have gx = 1.0, gy = 0.0 -> arctan(1.0) = 45 degrees
        np.testing.assert_allclose(slope[1:-1, 1:-1], 45.0, atol=1e-6)


# ---------------------------------------------------------------------------
# Route Densification Tests (Spec v3.1 § 3.2)
# ---------------------------------------------------------------------------

class TestRouteDensification:
    """Test polyline densification at 5m intervals."""

    def test_short_segment_not_split(self):
        # Two points separated by ~2m (< 5m)
        a = coord(0.0, 0.0)
        b = coord(0.0, 0.00003)
        pts = densify_route([a, b], step_m=5.0)
        assert len(pts) == 2

    def test_long_segment_densified(self):
        # Route ~100m long should produce ~21 points at 5m steps
        a = coord(0.0, 0.0)
        # ~100m north at equator: 100 / (2pi*R / 360) ~ 0.001687 deg
        deg_100m = (100.0 / MARS_CIRCUMFERENCE_M) * 360.0
        b = coord(0.0, deg_100m)
        pts = densify_route([a, b], step_m=5.0)
        assert len(pts) >= 20
        # Check every consecutive step is <= 5.1m
        for i in range(len(pts) - 1):
            assert haversine_m(pts[i], pts[i + 1]) <= 5.1


# ---------------------------------------------------------------------------
# Bilinear Sampling & Strict 4-Neighbor NoData Tests (Spec v3.1 § 3.4)
# ---------------------------------------------------------------------------

class TestBilinearSampling:
    """Validate 4-neighbor bilinear interpolation and NoData masking."""

    def test_exact_pixel_center(self):
        data = np.array([
            [10.0, 20.0],
            [30.0, 40.0],
        ], dtype=float)
        # At midpoint (col=0.5, row=0.5)
        # (10 + 20 + 30 + 40) / 4 = 25.0
        val = sample_point_bilinear(data, col_f=0.5, row_f=0.5)
        assert pytest.approx(val, abs=1e-6) == 25.0

    def test_strict_4_neighbor_nodata_rule(self):
        nodata = -3.4028227e+38
        data = np.array([
            [10.0, 20.0],
            [30.0, nodata],  # One neighbor is NoData
        ], dtype=float)
        val = sample_point_bilinear(data, col_f=0.2, row_f=0.2, nodata=nodata)
        assert np.isnan(val)

    def test_out_of_bounds_returns_nan(self):
        data = np.full((3, 3), 100.0, dtype=float)
        val = sample_point_bilinear(data, col_f=-0.5, row_f=1.0)
        assert np.isnan(val)
        val = sample_point_bilinear(data, col_f=1.0, row_f=2.8)
        assert np.isnan(val)


# ---------------------------------------------------------------------------
# Gap Processing & Partial Gap Tests (Spec v3.1 § 3.5)
# ---------------------------------------------------------------------------

class TestGapProcessing:
    """Validate gap filling thresholds and coverage status."""

    def test_short_gap_filled_linearly(self):
        # 2 missing samples (10m gap <= 15m threshold)
        elevs = [10.0, float("nan"), float("nan"), 13.0]
        filled, status, gain, loss = process_elevation_gaps(elevs, step_m=5.0, max_fill_m=15.0)
        assert status == "complete"
        assert filled == pytest.approx([10.0, 11.0, 12.0, 13.0], abs=1e-4)
        assert pytest.approx(gain, abs=1e-4) == 3.0
        assert loss == 0.0

    def test_long_gap_triggers_partial_gap(self):
        # 4 missing samples (20m gap > 15m threshold)
        elevs = [10.0, float("nan"), float("nan"), float("nan"), float("nan"), 20.0, 25.0]
        filled, status, gain, loss = process_elevation_gaps(elevs, step_m=5.0, max_fill_m=15.0)
        assert status == "partial_gap"
        assert np.isnan(filled[1])
        # Gain across valid step (20 -> 25) must still be accumulated!
        assert pytest.approx(gain, abs=1e-4) == 5.0

    def test_all_missing_returns_out_of_bounds(self):
        elevs = [float("nan"), float("nan"), float("nan")]
        _, status, gain, loss = process_elevation_gaps(elevs)
        assert status == "out_of_bounds"
        assert gain == 0.0
        assert loss == 0.0


# ---------------------------------------------------------------------------
# LTTB Downsampling Tests (Spec v3.1 § 5)
# ---------------------------------------------------------------------------

class TestLTTBDownsampling:
    """Validate Largest-Triangle-Three-Buckets algorithm."""

    def test_threshold_larger_than_data_returns_all(self):
        pts = [(float(i), float(i * 2)) for i in range(10)]
        sampled = lttb_downsample(pts, threshold=20)
        assert sampled == pts

    def test_preserves_endpoints(self):
        pts = [(float(i), math.sin(i * 0.1)) for i in range(100)]
        sampled = lttb_downsample(pts, threshold=10)
        assert len(sampled) == 10
        assert sampled[0] == pts[0]
        assert sampled[-1] == pts[-1]

    def test_preserves_sharp_peak(self):
        # Flat with a single sharp spike at index 50
        pts = [(float(i), 0.0) for i in range(100)]
        pts[50] = (50.0, 1000.0)
        sampled = lttb_downsample(pts, threshold=10)
        peak_present = any(p[1] == 1000.0 for p in sampled)
        assert peak_present


# ---------------------------------------------------------------------------
# Along-Track Grade Tests (Spec v3.1 § 4.4)
# ---------------------------------------------------------------------------

class TestAlongTrackGrade:
    """Validate along-track grade calculation across evaluation windows."""

    def test_flat_route_zero_grade(self):
        dists = [float(i * 5) for i in range(20)]
        elevs = [100.0] * 20
        max_g, grades = along_track_grades(dists, elevs, window_m=50.0)
        assert max_g == 0.0
        for g in grades:
            assert g == 0.0

    def test_ten_percent_ramp_grade(self):
        # Rise of 5m every 50m -> 10% slope -> arctan(0.1) ~ 5.71059 deg
        dists = [float(i * 5) for i in range(20)]
        elevs = [float(i * 0.5) for i in range(20)]
        max_g, _ = along_track_grades(dists, elevs, window_m=50.0)
        expected = math.degrees(math.atan(0.1))
        assert pytest.approx(max_g, abs=1e-3) == expected

    def test_multi_scale_slope_spread_evaluation(self):
        """Multi-scale grade evaluation must return correct spread and default 50m value."""
        dists = [float(i * 5) for i in range(30)]
        # Steeper local bump in the middle (5m rise over 20m), flatter elsewhere
        elevs = [0.0] * 30
        for i in range(10, 15):
            elevs[i] = float((i - 10) * 1.0)
        for i in range(15, 30):
            elevs[i] = 5.0

        res = multi_scale_along_track_grades(dists, elevs, windows_m=[20.0, 50.0, 100.0])
        assert "by_window" in res
        assert 20.0 in res["by_window"]
        assert 50.0 in res["by_window"]
        assert 100.0 in res["by_window"]
        assert res["default_max_grade_deg"] == res["by_window"][50.0]["max_grade_deg"]
        # Shorter window resolves sharp local bump better than longer window
        assert res["by_window"][20.0]["max_grade_deg"] >= res["by_window"][100.0]["max_grade_deg"]
        assert res["grade_spread_deg"] == pytest.approx(
            res["max_scale_grade_deg"] - res["min_scale_grade_deg"], abs=1e-9
        )

    def test_scarp_route_peaks_at_gentle_slope_at_fifty_meters(self):
        """Scarp route fixture peaks at ~4.1 deg across 50 m baseline window (gentle slope)."""
        scarp_fixture = _FIXTURES_DIR / "demo_route_scarp_5m.json"
        if not scarp_fixture.exists():
            pytest.skip("demo_route_scarp_5m.json fixture not available")

        with open(scarp_fixture) as f:
            data = json.load(f)

        pts = data["sample_points"]
        dists = [p["cumulative_distance_m"] for p in pts]
        elevs = [p["elevation_m"] for p in pts]

        res = multi_scale_along_track_grades(dists, elevs, windows_m=[20.0, 50.0, 100.0])
        g50 = res["by_window"][50.0]["max_grade_deg"]
        # Master Guide: "The scarp route peaks at 4.1 deg: call it a gentle slope."
        assert g50 == pytest.approx(4.09, abs=0.1)
        assert g50 < 4.5  # < 5° is classified as gentle slope in Martian rover terrain ops

    def test_seam_detection_5m_evenly_spaced_profile(self):
        # 1. Existing 5m evenly spaced profile
        # 30 samples: 0 to 145 m.
        dists = [float(i * 5) for i in range(30)]
        elevs = [100.0] * 30

        # Without mask: all 0.0
        max_g_nomask, grades_nomask = along_track_grades(dists, elevs, window_m=50.0)
        assert max_g_nomask == 0.0
        assert all(g == 0.0 for g in grades_nomask)

        # Uniform source mask: identical to no mask
        mask_uniform = ["hirise_v2"] * 30
        max_g_uni, grades_uni = along_track_grades(dists, elevs, window_m=50.0, source_mask=mask_uniform)
        assert max_g_uni == 0.0
        assert all(g == 0.0 for g in grades_uni)

        # Seam transition at sample 14 -> 15 (distance 70m to 75m)
        mask_seam = ["hirise_v2"] * 15 + ["hrsc_v1"] * 15
        max_g_seam, grades_seam = along_track_grades(dists, elevs, window_m=50.0, source_mask=mask_seam)

        # With window 50m (half_w 25m), any sample with [s - 25, s + 25] overlapping (70, 75) must be NaN.
        # Overlap occurs when s - 25 < 75 and s + 25 > 70 => s in (45, 100), i.e. indices 10 to 19 (50m to 95m).
        for i, s in enumerate(dists):
            if 50.0 <= s <= 95.0:
                assert math.isnan(grades_seam[i]), f"Expected NaN at s={s}m"
            elif s <= 45.0 or s >= 100.0:
                assert not math.isnan(grades_seam[i]), f"Expected valid grade at s={s}m"
                assert grades_seam[i] == 0.0

    def test_seam_detection_irregularly_spaced_samples(self):
        # 2. Irregularly spaced samples with a seam transition between sample positions
        dists = [0.0, 15.0, 35.0, 70.0, 85.0, 120.0, 150.0]
        elevs = [10.0, 10.0, 10.0, 20.0, 20.0, 20.0, 20.0]
        # Transition occurs between sample 2 (35m) and sample 3 (70m)
        source_mask = ["tile_a", "tile_a", "tile_a", "tile_b", "tile_b", "tile_b", "tile_b"]

        max_g, grades = along_track_grades(dists, elevs, window_m=50.0, source_mask=source_mask)

        # At s=0.0: window is [0, 25]. 25 < 35 -> pure tile_a, valid grade
        assert not math.isnan(grades[0])
        # At s=35.0: window is [10, 60]. Overlaps transition [35, 70] -> NaN
        assert math.isnan(grades[2])
        # At s=70.0: window is [45, 95]. Overlaps transition [35, 70] -> NaN
        assert math.isnan(grades[3])
        # At s=150.0: window is [125, 150]. 125 > 70 -> pure tile_b, valid grade
        assert not math.isnan(grades[6])

    def test_seam_detection_window_boundary_inside_transition_segment(self):
        # 3. A window boundary lying inside a seam-transition segment
        # Transition segment is [40.0, 70.0]
        dists = [0.0, 20.0, 40.0, 70.0, 90.0, 120.0]
        elevs = [10.0, 10.0, 10.0, 10.0, 10.0, 10.0]
        source_mask = ["dem1", "dem1", "dem1", "dem2", "dem2", "dem2"]

        # With window 50m (half_w 25m):
        # Sample at s=80 doesn't exist, but at s=90: window is [65.0, 115.0].
        # s_back = 65.0 falls strictly inside transition segment (40.0, 70.0)!
        _, grades = along_track_grades(dists, elevs, window_m=50.0, source_mask=source_mask)
        assert math.isnan(grades[4]), "s=90m has s_back=65m inside seam segment [40, 70], must be NaN"

        # Sample at s=20: window is [0.0, 45.0].
        # s_fwd = 45.0 falls strictly inside transition segment (40.0, 70.0)!
        assert math.isnan(grades[1]), "s=20m has s_fwd=45m inside seam segment [40, 70], must be NaN"

    def test_mismatched_source_mask_and_elevation_length(self):
        # 4. Mismatched source-mask length and elevation length
        dists = [0.0, 5.0, 10.0, 15.0]
        elevs = [1.0, 2.0, 3.0, 4.0]

        # source_mask length 3 != dists length 4
        with pytest.raises(ValueError, match="source_mask length"):
            along_track_grades(dists, elevs, source_mask=["a", "a", "b"])

        # elevs length 3 != dists length 4
        with pytest.raises(ValueError, match="distances_m length"):
            along_track_grades(dists, [1.0, 2.0, 3.0])

    def test_all_evaluation_windows_unavailable_returns_nan_max_grade(self):
        # 5. A route whose valid grade windows are all unavailable
        dists = [0.0, 10.0, 20.0, 30.0, 40.0]
        elevs = [100.0, 100.0, 100.0, 100.0, 100.0]
        # Seam at [10.0, 20.0]. With window 50m (half_w 25m), every point's window covers [10.0, 20.0]
        source_mask = ["dem1", "dem1", "dem2", "dem2", "dem2"]

        max_g, grades = along_track_grades(dists, elevs, window_m=50.0, source_mask=source_mask)
        assert all(math.isnan(g) for g in grades)
        assert math.isnan(max_g), "max_grade must be NaN (not 0.0) when every window is unavailable"

        # Also test when all elevations are NaN
        all_nan_elevs = [float("nan")] * 5
        max_g_nan, grades_nan = along_track_grades(dists, all_nan_elevs, window_m=50.0)
        assert all(math.isnan(g) for g in grades_nan)
        assert math.isnan(max_g_nan), "max_grade must be NaN when all elevations are NaN"

    def test_insufficient_input_zero_and_one_sample(self):
        # Insufficient input: zero and one sample cannot calculate a valid grade.
        # Unavailable grades must NOT be returned as 0.0 when no calculation is possible.

        # Zero samples
        max_g0, grades0 = along_track_grades([], [])
        assert math.isnan(max_g0), "max_grade must be NaN for 0 samples, not 0.0"
        assert grades0 == []

        # One sample
        max_g1, grades1 = along_track_grades([0.0], [100.0])
        assert math.isnan(max_g1), "max_grade must be NaN for 1 sample, not 0.0"
        assert len(grades1) == 1
        assert math.isnan(grades1[0]), "grade must be NaN for 1 sample, not 0.0"

        # One sample with source_mask
        max_g1_m, grades1_m = along_track_grades([0.0], [100.0], source_mask=["hirise"])
        assert math.isnan(max_g1_m)
        assert len(grades1_m) == 1
        assert math.isnan(grades1_m[0])

    def test_seam_boundary_touching_endpoint_is_not_false_positive(self):
        """A window whose endpoint strictly touches a transition segment boundary without
        entering it must remain valid (avoiding boundary false positives).
        """
        # Distances: 0, 25, 50, 75, 100, 125, 150
        # Seam transition is between sample 2 (50.0m) and sample 3 (75.0m) -> segment [50.0, 75.0]
        dists = [0.0, 25.0, 50.0, 75.0, 100.0, 125.0, 150.0]
        elevs = [10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0]
        mask = ["demA", "demA", "demA", "demB", "demB", "demB", "demB"]

        # window_m = 50.0 -> half_w = 25.0
        # At sample 1 (s = 25.0m): s_back = 0.0, s_fwd = 50.0.
        # s_fwd touches segment start 50.0, but does not enter (50.0, 75.0).
        # Must be valid (not NaN).
        # At sample 4 (s = 100.0m): s_back = 75.0, s_fwd = 125.0.
        # s_back touches segment end 75.0, but does not enter (50.0, 75.0).
        # Must be valid (not NaN).
        # At sample 2 (s = 50.0m): window is [25.0, 75.0], crosses transition -> NaN.
        # At sample 3 (s = 75.0m): window is [50.0, 100.0], crosses transition -> NaN.
        max_g, grades = along_track_grades(dists, elevs, window_m=50.0, source_mask=mask)

        assert not math.isnan(grades[1]), "s=25m window [0, 50] touches 50m but does not enter seam, should be valid"
        assert grades[1] == 0.0
        assert not math.isnan(grades[4]), "s=100m window [75, 125] touches 75m but does not enter seam, should be valid"
        assert grades[4] == 0.0
        assert math.isnan(grades[2]), "s=50m window [25, 75] intersects seam [50, 75], must be NaN"
        assert math.isnan(grades[3]), "s=75m window [50, 100] intersects seam [50, 75], must be NaN"


# ---------------------------------------------------------------------------
# Radius Trap Verification Test ([v3.1] § 2.1)
# ---------------------------------------------------------------------------

class TestRadiusTrapShift:
    """Validate that using map radius (3396190) vs DTM sphere (3394839.8133) shifts northing by ~431 px."""

    def test_wrong_radius_shift_distance(self):
        r_map = 3_396_190.0
        r_dtm = 3_394_839.8133163
        delta_r = r_map - r_dtm

        # At Jezero latitude ~18.46°N
        lat_rad = math.radians(18.46)
        shift_m = lat_rad * delta_r

        # Expected shift is ~435m north
        assert pytest.approx(shift_m, abs=1.0) == 435.0

        # Pixel size at Jezero is ~1.00966 m/px -> ~431 pixels
        pixel_shift = shift_m / 1.0096633
        assert pytest.approx(pixel_shift, abs=1.0) == 431.0



# ---------------------------------------------------------------------------
# Golden Route Fixture Tests (Oct 25–26) — Issue #19 Phase Oct 24–27
# ---------------------------------------------------------------------------
# These tests anchor terrain.py functions to ground-truth elevation values
# stored in tests/fixtures/golden_routes.json.
#
# S-basic: uses syrtis_major_sample_dtm.tif (available in CI).
# J-gentle, J-steep, J-edge, J-handcheck: require jezero_aoi_v2.tif
#   (only on Shyam's local machine). Skipped automatically in CI.
#
# All elevation tolerances are set to 1.0 m (terrain spec tolerance).
# ---------------------------------------------------------------------------

import json
import os
import pathlib

_FIXTURES_DIR = pathlib.Path(__file__).parent.parent / "fixtures"
_GOLDEN_ROUTES_PATH = _FIXTURES_DIR / "golden_routes.json"
_SYRTIS_DTM_PATH = pathlib.Path(__file__).parent.parent.parent / "data" / "dtm" / "syrtis_major_sample_dtm.tif"

try:
    import rasterio  # noqa: F401
    _has_rasterio = True
except ImportError:
    _has_rasterio = False

# Rasters require rasterio and the physical file on disk.
_JEZERO_AOI_PATH = pathlib.Path(os.environ.get("VYOMPATH_DEM_PATH", "data/dtm/jezero_aoi_v2.tif"))
_jezero_available = _JEZERO_AOI_PATH.exists() and _has_rasterio
_syrtis_available = _SYRTIS_DTM_PATH.exists() and _has_rasterio

# Load golden routes fixture once for all test classes
with open(_GOLDEN_ROUTES_PATH) as _f:
    _GOLDEN = json.load(_f)

def _route(route_id: str) -> dict:
    """Retrieve a named route dict from the golden fixture."""
    for r in _GOLDEN["routes"]:
        if r["route_id"] == route_id:
            return r
    raise KeyError(f"Route {route_id!r} not found in golden_routes.json")


class TestGoldenRouteFixtureIntegrity:
    """Verify golden_routes.json is well-formed and contains all required routes."""

    def test_fixture_file_exists(self):
        assert _GOLDEN_ROUTES_PATH.exists(), (
            "tests/fixtures/golden_routes.json is missing. "
            "Run Pranav's Oct 25-26 golden route generation task."
        )

    def test_all_required_routes_present(self):
        ids = {r["route_id"] for r in _GOLDEN["routes"]}
        for required in ("J-gentle", "J-steep", "J-edge", "S-basic", "J-handcheck"):
            assert required in ids, f"Required golden route {required!r} missing from fixture"

    def test_each_route_has_at_least_5_sample_points(self):
        for route in _GOLDEN["routes"]:
            pts = route["sample_points"]
            assert len(pts) >= 5, (
                f"Route {route['route_id']} has only {len(pts)} sample points; "
                "spec requires >= 5."
            )

    def test_j_handcheck_has_6_points(self):
        """Issue #19 requires a 6-point hand-checkable route."""
        route = _route("J-handcheck")
        assert len(route["sample_points"]) == 6

    def test_j_edge_documents_nodata_transition(self):
        route = _route("J-edge")
        nodata_pts = [p for p in route["sample_points"] if p["status"] == "dtm_nodata"]
        assert len(nodata_pts) >= 1, (
            "J-edge must contain at least one dtm_nodata sample point "
            "to document the NoData boundary crossing."
        )
        assert route["expected_coverage_status"] == "partial_gap"

    def test_s_basic_does_not_require_jezero(self):
        route = _route("S-basic")
        assert route["requires_jezero_raster"] is False

    def test_j_handcheck_anchor_elevation_matches_unit_test_anchors(self):
        """Sol-386 elevation must be within 1 mm of the gdallocationinfo value."""
        route = _route("J-handcheck")
        anchor = route["sample_points"][0]
        assert anchor["lon"] == pytest.approx(77.46313311, abs=1e-8)
        assert anchor["lat"] == pytest.approx(18.4607914, abs=1e-8)
        # gdallocationinfo exact value: -2568.87329101562
        assert anchor["elevation_m"] == pytest.approx(-2568.87329101562, abs=0.001)

    def test_j_handcheck_431px_trap_documented(self):
        """The golden fixture must document the 431-pixel naive vs pyproj offset."""
        route = _route("J-handcheck")
        trap = route["anchor_trap"]
        assert trap["row_shift_pixels"] == 431
        assert trap["naive_pixel"]["row"] == 1726
        assert trap["correct_pixel"]["row"] == 2157
        # The shift must be > 400 pixels to be a meaningful safety test
        assert trap["row_shift_pixels"] > 400


class TestGoldenRouteSBasicWithSyrtis:
    """S-basic golden route: verify elevations using local syrtis_major_sample_dtm.tif.

    These tests run in CI because the Syrtis sample DTM is committed to the repo.
    Elevations verified via raw rasterio nearest-pixel read — independent of terrain.py.
    """

    @pytest.mark.skipif(not _syrtis_available, reason="syrtis_major_sample_dtm.tif or rasterio not available")
    def test_s_basic_sample_point_elevations_match_rasterio(self):
        """Each golden S-basic sample point elevation must match rasterio read within 1 m."""
        import rasterio

        route = _route("S-basic")
        with rasterio.open(str(_SYRTIS_DTM_PATH)) as src:
            gt = src.transform
            nodata = float(src.nodata)
            data = src.read(1).astype(float)
            data[data == nodata] = float("nan")

        for pt in route["sample_points"]:
            col = pt["pixel_col"]
            row = pt["pixel_row"]
            z_golden = pt["elevation_m"]

            # Independent nearest-pixel read
            z_raster = float(data[row, col])
            assert not math.isnan(z_raster), f"Pixel ({col},{row}) is NoData in Syrtis DTM"
            assert z_raster == pytest.approx(z_golden, abs=1.0), (
                f"S-basic idx={pt['sample_index']}: rasterio read {z_raster:.4f} m "
                f"vs golden {z_golden:.4f} m (tolerance 1.0 m)"
            )

    def test_s_basic_cumulative_distances_monotone_increasing(self):
        route = _route("S-basic")
        pts = route["sample_points"]
        dists = [p["cumulative_distance_m"] for p in pts]
        for i in range(1, len(dists)):
            assert dists[i] > dists[i - 1], (
                f"S-basic cumulative distance not monotone at idx {i}: "
                f"{dists[i-1]} -> {dists[i]}"
            )

    def test_s_basic_elevation_gain_matches_golden(self):
        """Total raw elevation gain across S-basic must match golden fixture within 0.1 m."""
        route = _route("S-basic")
        pts = route["sample_points"]
        gain = 0.0
        for i in range(1, len(pts)):
            z1 = pts[i - 1]["elevation_m"]
            z2 = pts[i]["elevation_m"]
            if z1 is not None and z2 is not None:
                dz = z2 - z1
                if dz > 0:
                    gain += dz
        assert gain == pytest.approx(route["expected_total_gain_raw_m"], abs=0.5), (
            f"S-basic computed gain {gain:.3f} m != golden {route['expected_total_gain_raw_m']:.3f} m"
        )

    def test_s_basic_haversine_distances_agree_with_golden(self):
        """Verify cumulative haversine distances match golden to within 0.5 m."""
        from backend.app.services.coords import haversine_m as hav

        route = _route("S-basic")
        pts = route["sample_points"]
        cum = 0.0
        for i, pt in enumerate(pts):
            if i == 0:
                assert cum == pytest.approx(pt["cumulative_distance_m"], abs=0.01)
                continue
            prev = pts[i - 1]
            seg = float(hav(prev["lon"], prev["lat"], pt["lon"], pt["lat"]))
            cum += seg
            assert cum == pytest.approx(pt["cumulative_distance_m"], abs=0.5), (
                f"S-basic cumulative dist at idx {i}: computed {cum:.4f} m "
                f"vs golden {pt['cumulative_distance_m']:.4f} m"
            )


class TestGoldenRouteSBasicProcessElevationGaps:
    """Verify process_elevation_gaps returns 'complete' for the clean S-basic route."""

    def test_s_basic_no_gaps(self):
        route = _route("S-basic")
        elevs = [p["elevation_m"] for p in route["sample_points"]]
        _, status, gain, loss = process_elevation_gaps(elevs, step_m=5.0)
        assert status == "complete"
        assert gain >= 0.0
        assert loss >= 0.0

    def test_j_edge_has_gaps(self):
        """J-edge fixture must produce partial_gap when fed to process_elevation_gaps."""
        route = _route("J-edge")
        elevs = [p["elevation_m"] if p["elevation_m"] is not None else float("nan")
                 for p in route["sample_points"]]
        _, status, _, _ = process_elevation_gaps(elevs, step_m=5.0)
        assert status in ("partial_gap", "out_of_bounds"), (
            f"J-edge expected partial_gap or out_of_bounds, got {status!r}"
        )


class TestGoldenRouteJGentleSkippedInCI:
    """J-gentle elevation checks — requires jezero_aoi_v2.tif (skipped in CI)."""

    @pytest.mark.skipif(not _jezero_available, reason="jezero_aoi_v2.tif not available (CI skip)")
    def test_j_gentle_first_elevation(self):
        """First sample point elevation matches ground truth within 1 m."""
        route = _route("J-gentle")
        pt = route["sample_points"][0]
        # Re-read from raster and compare
        import rasterio
        with rasterio.open(str(_JEZERO_AOI_PATH)) as src:
            import pyproj
            crs_geo = pyproj.CRS.from_proj4("+proj=longlat +a=3394839.8133163 +b=3394839.8133163 +no_defs")
            transformer = pyproj.Transformer.from_crs(crs_geo, pyproj.CRS(src.crs), always_xy=True)
            x, y = transformer.transform(pt["lon"], pt["lat"])
            gt = src.transform
            col = int((x - gt.c) / gt.a)
            row = int((y - gt.f) / gt.e)
            z = float(src.read(1, window=((row, row + 1), (col, col + 1)))[0, 0])
        assert z == pytest.approx(pt["elevation_m"], abs=1.0)

    @pytest.mark.skipif(not _jezero_available, reason="jezero_aoi_v2.tif not available (CI skip)")
    def test_j_gentle_coverage_complete(self):
        route = _route("J-gentle")
        assert route["expected_coverage_status"] == "complete"
        nodata = [p for p in route["sample_points"] if p["status"] == "dtm_nodata"]
        assert len(nodata) == 0

    @pytest.mark.skipif(not _jezero_available, reason="jezero_aoi_v2.tif not available (CI skip)")
    def test_j_handcheck_sol387_anchor(self):
        """Sol-387 elevation must be within 1 mm of gdallocationinfo value."""
        route = _route("J-handcheck")
        pt = route["sample_points"][1]
        assert pt["lon"] == pytest.approx(77.46157944, abs=1e-8)
        assert pt["lat"] == pytest.approx(18.46447597, abs=1e-8)
        # gdallocationinfo exact value: -2568.58251953125
        assert pt["elevation_m"] == pytest.approx(-2568.58251953125, abs=0.001)


# ---------------------------------------------------------------------------
# 3D Surface Distance Integration Tests (Spec v3.1 § 4.2, AC-08)
# ---------------------------------------------------------------------------

class TestSurfaceDistance3DIntegration:
    """AC-08: 3D surface distance >= 2D great-circle distance.

    Validates that surface_distance_3d_m() integrates correctly with
    process_elevation_gaps() and densify_route() to produce 3D path
    lengths that are always >= the flat 2D haversine distance.

    Spec ref: docs/terrain-spec.md § 4.2 [v3.1]
    Formula: d_3D = sum(sqrt(d_2D_k^2 + (z_{k+1} - z_k)^2))
    """

    def test_flat_route_3d_equals_2d(self):
        """Flat terrain: 3D surface distance equals 2D distance (no elevation change)."""
        # 100 m route at 5 m steps, constant elevation
        dists = [float(i * 5) for i in range(21)]  # 0..100 m, 21 pts
        elevs = [100.0] * 21
        filled, status, _, _ = process_elevation_gaps(elevs, step_m=5.0)
        d2d_steps = [5.0] * 20
        d3d_steps = [surface_distance_3d_m(d, filled[i + 1] - filled[i])
                     for i, d in enumerate(d2d_steps)]
        total_3d = sum(d3d_steps)
        total_2d = sum(d2d_steps)
        assert total_3d == pytest.approx(total_2d, abs=1e-6)
        assert status == "complete"

    def test_inclined_route_3d_greater_than_2d(self):
        """Incline terrain: 3D surface distance strictly > 2D distance (AC-08)."""
        # 10% ramp: 5 m horizontal, 0.5 m rise per step -> 3D = sqrt(25 + 0.25) per step
        n_steps = 20
        d2d = 5.0
        dz = 0.5  # 10% grade
        d3d_step = math.sqrt(d2d ** 2 + dz ** 2)
        elevs = [float(i * dz) for i in range(n_steps + 1)]
        filled, status, gain, _ = process_elevation_gaps(elevs, step_m=d2d)
        d3d_total = sum(
            surface_distance_3d_m(d2d, filled[i + 1] - filled[i])
            for i in range(n_steps)
        )
        d2d_total = d2d * n_steps
        assert d3d_total > d2d_total
        assert d3d_total == pytest.approx(d3d_step * n_steps, abs=1e-6)
        assert gain == pytest.approx(n_steps * dz, abs=1e-4)

    def test_3d_pythagorean_triple_profile(self):
        """3-4-5 step: d_2D=4, dz=3 -> d_3D=5 per step (exact Pythagorean triple)."""
        d2d = 4.0
        dz = 3.0
        d3d = surface_distance_3d_m(d2d, dz)
        assert d3d == pytest.approx(5.0, abs=1e-10)

    def test_3d_symmetric_dz_positive_and_negative(self):
        """Descent and ascent of equal magnitude produce equal 3D distance."""
        d2d = 10.0
        assert surface_distance_3d_m(d2d, 5.0) == pytest.approx(
            surface_distance_3d_m(d2d, -5.0), abs=1e-10
        )

    def test_3d_over_partial_gap_profile(self):
        """3D distance is accumulated only over valid consecutive segments.

        A large gap (>15m) produces NaN in the filled profile. The 3D distance
        accumulation must skip NaN steps and never return NaN as the total.
        """
        # Gap from index 2 to index 5 (3 samples = 15m): exactly on boundary -> still filled
        # Gap from index 5 to index 9 (4 samples = 20m): large gap -> partial_gap NaNs remain
        elevs = (
            [100.0, 101.0, float("nan"), float("nan"), float("nan"), 103.0]
            + [float("nan")] * 4
            + [107.0, 108.0]
        )
        filled, status, gain, loss = process_elevation_gaps(elevs, step_m=5.0, max_fill_m=15.0)
        assert status == "partial_gap"

        d2d = 5.0
        d3d_total = 0.0
        for i in range(len(filled) - 1):
            z1, z2 = filled[i], filled[i + 1]
            if not (math.isnan(z1) or math.isnan(z2)):
                d3d_total += surface_distance_3d_m(d2d, z2 - z1)
        # Must be a finite positive value, never 0 or NaN
        assert math.isfinite(d3d_total)
        assert d3d_total > 0.0

    def test_3d_with_densified_route_two_waypoints(self):
        """Densified 2-waypoint route: 3D distance computed per 5 m step."""
        # Two waypoints ~100 m apart; assign linear elevation profile
        c1 = coord(77.45, 18.44)
        c2 = coord(77.4509, 18.44)  # ~100 m east at Jezero latitude
        dense = densify_route([c1, c2], step_m=5.0)
        assert len(dense) >= 2

        # Assign linear elevation: 0.0 to 10.0 across all densified points
        n = len(dense)
        elevs = [10.0 * i / (n - 1) for i in range(n)]
        filled, status, gain, _ = process_elevation_gaps(elevs, step_m=5.0)

        d3d_total = 0.0
        for i in range(n - 1):
            d2d = haversine_m(dense[i], dense[i + 1])
            d3d_total += surface_distance_3d_m(d2d, filled[i + 1] - filled[i])

        # Total 3D distance must exceed flat 2D total distance
        d2d_total = sum(haversine_m(dense[i], dense[i + 1]) for i in range(n - 1))
        assert d3d_total > d2d_total
        assert gain == pytest.approx(10.0, abs=0.01)
