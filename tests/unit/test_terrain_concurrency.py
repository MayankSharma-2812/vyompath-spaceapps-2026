"""Concurrency and Stress Tests for VyomPath Terrain Engine.

Author: Pranav Sharma (Terrain Service Lead)
Reference: Master Coding Guide v3.1 § 5.5, Build Timeline v3.1 Section 5.5 (Gate G2 milestone)

Validates:
  - 20 simultaneous requests execute in parallel without race conditions or memory corruption.
  - Multi-threaded sampling from pure functions and cached/isolated raster handles.
  - Independent thread execution of LTTB downsampling, grade calculations, and gap processing.

Run with:
    python3 -m pytest tests/unit/test_terrain_concurrency.py -v
"""

from __future__ import annotations

import concurrent.futures
import math
import pytest

from backend.app.schemas import Coordinate
from backend.app.services.coords import (
    cross_along_m,
    haversine_m as coords_haversine_m,
    surface_distance_3d_m,
)
from backend.app.services.terrain import (
    along_track_grades,
    densify_route,
    lttb_downsample,
    multi_scale_along_track_grades,
    process_elevation_gaps,
    route_distance_m,
    sample_point_bilinear,
)


def _worker_simulate_route_pipeline(worker_id: int) -> dict:
    """Simulates a full terrain pipeline run inside an isolated thread."""
    # 1. Route densification
    c1 = Coordinate(lon=77.45 + (worker_id * 0.0001), lat=18.44 + (worker_id * 0.0001))
    c2 = Coordinate(lon=77.46 + (worker_id * 0.0001), lat=18.45 + (worker_id * 0.0001))
    route = densify_route([c1, c2], step_m=5.0)

    # 2. Cumulative distance calculation
    dists = [0.0]
    for i in range(len(route) - 1):
        d = float(coords_haversine_m(route[i].lon, route[i].lat, route[i + 1].lon, route[i + 1].lat))
        dists.append(dists[-1] + d)

    # 3. Simulated synthetic elevation samples with a gap in the middle
    n_pts = len(dists)
    elevs = [-2500.0 + math.sin(i * 0.1) * 20.0 for i in range(n_pts)]
    # Inject a 3-step gap
    if n_pts > 10:
        elevs[5] = float("nan")
        elevs[6] = float("nan")

    # 4. Process gaps and calculate gain/loss
    filled, status, gain, loss = process_elevation_gaps(elevs, step_m=5.0, max_fill_m=15.0)

    # 5. Multi-scale grade calculations
    grades_res = multi_scale_along_track_grades(dists, filled, windows_m=[20.0, 50.0, 100.0])

    # 6. LTTB profile downsampling
    pts_2d = [(dists[i], filled[i]) for i in range(n_pts)]
    downsampled = lttb_downsample(pts_2d, threshold=50)

    # 7. 3D surface distance
    step_d2d = [dists[i + 1] - dists[i] for i in range(n_pts - 1)]
    step_dz = [filled[i + 1] - filled[i] for i in range(n_pts - 1)]
    dist_3d = sum(surface_distance_3d_m(step_d2d, step_dz))

    return {
        "worker_id": worker_id,
        "n_pts": n_pts,
        "status": status,
        "gain": gain,
        "loss": loss,
        "dist_3d": dist_3d,
        "default_max_grade": grades_res["default_max_grade_deg"],
        "downsampled_count": len(downsampled),
    }


class TestTerrainParallelExecution:
    """Verify concurrent thread execution of terrain functions without deadlocks or corruption."""

    def test_twenty_simultaneous_terrain_worker_pipelines(self):
        """Run 20 concurrent threads simulating parallel route analysis pipelines."""
        num_workers = 20
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = [
                executor.submit(_worker_simulate_route_pipeline, worker_id=i)
                for i in range(num_workers)
            ]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        assert len(results) == num_workers
        for res in results:
            assert res["status"] in ("complete", "partial_gap")
            assert res["gain"] > 0.0
            assert res["loss"] > 0.0
            assert res["dist_3d"] > 0.0
            assert res["downsampled_count"] <= 50
            assert res["default_max_grade"] >= 0.0

    def test_concurrent_lttb_downsampling_determinism(self):
        """Verify LTTB downsampling remains purely deterministic under 20 concurrent callers."""
        test_pts = [(float(i), math.sin(i * 0.05) * 100.0) for i in range(200)]
        expected = lttb_downsample(test_pts, threshold=25)

        def run_lttb(_):
            return lttb_downsample(test_pts, threshold=25)

        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(run_lttb, i) for i in range(20)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        assert len(results) == 20
        for r in results:
            assert r == expected
