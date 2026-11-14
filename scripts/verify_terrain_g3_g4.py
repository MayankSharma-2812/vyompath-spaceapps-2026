#!/usr/bin/env python3
"""Offline Terrain Service Verification Harness for Gates G3 & G4.

Executes complete pre-event mathematical, fixture, and concurrency validation
with zero network dependencies. Designed for tabletop dry runs (Nov 8 / G3)
and offline bundle verification (Nov 11-13 / G4).

Usage:
    python3 scripts/verify_terrain_g3_g4.py

Author: Pranav Sharma (@PranavSharma124), Terrain Service Lead
Team NAKSHATRA X | NASA Space Apps Challenge 2026
"""

from __future__ import annotations

import concurrent.futures
import json
import math
import sys
import time
from pathlib import Path

import numpy as np

# Ensure repository root is on sys.path
_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT))

from backend.app.schemas import Coordinate
from backend.app.services.coords import (
    MARS_RADIUS_M,
    cross_along_m,
    haversine_m,
    local_xy_m,
    surface_distance_3d_m,
)
from backend.app.services.terrain import (
    along_track_grades,
    densify_route,
    ground_spacing_m,
    lttb_downsample,
    multi_scale_along_track_grades,
    normalize_longitude,
    process_elevation_gaps,
)

# Robust Windows console output (UTF-8 auto-reconfigure or fallback for cp1252 / cp437)
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def _safe_print(text: str) -> None:
    try:
        print(text)
    except UnicodeEncodeError:
        clean = (
            text.replace("✔", "[PASS]")
            .replace("✘", "[FAIL]")
            .replace("°", " deg")
            .replace("§", "Sec ")
            .replace("—", "-")
        )
        try:
            print(clean)
        except UnicodeEncodeError:
            print(clean.encode("ascii", errors="replace").decode("ascii"))


def log(msg: str) -> None:
    _safe_print(f"[VERIFY] {msg}")


def log_pass(name: str) -> None:
    _safe_print(f"  \033[92m✔ PASS\033[0m: {name}")


def log_fail(name: str, reason: str) -> None:
    _safe_print(f"  \033[91m✘ FAIL\033[0m: {name} — {reason}")


def verify_fixtures_exist() -> bool:
    log("Checking golden fixtures integrity...")
    fixtures = [
        "tests/fixtures/golden_routes.json",
        "tests/fixtures/golden_pois.json",
        "tests/fixtures/tile_indices.json",
        "tests/fixtures/unit_test_anchors.json",
    ]
    all_ok = True
    for fix_rel in fixtures:
        p = _REPO_ROOT / fix_rel
        if p.exists() and p.stat().st_size > 0:
            with open(p) as f:
                json.load(f)
            log_pass(f"{fix_rel} ({p.stat().st_size} bytes)")
        else:
            log_fail(fix_rel, "File missing or empty")
            all_ok = False
    return all_ok


def verify_3d_surface_distance() -> bool:
    log("Verifying 3D surface distance mathematics (Spec v3.1 § 4.2)...")
    all_ok = True

    # 1. Flat terrain 3D == 2D
    d2d = 100.0
    d3d_flat = surface_distance_3d_m(d2d, 0.0)
    if abs(d3d_flat - d2d) < 1e-9:
        log_pass("Flat terrain: d_3D == d_2D (100.0 m == 100.0 m)")
    else:
        log_fail("Flat terrain", f"d_3D={d3d_flat} != d_2D={d2d}")
        all_ok = False

    # 2. Incline 3D > 2D
    d3d_inc = surface_distance_3d_m(d2d, 10.0)
    if d3d_inc > d2d and abs(d3d_inc - math.sqrt(100**2 + 10**2)) < 1e-9:
        log_pass(f"Incline terrain: d_3D ({d3d_inc:.3f} m) > d_2D ({d2d:.3f} m)")
    else:
        log_fail("Incline terrain", f"d_3D={d3d_inc} not matching sqrt(d2d^2 + dz^2)")
        all_ok = False

    # 3. Pythagorean triple: 4 m horiz, 3 m vert -> 5 m
    d3d_pyth = surface_distance_3d_m(4.0, 3.0)
    if abs(d3d_pyth - 5.0) < 1e-9:
        log_pass("Pythagorean triple step (4 m horiz, 3 m vert = 5.000 m)")
    else:
        log_fail("Pythagorean triple", f"Expected 5.0, got {d3d_pyth}")
        all_ok = False

    return all_ok


def verify_golden_routes() -> bool:
    log("Verifying golden route fixtures (Spec v3.1 § 4 & § 6)...")
    golden_path = _REPO_ROOT / "tests/fixtures/golden_routes.json"
    with open(golden_path) as f:
        data = json.load(f)

    all_ok = True
    routes_map = {r["route_id"]: r for r in data["routes"]}
    expected_ids = ["J-gentle", "J-steep", "J-edge", "S-basic", "J-handcheck"]

    for r_id in expected_ids:
        if r_id in routes_map:
            r = routes_map[r_id]
            pts = r["sample_points"]
            log_pass(f"Route '{r_id}': {len(pts)} points, coverage={r['expected_coverage_status']}")
        else:
            log_fail(f"Route '{r_id}'", "Missing from golden_routes.json")
            all_ok = False

    # Verify scarp route peaks at 4.09° ~ 4.1° at 50 m baseline window
    scarp_fixture = _REPO_ROOT / "tests/fixtures/demo_route_scarp_5m.json"
    if scarp_fixture.exists():
        with open(scarp_fixture) as f:
            scarp_data = json.load(f)
        pts = scarp_data["sample_points"]
        dists = [p["cumulative_distance_m"] for p in pts]
        elevs = [p["elevation_m"] for p in pts]
        res = multi_scale_along_track_grades(dists, elevs, windows_m=[20.0, 50.0, 100.0])
        g50 = res["by_window"][50.0]["max_grade_deg"]
        g20 = res["by_window"][20.0]["max_grade_deg"]
        if abs(g50 - 4.09) < 0.1 and g50 < 4.5:
            log_pass(f"Scarp traverse (J-steep) peaks at {g50:.2f}° at 50m (gentle slope < 5°); 20m peaks at {g20:.2f}°")
        else:
            log_fail("Scarp grade check", f"Expected ~4.09°, got {g50}°")
            all_ok = False

    return all_ok


def verify_golden_poi_corridors() -> bool:
    log("Verifying science POI corridor buffer math (Tolerance <= 1.0 m)...")
    golden_pois_path = _REPO_ROOT / "tests/fixtures/golden_pois.json"
    with open(golden_pois_path) as f:
        data = json.load(f)

    all_ok = True
    for ct in data["corridor_tests"]:
        fix_path = _REPO_ROOT / ct["route_fixture_path"]
        if not fix_path.exists():
            log_fail(ct["test_id"], f"Fixture {fix_path} not found")
            all_ok = False
            continue

        with open(fix_path) as f:
            route_data = json.load(f)

        pts = [(p["coordinates"][0], p["coordinates"][1]) for p in route_data["sample_points"]]
        lon0, lat0 = pts[0]
        route_xy = np.array([local_xy_m(lon, lat, lon0, lat0) for lon, lat in pts])

        for ep in ct["expected_pois"]:
            # Lookup POI coordinates from MMGIS anchor
            if ep["id"] == "POI-M20-SOL-386":
                p_geo = (77.46313311, 18.4607914)
            elif ep["id"] == "POI-M20-SOL-387":
                p_geo = (77.46157944, 18.46447597)
            else:
                continue

            p_xy = np.array(local_xy_m(p_geo[0], p_geo[1], lon0, lat0))
            cross, along = cross_along_m(route_xy, p_xy)
            err_c = abs(cross - ep["cross_track_m"])
            err_a = abs(along - ep["along_route_m"])

            if err_c <= 1.0 and err_a <= 1.0:
                log_pass(f"Corridor {ct['test_id']} -> {ep['id']}: cross error={err_c*1000:.1f}mm, along error={err_a*1000:.1f}mm")
            else:
                log_fail(f"Corridor {ct['test_id']} -> {ep['id']}", f"cross err={err_c:.3f}m, along err={err_a:.3f}m (>1.0m)")
                all_ok = False

    return all_ok


def verify_concurrency() -> bool:
    log("Verifying 20-worker parallel read concurrency (Spec v3.1 § 5.5)...")
    num_workers = 20
    runs_per_worker = 20

    def worker_job(worker_id: int):
        coords = [
            Coordinate(lon=77.45 + worker_id * 0.0001, lat=18.44),
            Coordinate(lon=77.455 + worker_id * 0.0001, lat=18.445),
        ]
        dense = densify_route(coords, step_m=5.0)
        n = len(dense)
        elevs = [float(100.0 + (i % 10) * 1.5) for i in range(n)]
        filled, status, gain, loss = process_elevation_gaps(elevs, step_m=5.0)
        dists = [float(i * 5.0) for i in range(n)]
        grades = multi_scale_along_track_grades(dists, filled, windows_m=[20.0, 50.0, 100.0])
        lttb = lttb_downsample(list(zip(dists, filled)), threshold=50)
        d3d = sum(surface_distance_3d_m(5.0, filled[i + 1] - filled[i]) for i in range(n - 1))
        return {
            "worker_id": worker_id,
            "status": status,
            "dense_count": n,
            "gain": gain,
            "d3d": d3d,
            "lttb_count": len(lttb),
        }

    t0 = time.perf_counter()
    with concurrent.futures.ThreadPoolExecutor(max_workers=num_workers) as executor:
        futures = [
            executor.submit(worker_job, i % num_workers)
            for i in range(num_workers * runs_per_worker)
        ]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]
    elapsed = time.perf_counter() - t0

    if len(results) == num_workers * runs_per_worker and all(r["status"] == "complete" for r in results):
        log_pass(f"Executed {len(results)} full pipeline runs across {num_workers} threads in {elapsed:.3f}s (0 deadlocks)")
        return True
    else:
        log_fail("Concurrency stress test", "Jobs failed or dropped")
        return False


def verify_tile_indices() -> bool:
    log("Verifying MARS:2000 tile grid indices at golden anchor (Spec v3.1 § 5.4)...")
    # Mars 2000 sphere R = 3396190 m
    # Test point: Perseverance landing site (77.45, 18.44) at z=15
    # Formula:
    #   HX = pi * R
    #   RES0 = 2 * HX / 512 = 41677.52169567
    #   t = 256 * RES0 / 2**z
    #   x = int((lon_rad * R + HX) // t)
    #   y = int((HY - lat_rad * R) // t)
    HX = math.pi * MARS_RADIUS_M
    HY = HX / 2.0
    RES0 = 2.0 * HX / 512.0
    z = 15
    t = 256.0 * RES0 / (2.0 ** z)
    X = math.radians(77.45) * MARS_RADIUS_M
    Y = math.radians(18.44) * MARS_RADIUS_M
    tile_x = int((X + HX) // t)
    tile_y = int((HY - Y) // t)

    if tile_x == 46867 and tile_y == 13027:
        log_pass(f"Perseverance anchor (77.45°E, 18.44°N, z=15) -> ({z}, {tile_x}, {tile_y}) exact match")
        return True
    else:
        log_fail("Tile index check", f"Expected (15, 46867, 13027), got ({z}, {tile_x}, {tile_y})")
        return False


def main() -> int:
    print("=" * 72)
    print(" VYOMPATH TERRAIN SERVICE TABLETOP & OFFLINE VERIFICATION (G3/G4)")
    print(" Team NAKSHATRA X | NASA Space Apps Challenge 2026")
    print("=" * 72)

    checks = [
        ("Golden Fixtures Integrity", verify_fixtures_exist),
        ("3D Surface Distance Engine", verify_3d_surface_distance),
        ("Golden Route Traverses & Scarp Grade", verify_golden_routes),
        ("Science POI Corridor Cross-Validation", verify_golden_poi_corridors),
        ("20-Worker Concurrency Stress Test", verify_concurrency),
        ("MARS:2000 Tile Grid Index Alignment", verify_tile_indices),
    ]

    all_passed = True
    for name, check_func in checks:
        print()
        if not check_func():
            all_passed = False

    print("\n" + "=" * 72)
    if all_passed:
        print(" \033[92mALL 6 PRE-EVENT ENGINEERING CHECKS PASSED (ZERO NETWORK REQUIRED)\033[0m")
        print(" Gate G3 Tabletop Dry Run & Nov 11 Fixture Freeze Ready.")
        print("=" * 72)
        return 0
    else:
        print(" \033[91mONE OR MORE CHECKS FAILED. INVESTIGATE ERRORS ABOVE.\033[0m")
        print("=" * 72)
        return 1


if __name__ == "__main__":
    sys.exit(main())
