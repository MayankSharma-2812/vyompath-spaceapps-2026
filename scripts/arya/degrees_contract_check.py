#!/usr/bin/env python3
# PREP TOOLING, NOT PRODUCT CODE
"""
degrees_contract_check.py — Verification of Frontend/Backend Lon-Lat Degrees Contract

Author: Arya (Map & OpenLayers Lead, Team NAKSHATRA X)
Role: NASA Space Apps Challenge 2026 - Martian Map / VyomPath
Reference: Master Coding Manual v3.1 (Sections 5.1 and 5.5)

Purpose:
  1. Verify bidirectional conversion between planetocentric degrees and MARS:2000 metres.
  2. Prove round-trip numerical accuracy (< 1e-9 degrees).
  3. Demonstrate the "metres-as-degrees" trap: passing raw projected metres to the
     backend Coordinate schema (ge=-180, le=360, ge=-90, le=90) fails validation.
  4. Verify Manual 5.1 longitude wrapping: 270 deg -> -90 deg, 180 deg -> -180 deg (seam jump).
  5. Document that OpenLayers ol/sphere helpers (e.g. getLength) are prohibited because
     they assume an Earth radius (6,371,008.8 m); only backend distances (R = 3,396,190 m)
     are authoritative.
"""

import sys
import math
import json
from datetime import datetime, timezone

# Authoritative constant from IAU 2000 Mars Sphere / Master Guide v3.1
R = 3396190.0
TOLERANCE_DEG = 1e-9


def degrees_to_mars2000_meters(lon: float, lat: float) -> tuple[float, float]:
    """
    Forward conversion: planetocentric degrees -> MARS:2000 projected metres.
    CRS: +proj=eqc +lat_ts=0 +lat_0=0 +lon_0=0 +R=3396190 +units=m +no_defs
    """
    x = math.radians(lon) * R
    y = math.radians(lat) * R
    return x, y


def mars2000_meters_to_degrees(x: float, y: float) -> tuple[float, float]:
    """
    Inverse conversion: MARS:2000 projected metres -> planetocentric degrees.
    """
    lon = math.degrees(x / R)
    lat = math.degrees(y / R)
    return lon, lat


def wrap_lon_manual_5_1(v: float) -> float:
    """
    Master Coding Manual v3.1 Section 5.1 validator:
      ((v + 180.0) % 360.0) - 180.0
    Normalizes longitude into [-180.0, 180.0).
    Note seam behavior: +180.0 maps to -180.0.
    """
    return ((v + 180.0) % 360.0) - 180.0


def validate_backend_schema(lon: float, lat: float) -> dict:
    """
    Simulates Pydantic validation from backend/app/schemas.py (Manual 5.1):
      lon: float = Field(..., ge=-180.0, le=360.0)
      lat: float = Field(..., ge=-90.0, le=90.0)
    """
    errors = []
    if lon < -180.0:
        errors.append(f"lon: Input should be greater than or equal to -180 [got {lon}]")
    elif lon > 360.0:
        errors.append(f"lon: Input should be less than or equal to 360 [got {lon}]")

    if lat < -90.0:
        errors.append(f"lat: Input should be greater than or equal to -90 [got {lat}]")
    elif lat > 90.0:
        errors.append(f"lat: Input should be less than or equal to 90 [got {lat}]")

    is_valid = len(errors) == 0
    wrapped_lon = wrap_lon_manual_5_1(lon) if is_valid else None

    return {
        "valid": is_valid,
        "errors": errors,
        "wrapped_lon": wrapped_lon
    }


def get_test_vectors() -> list[dict]:
    """
    Returns required test vectors:
      - Sol 386 & Sol 387
      - Jezero DTM footprint vertices & bounding box corners
      - Global edge cases: lon 0, lon 180, lon -180, lat 0, lat +-90, lon 270
    """
    return [
        {
            "name": "POI Sol 386",
            "lon": 77.46313311,
            "lat": 18.46079140,
            "description": "Perseverance Sol 386 rapid transit waypoint"
        },
        {
            "name": "POI Sol 387",
            "lon": 77.46157944,
            "lat": 18.46447597,
            "description": "Perseverance Sol 387 rapid transit staging waypoint"
        },
        {
            "name": "Footprint NW Vertex",
            "lon": 77.4529065312924,
            "lat": 18.509867934244717,
            "description": "jezero_dtm.geojson Northwest outline vertex"
        },
        {
            "name": "Footprint SW Vertex",
            "lon": 77.49937431082921,
            "lat": 18.159346791095654,
            "description": "jezero_dtm.geojson Southwest outline vertex"
        },
        {
            "name": "Footprint SE Vertex",
            "lon": 77.59814921501544,
            "lat": 18.171121711363813,
            "description": "jezero_dtm.geojson Southeast outline vertex"
        },
        {
            "name": "Footprint NE Vertex",
            "lon": 77.55176964310874,
            "lat": 18.521557652484884,
            "description": "jezero_dtm.geojson Northeast outline vertex"
        },
        {
            "name": "Footprint BBox NW Corner",
            "lon": 77.4529065312924,
            "lat": 18.521557652484884,
            "description": "Jezero DTM bounding box NW corner"
        },
        {
            "name": "Footprint BBox SW Corner",
            "lon": 77.4529065312924,
            "lat": 18.159346791095654,
            "description": "Jezero DTM bounding box SW corner"
        },
        {
            "name": "Footprint BBox SE Corner",
            "lon": 77.59814921501544,
            "lat": 18.159346791095654,
            "description": "Jezero DTM bounding box SE corner"
        },
        {
            "name": "Footprint BBox NE Corner",
            "lon": 77.59814921501544,
            "lat": 18.521557652484884,
            "description": "Jezero DTM bounding box NE corner"
        },
        {
            "name": "Origin (Equator & Prime Meridian)",
            "lon": 0.0,
            "lat": 0.0,
            "description": "Planetary coordinate origin"
        },
        {
            "name": "Antimeridian East (+180)",
            "lon": 180.0,
            "lat": 0.0,
            "description": "Eastern antimeridian edge (+180)"
        },
        {
            "name": "Antimeridian West (-180)",
            "lon": -180.0,
            "lat": 0.0,
            "description": "Western antimeridian edge (-180)"
        },
        {
            "name": "North Pole (+90)",
            "lon": 0.0,
            "lat": 90.0,
            "description": "Planetary North Pole"
        },
        {
            "name": "South Pole (-90)",
            "lon": 0.0,
            "lat": -90.0,
            "description": "Planetary South Pole"
        },
        {
            "name": "0-360 Domain Point (lon 270 equator)",
            "lon": 270.0,
            "lat": 0.0,
            "description": "Positive 0-360 representation of 90 deg West"
        },
        {
            "name": "0-360 Domain Point (lon 270 lat 18.44)",
            "lon": 270.0,
            "lat": 18.44,
            "description": "Jezero latitude with 0-360 longitude domain"
        }
    ]


def run_checks() -> dict:
    vectors = get_test_vectors()
    results = []

    max_err_lon = 0.0
    max_err_lat = 0.0
    worst_vector_name = ""

    for v in vectors:
        lon_in = v["lon"]
        lat_in = v["lat"]

        # 1. Forward conversion: degrees -> metres
        x_m, y_m = degrees_to_mars2000_meters(lon_in, lat_in)

        # 2. Inverse conversion: metres -> degrees
        lon_rt, lat_rt = mars2000_meters_to_degrees(x_m, y_m)

        err_lon = abs(lon_rt - lon_in)
        err_lat = abs(lat_rt - lat_in)

        if err_lon > max_err_lon or err_lat > max_err_lat:
            max_err_lon = max(max_err_lon, err_lon)
            max_err_lat = max(max_err_lat, err_lat)
            worst_vector_name = v["name"]

        # 3. Validation when sent properly as degrees
        degrees_validation = validate_backend_schema(lon_in, lat_in)

        # 4. TRAP DEMONSTRATION: what happens if raw metres (x_m, y_m) are sent directly as degrees?
        metres_as_degrees_validation = validate_backend_schema(x_m, y_m)

        # 5. Longitude wrap analysis
        wrapped_lon = wrap_lon_manual_5_1(lon_in)

        results.append({
            "name": v["name"],
            "description": v["description"],
            "input_degrees": {
                "lon": round(lon_in, 8),
                "lat": round(lat_in, 8)
            },
            "mars2000_meters": {
                "x": round(x_m, 3),
                "y": round(y_m, 3)
            },
            "round_trip_degrees": {
                "lon": round(lon_rt, 8),
                "lat": round(lat_rt, 8)
            },
            "round_trip_error_deg": {
                "lon_err": f"{err_lon:.2e}",
                "lat_err": f"{err_lat:.2e}",
                "passed_1e_9": (err_lon < TOLERANCE_DEG and err_lat < TOLERANCE_DEG)
            },
            "schema_validation_as_degrees": degrees_validation,
            "metres_as_degrees_trap": {
                "sent_values": {"lon": round(x_m, 3), "lat": round(y_m, 3)},
                "validation_passed": metres_as_degrees_validation["valid"],
                "validation_errors": metres_as_degrees_validation["errors"],
                "http_status_expected": 200 if metres_as_degrees_validation["valid"] else 422
            },
            "lon_wrap_result": {
                "original_lon": lon_in,
                "wrapped_lon": round(wrapped_lon, 8),
                "seam_shift_detected": (lon_in == 180.0 and wrapped_lon == -180.0)
            }
        })

    # Summary of wrap test cases
    wrap_checks = {
        "lon_270_maps_to": wrap_lon_manual_5_1(270.0),
        "lon_180_maps_to": wrap_lon_manual_5_1(180.0),
        "lon_minus_180_maps_to": wrap_lon_manual_5_1(-180.0),
        "seam_behavior_note": "Lon +180.0 maps to -180.0; both boundary limits fold onto the Western antimeridian [-180, 180)."
    }

    trap_failures = sum(1 for r in results if not r["metres_as_degrees_trap"]["validation_passed"])

    return {
        "generated_by": "scripts/arya/degrees_contract_check.py",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "crs": "MARS:2000 (IAU 2000 Mars Sphere, R = 3,396,190.0 m)",
        "tolerance_deg": TOLERANCE_DEG,
        "round_trip_accuracy": {
            "all_passed": (max_err_lon < TOLERANCE_DEG and max_err_lat < TOLERANCE_DEG),
            "max_err_lon_deg": f"{max_err_lon:.2e}",
            "max_err_lat_deg": f"{max_err_lat:.2e}",
            "worst_vector": worst_vector_name
        },
        "metres_as_degrees_trap_summary": {
            "total_tested": len(results),
            "rejected_by_backend_schema": trap_failures,
            "passed_only_at_origin": len(results) - trap_failures,
            "conclusion": "Raw projected metres sent as degrees are immediately rejected by Pydantic with HTTP 422 Unprocessable Entity for all non-origin coordinates."
        },
        "longitude_wrap_checks": wrap_checks,
        "openlayers_distance_notice": "OpenLayers ol/sphere.getLength() is strictly PROHIBITED because it hardcodes Earth authalic radius (6,371,008.8 m). Frontend displays only authoritative backend-calculated geodesic distances.",
        "vectors": results
    }


def main():
    print("=" * 75)
    print("Arya's Degrees Contract & Schema Trap Check (PREP TOOLING, NOT PRODUCT CODE)")
    print("=" * 75)

    res = run_checks()
    acc = res["round_trip_accuracy"]
    print(f"1. Bidirectional Precision Check (< {res['tolerance_deg']} deg):")
    print(f"   Max lon error: {acc['max_err_lon_deg']} deg")
    print(f"   Max lat error: {acc['max_err_lat_deg']} deg")
    print(f"   Worst case vector: {acc['worst_vector']}")
    print(f"   Status: {'PASSED' if acc['all_passed'] else 'FAILED'}")
    print("-" * 75)

    print("2. Longitude Wrap (Manual Section 5.1):")
    wc = res["longitude_wrap_checks"]
    print(f"   wrap_lon(270.0)  -> {wc['lon_270_maps_to']:.1f} deg (expected -90.0 deg)")
    print(f"   wrap_lon(180.0)  -> {wc['lon_180_maps_to']:.1f} deg (expected -180.0 deg)")
    print(f"   wrap_lon(-180.0) -> {wc['lon_minus_180_maps_to']:.1f} deg (expected -180.0 deg)")
    print(f"   Seam Note: {wc['seam_behavior_note']}")
    print("-" * 75)

    print("3. Metres-as-Degrees Schema Trap:")
    trap = res["metres_as_degrees_trap_summary"]
    print(f"   Tested vectors: {trap['total_tested']}")
    print(f"   Rejected (HTTP 422): {trap['rejected_by_backend_schema']}")
    print(f"   Passed (Origin (0,0) only): {trap['passed_only_at_origin']}")
    print(f"   {trap['conclusion']}")
    print("-" * 75)

    print("4. Distance Calculation Policy:")
    print(f"   {res['openlayers_distance_notice']}")
    print("=" * 75)

    if "--json" in sys.argv:
        print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
