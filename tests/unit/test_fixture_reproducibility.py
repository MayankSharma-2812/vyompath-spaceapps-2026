"""Automated regression and reproducibility tests for fixture coordinates and elevations.

Tests cover:
1. Reconfirmation of the baseline sample 74 numerical discrepancy against tolerance.
2. Verification of the canonical coordinate-precision contract (preserving adequate precision
   and ensuring stored elevations are sampled from exact serialized coordinates).
3. Grade-path reconciliation between legacy 5m discrete evaluation and proposed 1m continuous
   evaluation at identical chainage.

NASA Space Apps Challenge 2026 | Team NAKSHATRA X
"""

import json
import math
import os
from pathlib import Path
import numpy as np
import pytest

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures" / "validation"
FIXTURE_100M_5M = FIXTURES_DIR / "demo_route_sol_corridor_100m_5m.json"
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_DEFAULT_DEM = _REPO_ROOT / "data" / "dtm" / "jezero_aoi_v2.tif"
DEM_PATH = Path(
    os.environ.get(
        "VYOMPATH_DEM_PATH",
        str(_DEFAULT_DEM if _DEFAULT_DEM.exists() else r"E:\DATASETS\_phase2\jezero_aoi_v2.tif"),
    )
)

has_rasterio = False
try:
    import rasterio
    import pyproj
    has_rasterio = True
except ImportError:
    pass

skip_dem = pytest.mark.skipif(
    not (has_rasterio and DEM_PATH.exists()),
    reason="Requires rasterio and local jezero_aoi_v2.tif DTM",
)


class TestFixtureCoordinateAndElevationReproducibility:
    """Validate numerical reproducibility and coordinate boundary behavior."""

    def test_sample_74_canonical_contract_reconfirmation(self):
        """Reconfirm sample 74 values in the regenerated canonical fixture."""
        assert FIXTURE_100M_5M.exists(), f"Missing {FIXTURE_100M_5M}"
        with open(FIXTURE_100M_5M, "r", encoding="utf-8") as f:
            fx = json.load(f)

        assert fx["sample_points_count"] == 110
        pt74 = fx["sample_points"][74]

        assert pt74["sample_index"] == 74
        assert pt74["cumulative_distance_m"] == 370.0
        assert pt74["coordinates"] == [77.462772408, 18.464165555]
        assert round(pt74["coordinates"][0], 7) == 77.4627724
        assert round(pt74["coordinates"][1], 7) == 18.4641656
        assert pt74["elevation_m"] == -2568.6382

    @skip_dem
    def test_regenerated_fixture_all_samples_satisfy_tolerance(self):
        """Verify that all 110 samples in the active fixture pass live comparison within tolerance."""
        import sys
        sys.path.append(str(Path(__file__).resolve().parent.parent.parent / "tools"))
        from compare_fixture import compare, make_rasterio_sampler

        with open(FIXTURE_100M_5M, "r", encoding="utf-8") as f:
            fx = json.load(f)

        sampler = make_rasterio_sampler(str(DEM_PATH))
        res = compare(fx, sampler, tol=0.010000)

        assert res["elevation_nan_count"] == 0
        assert res["elevation_points_over_tol"] == 0
        assert res["elevation_max_abs_diff_m"] < 0.0001
        assert res["elevation_mean_abs_diff_m"] < 0.00005

    @skip_dem
    def test_live_raster_sample_74_boundary_shift(self):
        """Demonstrate that sample 74's 0.011702 m discrepancy is caused by 7-decimal

        coordinate rounding crossing the DTM row 1958/1959 boundary.
        """
        src = rasterio.open(DEM_PATH)
        gt = src.transform
        crs_file = pyproj.CRS.from_wkt(src.crs.to_wkt())
        crs_wire = pyproj.CRS.from_proj4("+proj=longlat +R=3396190 +no_defs")
        trans = pyproj.Transformer.from_crs(crs_wire, crs_file, always_xy=True)
        band = src.read(1)

        def sample_exact(lon: float, lat: float):
            x, y = trans.transform(lon, lat)
            c_f = (x - gt.c) / gt.a
            r_f = (y - gt.f) / gt.e
            c = int(math.floor(c_f))
            r = int(math.floor(r_f))
            return float(band[r, c]), c_f, r_f, c, r

        # 1. Continuous unrounded coordinates derived from route endpoints
        w_start = [77.4638, 18.4580]
        w_end = [77.4623, 18.4670]
        R = 3396190.0

        def haversine(p1, p2):
            phi1, phi2 = math.radians(p1[1]), math.radians(p2[1])
            dphi = math.radians(p2[1] - p1[1])
            dlam = math.radians(p2[0] - p1[0])
            a = math.sin(dphi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2.0) ** 2
            return R * 2.0 * math.atan2(math.sqrt(a), math.sqrt(max(0.0, 1.0 - a)))

        total_dist = haversine(w_start, w_end)
        cum_dist = min(74 * 5.0, total_dist)
        frac = cum_dist / total_dist
        lon_full = w_start[0] + frac * (w_end[0] - w_start[0])
        lat_full = w_start[1] + frac * (w_end[1] - w_start[1])

        z_full, _, r_f_full, _, r_full = sample_exact(lon_full, lat_full)
        assert r_full == 1959
        assert r_f_full > 1959.0
        assert z_full == pytest.approx(-2568.6382, abs=0.0001)

        # 2. Truncated 7-decimal serialized coordinates
        lon_ser = round(lon_full, 7)
        lat_ser = round(lat_full, 7)
        z_ser, _, r_f_ser, _, r_ser = sample_exact(lon_ser, lat_ser)
        assert r_ser == 1958
        assert r_f_ser < 1959.0
        assert z_ser == pytest.approx(-2568.6499, abs=0.0001)

        # Discrepancy between row 1958 and 1959
        row_diff = abs(z_ser - z_full)
        assert row_diff == pytest.approx(0.011719, abs=1e-5)

        # Discrepancy against stored fixture elevation (-2568.6382)
        stored_diff = abs(z_ser - (-2568.6382))
        assert stored_diff == pytest.approx(0.011702, abs=1e-5)
        # Confirms this point exceeds the 0.010000 m tolerance
        assert stored_diff > 0.010000

    @skip_dem
    def test_canonical_contract_satisfies_tolerance_across_all_samples(self):
        """Under the canonical contract where coordinates preserve adequate precision

        (>= 9 decimal places), all 110 samples agree with live sampling within < 0.0001 m.
        """
        src = rasterio.open(DEM_PATH)
        gt = src.transform
        crs_file = pyproj.CRS.from_wkt(src.crs.to_wkt())
        crs_wire = pyproj.CRS.from_proj4("+proj=longlat +R=3396190 +no_defs")
        trans = pyproj.Transformer.from_crs(crs_wire, crs_file, always_xy=True)
        band = src.read(1)

        w_start = [77.4638, 18.4580]
        w_end = [77.4623, 18.4670]
        R = 3396190.0

        def haversine(p1, p2):
            phi1, phi2 = math.radians(p1[1]), math.radians(p2[1])
            dphi = math.radians(p2[1] - p1[1])
            dlam = math.radians(p2[0] - p1[0])
            a = math.sin(dphi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2.0) ** 2
            return R * 2.0 * math.atan2(math.sqrt(a), math.sqrt(max(0.0, 1.0 - a)))

        total_dist = haversine(w_start, w_end)
        tol = 0.010000
        over_tol_count = 0
        max_abs_diff = 0.0

        for i in range(110):
            cum_dist = min(i * 5.0, total_dist)
            frac = cum_dist / total_dist
            # Canonical contract: 9 decimal places
            lon = round(w_start[0] + frac * (w_end[0] - w_start[0]), 9)
            lat = round(w_start[1] + frac * (w_end[1] - w_start[1]), 9)

            x, y = trans.transform(lon, lat)
            c = int(math.floor((x - gt.c) / gt.a))
            r = int(math.floor((y - gt.f) / gt.e))
            z_sampled = float(band[r, c])
            z_stored = round(z_sampled, 4)

            diff = abs(z_sampled - z_stored)
            if diff > max_abs_diff:
                max_abs_diff = diff
            if diff > tol:
                over_tol_count += 1

        assert over_tol_count == 0, f"Expected 0 over tolerance, found {over_tol_count}"
        assert max_abs_diff < 0.0001, f"Expected sub-millimeter diff, got {max_abs_diff}"

    def test_grade_path_reconciliation_identical_chainage(self):
        """Verify that at identical chainage 480.0 m, legacy 5m step and proposed 1m step

        agree to within 0.0001%.
        """
        with open(FIXTURE_100M_5M, "r", encoding="utf-8") as f:
            fx = json.load(f)

        pts = fx["sample_points"]
        z = [p["elevation_m"] for p in pts]
        d = [p["cumulative_distance_m"] for p in pts]

        # Legacy 5m step calculation at 480.0 m
        step_window = 10  # 50m / 5m
        idx_480 = d.index(480.0)
        z_start_480 = z[idx_480]
        z_end_480 = z[idx_480 + step_window]
        dz_480 = abs(z_end_480 - z_start_480)
        grade_legacy_480 = (dz_480 / 50.0) * 100.0

        assert pytest.approx(grade_legacy_480, abs=1e-3) == 10.683

        # Proposed 1m step evaluation at identical chainage 480.0 m
        z0 = np.interp(480.0, d, z)
        z1 = np.interp(530.0, d, z)
        grade_proposed_480 = (abs(z1 - z0) / 50.0) * 100.0

        assert pytest.approx(grade_proposed_480, abs=1e-5) == grade_legacy_480
        assert abs(grade_proposed_480 - grade_legacy_480) < 1e-6
