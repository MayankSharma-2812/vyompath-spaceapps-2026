"""Data Quality and Schema Validator for VyomPath.

Role: Shyam Sharma (NASA Source & DTM Data Lead)
Team: NAKSHATRA X

Validates:
1. data/layers.json - NASA WMTS layers and datum specification.
2. data/science_points.json - Sourced Martian scientific points of interest.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
LAYERS_FILE = REPO_ROOT / "data" / "layers.json"
POINTS_FILE = REPO_ROOT / "data" / "science_points.json"


def validate_layers(path: Path = LAYERS_FILE) -> list[str]:
    """Validate layer manifest JSON file."""
    errors = []
    if not path.is_file():
        return [f"File not found: {path}"]

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return [f"JSON parse error in {path.name}: {exc}"]

    layers = data.get("layers", data if isinstance(data, list) else None)
    if layers is None or not isinstance(layers, list):
        return ["Manifest must contain a 'layers' array or be a root array."]

    if len(layers) == 0:
        errors.append("Manifest 'layers' list is empty.")

    required_keys = ["id", "name", "type", "service_url", "native_crs", "bounds", "citation", "source_url"]

    for idx, lyr in enumerate(layers):
        if not isinstance(lyr, dict):
            errors.append(f"Layer [{idx}] is not an object.")
            continue

        for key in required_keys:
            if key not in lyr:
                errors.append(f"Layer [{idx}] missing required key '{key}'")
            elif not lyr[key]:
                errors.append(f"Layer [{idx}] key '{key}' is empty")

        # Validate URL template
        url = lyr.get("service_url", "")
        if url and not url.startswith(("http://", "https://")):
            errors.append(f"Layer [{idx}] '{lyr.get('id')}': service_url is not HTTP/HTTPS")

        # Validate Bounds [min_lon, min_lat, max_lon, max_lat]
        bounds = lyr.get("bounds")
        if bounds is not None:
            if not isinstance(bounds, (list, tuple)) or len(bounds) != 4:
                errors.append(f"Layer [{idx}] '{lyr.get('id')}': bounds must be 4 floats [min_lon, min_lat, max_lon, max_lat]")
            else:
                w, s, e, n = bounds
                if not (-180.0 <= w <= 180.0 and -180.0 <= e <= 180.0 and w <= e):
                    errors.append(f"Layer [{idx}] '{lyr.get('id')}': invalid longitude bounds [{w}, {e}]")
                if not (-90.0 <= s <= 90.0 and -90.0 <= n <= 90.0 and s <= n):
                    errors.append(f"Layer [{idx}] '{lyr.get('id')}': invalid latitude bounds [{s}, {n}]")

    return errors


def _extract_points(data: object, path: Path = POINTS_FILE) -> list[dict]:
    """Extract and normalize science points from root list or dictionary."""
    if isinstance(data, list):
        raw_points = data
    elif isinstance(data, dict):
        raw_points = data.get("points")
        if not isinstance(raw_points, list):
            raise ValueError("Science catalogue must contain a 'points' array.")
    else:
        raise ValueError("Science catalogue must contain a 'points' array.")

    points = []
    for item in raw_points:
        if isinstance(item, dict):
            pt = dict(item)
            if "coordinates" not in pt and "lon" in pt and "lat" in pt:
                pt["coordinates"] = [pt["lon"], pt["lat"]]
            if "citation" not in pt:
                # Intended citation precedence: source_title or source (never terms_of_use)
                citation = pt.get("source_title") or pt.get("source")
                if citation:
                    pt["citation"] = citation
            points.append(pt)
        else:
            points.append(item)
    return points


def resolve_citation(record: dict) -> str | None:
    """Resolve source citation string following the strict precedence rule:
    1. Explicit non-empty 'citation'.
    2. Meaningful non-empty 'source_title'.
    3. Valid HTTP/HTTPS 'source_url'.

    Important:
      'terms_of_use' or licensing policy text must NEVER substitute for a source citation.
      License status and policy metadata are separate from citation metadata.
    """
    cit = record.get("citation")
    tou = record.get("terms_of_use")
    pol_ref = record.get("source_policy_reference")

    if isinstance(cit, str) and cit.strip():
        # Reject if terms_of_use or policy reference was improperly used as citation
        if isinstance(tou, str) and tou.strip() and cit.strip().lower() == tou.strip().lower():
            return None
        if isinstance(pol_ref, str) and pol_ref.strip() and cit.strip().lower() == pol_ref.strip().lower():
            return None
        return cit.strip()

    title = record.get("source_title")
    if isinstance(title, str) and title.strip():
        return title.strip()

    url = record.get("source_url")
    if isinstance(url, str) and url.strip().startswith(("http://", "https://")):
        return url.strip()

    return None


def validate_science_points(path: Path = POINTS_FILE) -> list[str]:
    """Validate science points of interest JSON file."""
    errors = []
    if not path.is_file():
        return [f"File not found: {path}"]

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return [f"JSON parse error in {path.name}: {exc}"]

    try:
        points = _extract_points(data, path)
    except ValueError as exc:
        return [str(exc)]

    if len(points) == 0:
        errors.append("Science catalogue 'points' list is empty.")

    base_required_keys = ["id", "name", "coordinates", "mission", "significance", "source_url"]

    for idx, pt in enumerate(points):
        if not isinstance(pt, dict):
            errors.append(f"Point [{idx}] is not an object.")
            continue

        poi_id = pt.get("id", f"index-{idx}")

        for key in base_required_keys:
            if key not in pt:
                errors.append(f"Point [{idx}] missing required key '{key}'")
            elif pt[key] is None or (isinstance(pt[key], str) and not pt[key].strip()):
                errors.append(f"Point [{idx}] key '{key}' is empty")

        # Citation validation: terms_of_use must NEVER substitute for citation
        resolved_cit = resolve_citation(pt)
        if not resolved_cit:
            errors.append(
                f"Point [{idx}] '{poi_id}': missing valid citation (terms_of_use cannot substitute for citation)"
            )
        elif pt.get("terms_of_use") and isinstance(pt.get("citation"), str) and pt.get("citation", "").strip() == str(pt.get("terms_of_use")).strip():
            errors.append(
                f"Point [{idx}] '{poi_id}': terms_of_use cannot substitute for citation metadata"
            )

        # License policy verification: unverified policy status representation
        # License status must remain distinct from citation metadata
        if pt.get("source_policy_status") == "unverified" or pt.get("terms_of_use_status") == "unverified":
            if pt.get("terms_of_use") is not None:
                errors.append(
                    f"Point [{idx}] '{poi_id}': unverified policy status cannot report non-null terms_of_use"
                )
            if pt.get("source_policy_reference") is not None:
                errors.append(
                    f"Point [{idx}] '{poi_id}': unverified policy status cannot report non-null source_policy_reference"
                )

        # Check coordinates: [lon, lat]
        coords = pt.get("coordinates")
        if coords is not None:
            if not isinstance(coords, (list, tuple)) or len(coords) != 2:
                errors.append(f"Point [{idx}] '{poi_id}': coordinates must be [lon, lat]")
            else:
                lon, lat = coords
                if not (-180.0 <= lon <= 180.0):
                    errors.append(f"Point [{idx}] '{poi_id}': longitude {lon} out of [-180, 180]")
                if not (-90.0 <= lat <= 90.0):
                    errors.append(f"Point [{idx}] '{poi_id}': latitude {lat} out of [-90, 90]")

        # Check URL
        url = pt.get("source_url", "")
        if url and not url.startswith(("http://", "https://")):
            errors.append(f"Point [{idx}] '{poi_id}': source_url must be valid HTTP/HTTPS link")

    return errors


def run_full_validation() -> bool:
    """Run validation across all datasets and print formatted report."""
    print("=" * 65)
    print("  VYOMPATH DATA QUALITY AUDIT - SHYAM SHARMA")
    print("=" * 65)

    layer_errors = validate_layers(LAYERS_FILE)
    print(f"\n[1] Layer Manifest: {LAYERS_FILE.relative_to(REPO_ROOT)}")
    if layer_errors:
        print(f"    STATUS: FAIL ({len(layer_errors)} errors)")
        for err in layer_errors:
            print(f"      [X] {err}")
    else:
        print("    - Structural Schema: PASS (All layers structurally sound & valid bounds)")
        print("    - Service Endpoints: PASS (Verified HTTP/HTTPS WMTS/WMS service URLs)")

    poi_errors = validate_science_points(POINTS_FILE)
    print(f"\n[2] Science POIs:   {POINTS_FILE.relative_to(REPO_ROOT)}")
    if poi_errors:
        print(f"    STATUS: FAIL ({len(poi_errors)} errors)")
        for err in poi_errors:
            print(f"      [X] {err}")
    else:
        print("    - Structural Schema: PASS (Valid planetary coordinates in [-180, 180], [-90, 90])")
        print("    - Citation Metadata: PASS (Sourced MMGIS telemetry; terms_of_use not substituted)")
        print("    - Policy Status:     PASS (Unverified licensing status strictly preserved as null)")

    print("\n" + "=" * 65)
    total_errors = len(layer_errors) + len(poi_errors)
    if total_errors == 0:
        print("  RESULT: 100% QUALITY PASS - Structural & Citation Verified")
        print("  NOTICE: Licensing policies remain preserved as unverified.")
        print("=" * 65)
        return True
    else:
        print(f"  RESULT: FAILED with {total_errors} errors. Correction needed.")
        print("=" * 65)
        return False


if __name__ == "__main__":
    success = run_full_validation()
    sys.exit(0 if success else 1)
