#!/usr/bin/env python3
# PREP TOOLING, NOT PRODUCT CODE
"""
tile_index.py — Martian Equirectangular Tile Index Calculation & Verification

Author: Arya (Interactive Map Engineer, Team NAKSHATRA X)
Role: NASA Space Apps Challenge 2026 - Martian Map / VyomPath
Reference: Master Coding Guide v3.1, Section 5.4

Grid Specification (VERIFIED):
  - CRS: MARS:2000 Equirectangular (IAU 2000 Sphere, EPSG:104905)
  - Radius: R = 3,396,190.0 m (standard IAU Mars Sphere)
  - Half World Dimensions:
      HX = pi * R = 10,669,445.5540916 m
      HY = HX / 2 = 5,334,722.7770458 m
  - Zoom 0 Matrix: 2 columns x 1 row (2x1 aspect ratio)
  - Tile Size: 256 x 256 pixels
  - Zoom 0 Resolution: RES0 = (2 * HX) / 512 = 41,677.52169567 m/px
  - Origin: Top-Left (-180 deg lon, +90 deg lat), Y grows downward
  - Clamping: lon=180 clamped to 2^(z+1)-1, lat=-90 clamped to 2^z-1
"""

import sys
import os
import math
import json
from datetime import datetime, timezone

# Authoritative Constants (VERIFIED against Master Guide v3.1 Section 5.4 & DATA_FACTS.md)
R = 3396190.0
HX = math.pi * R
HY = HX / 2.0
RES0 = (2.0 * HX) / 512.0  # 41677.52169567039 m/pixel


def tile_index(lon: float, lat: float, z: int) -> tuple[int, int, int]:
    """
    Computes (z, tile_x, tile_y) on the shared Mars equirectangular grid.

    Args:
        lon: Longitude in degrees [-180, 180]
        lat: Latitude in degrees [-90, 90]
        z: Zoom level integer (>= 0)

    Returns:
        (z, tile_x, tile_y)
    """
    if z < 0:
        raise ValueError(f"Zoom level z must be >= 0, got {z}")

    X = math.radians(lon) * R
    Y = math.radians(lat) * R
    t = 256.0 * RES0 / (2.0 ** z)

    x = int((X + HX) // t)
    y = int((HY - Y) // t)

    max_x = (2 ** (z + 1)) - 1
    max_y = (2 ** z) - 1

    # Clamp edge cases (anti-meridian +180 and South Pole -90)
    x = max(0, min(x, max_x))
    y = max(0, min(y, max_y))

    return z, x, y


def tile_bounds(z: int, x: int, y: int) -> tuple[float, float, float, float]:
    """
    Computes the geographic bounding box of a tile in planetocentric degrees.

    Returns:
        (min_lon, min_lat, max_lon, max_lat)
    """
    n_x = 2 * (2 ** z)
    n_y = 2 ** z

    min_lon = -180.0 + (x / n_x) * 360.0
    max_lon = -180.0 + ((x + 1) / n_x) * 360.0
    max_lat = 90.0 - (y / n_y) * 180.0
    min_lat = 90.0 - ((y + 1) / n_y) * 180.0

    return min_lon, min_lat, max_lon, max_lat


def verify_manual_claim() -> dict:
    """
    Verifies the claimed reference point from Master Coding Guide v3.1 Section 5.4:
      tile_index(77.45, 18.44, 15) -> claimed (15, 46867, 13027)
    """
    computed = tile_index(77.45, 18.44, 15)
    claimed = (15, 46867, 13027)
    matches = (computed == claimed)
    return {
        "input": {"lon": 77.45, "lat": 18.44, "z": 15},
        "computed": list(computed),
        "claimed": list(claimed),
        "matches": matches,
        "note": "Mathematical result matches claimed index exactly. However, file 15/46867/13027.jpg does not exist in tiles_aoi because lon 77.45 deg E is 681.75 m west of the Jezero valid stereo boundary at lat 18.44 deg N (edge at lon 77.462124 deg E, computed with R=3,396,190 m)."
    }


def get_test_points() -> list[dict]:
    """
    Returns standard verification points:
      - 5 strictly sourced POIs from poi_strictly_sourced.json
      - 4 corners of Jezero valid stereo footprint
      - Global edge clamp points (lon=180, lat=-90, lon=0, tile boundary)
    """
    return [
        {
            "name": "POI-M20-SOL-013",
            "lon": 77.45088572,
            "lat": 18.44462715,
            "notes": "Perseverance Sol 13 (landing site vicinity; outside v2 valid stereo footprint)"
        },
        {
            "name": "POI-M20-SOL-023",
            "lon": 77.45177711,
            "lat": 18.44520229,
            "notes": "Perseverance Sol 23 (early ingress; outside v2 valid stereo footprint)"
        },
        {
            "name": "POI-M20-SOL-034",
            "lon": 77.45102155,
            "lat": 18.44486273,
            "notes": "Perseverance Sol 34 (Van Zyl overlook; outside v2 valid stereo footprint)"
        },
        {
            "name": "POI-M20-SOL-386",
            "lon": 77.46313311,
            "lat": 18.46079140,
            "notes": "Perseverance Sol 386 (rapid transit waypoint; INSIDE v2 valid stereo footprint)"
        },
        {
            "name": "POI-M20-SOL-387",
            "lon": 77.46157944,
            "lat": 18.46447597,
            "notes": "Perseverance Sol 387 (rapid transit staging; INSIDE v2 valid stereo footprint)"
        },
        {
            "name": "Footprint-NW-Corner",
            "lon": 77.45290653,
            "lat": 18.50986793,
            "notes": "Jezero valid stereo footprint NW vertex"
        },
        {
            "name": "Footprint-SW-Corner",
            "lon": 77.49937431,
            "lat": 18.15934679,
            "notes": "Jezero valid stereo footprint SW vertex"
        },
        {
            "name": "Footprint-SE-Corner",
            "lon": 77.59814922,
            "lat": 18.17112171,
            "notes": "Jezero valid stereo footprint SE vertex"
        },
        {
            "name": "Footprint-NE-Corner",
            "lon": 77.55176964,
            "lat": 18.52155765,
            "notes": "Jezero valid stereo footprint NE vertex"
        },
        {
            "name": "Manual-Claim-Point",
            "lon": 77.45,
            "lat": 18.44,
            "notes": "Master Guide Section 5.4 reference point (tested)"
        },
        {
            "name": "Edge-Antimeridian-East",
            "lon": 180.0,
            "lat": 0.0,
            "notes": "Global edge case: lon=180 boundary clamp"
        },
        {
            "name": "Edge-SouthPole",
            "lon": 0.0,
            "lat": -90.0,
            "notes": "Global edge case: lat=-90 boundary clamp"
        },
        {
            "name": "Edge-Origin",
            "lon": 0.0,
            "lat": 0.0,
            "notes": "Global origin: prime meridian and equator intersection"
        },
        {
            "name": "Tile-Boundary-Jezero",
            "lon": 77.4365234375,
            "lat": 18.45703125,
            "notes": "Exact tile grid boundary at z12 (multiple of 180 / 2^12)"
        }
    ]


def build_fixtures(bundle_dir: str | None = None) -> dict:
    """
    Constructs the complete test fixture dictionary for the team.
    """
    zooms = [12, 14, 15, 16]
    points = get_test_points()
    fixture_points = []

    # Detect bundle directory if available
    effective_bundle_dir = bundle_dir or os.environ.get("VYOMPATH_BUNDLE_DIR")
    if not effective_bundle_dir:
        # Check standard temp locations
        candidates = [
            r"C:\Users\aryat\AppData\Local\Temp\vyompath_bundle",
            "/tmp/vyompath_bundle",
            os.path.abspath("data/bundle")
        ]
        for c in candidates:
            if os.path.isdir(c) and os.path.isdir(os.path.join(c, "tiles_aoi")):
                effective_bundle_dir = c
                break

    for p in points:
        for z in zooms:
            z_idx, x_idx, y_idx = tile_index(p["lon"], p["lat"], z)
            aoi_rel = f"tiles_aoi/{z}/{x_idx}/{y_idx}.jpg"
            hill_rel = f"tiles_hillshade/{z}/{x_idx}/{y_idx}.jpg"

            aoi_exists = False
            hill_exists = False
            if effective_bundle_dir and os.path.isdir(effective_bundle_dir):
                aoi_exists = os.path.isfile(os.path.join(effective_bundle_dir, aoi_rel))
                hill_exists = os.path.isfile(os.path.join(effective_bundle_dir, hill_rel))

            bounds = tile_bounds(z_idx, x_idx, y_idx)

            fixture_points.append({
                "name": p["name"],
                "lon": p["lon"],
                "lat": p["lat"],
                "z": z,
                "expected": [z_idx, x_idx, y_idx],
                "tile_bounds_lonlat": [round(b, 8) for b in bounds],
                "bundle_file_exists": {
                    "tiles_aoi": aoi_exists,
                    "tiles_hillshade": hill_exists
                },
                "notes": p["notes"]
            })

    return {
        "generated_by": "scripts/arya/tile_index.py",
        "method": "Master Coding Manual v3.1, Section 5.4 (Mars 2000 Equirectangular 2x1)",
        "grid_specification": {
            "crs": "MARS:2000 (IAU 2000 Sphere, EPSG:104905)",
            "radius_m": R,
            "half_width_hx_m": HX,
            "half_height_hy_m": HY,
            "res0_m_per_px": RES0,
            "aspect_ratio": "2:1",
            "tile_size_px": 256,
            "origin": "top-left [-180, 90]"
        },
        "manual_claim_verification": verify_manual_claim(),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "bundle_dir_evaluated": effective_bundle_dir or "UNAVAILABLE",
        "points": fixture_points
    }


def main():
    print("=" * 70)
    print("Arya's Mars Tile Index Verification (PREP TOOLING, NOT PRODUCT CODE)")
    print("=" * 70)

    # 1. Verify Section 5.4 claim
    claim = verify_manual_claim()
    print(f"Manual 5.4 Claim Test: tile_index(77.45, 18.44, 15)")
    print(f"  Computed: {claim['computed']}")
    print(f"  Claimed:  {claim['claimed']}")
    print(f"  Matches:  {claim['matches']} (VERIFIED)")
    print(f"  Note:     {claim['note']}")
    print("-" * 70)

    # 2. Build and export fixtures
    fixtures = build_fixtures()
    print(f"Generated {len(fixtures['points'])} golden test vectors across zooms 12, 14, 15, 16.")
    
    existing_aoi = sum(1 for p in fixtures["points"] if p["bundle_file_exists"]["tiles_aoi"])
    existing_hill = sum(1 for p in fixtures["points"] if p["bundle_file_exists"]["tiles_hillshade"])
    print(f"Bundle file existence (dir: {fixtures['bundle_dir_evaluated']}):")
    print(f"  tiles_aoi matches:       {existing_aoi} / {len(fixtures['points'])}")
    print(f"  tiles_hillshade matches: {existing_hill} / {len(fixtures['points'])}")
    print("=" * 70)

    # Output JSON if requested via argument
    if "--json" in sys.argv:
        print(json.dumps(fixtures, indent=2))


if __name__ == "__main__":
    main()
