"""Science-POI corridor-buffer service.

Finds verified Martian science points of interest within a configurable
corridor around a user-drawn route.

Algorithm & Architecture
------------------------
1. Load the verified POI catalogue from data/science_points.json (fallback to
   backend/data/science_points.json).
2. Project both route waypoints and POI locations onto a local metric plane
   (in metres) relative to the route centre using coords.local_xy_m.
3. Compute exact cross-track (perpendicular) and along-route distances for each
   candidate POI using analytical segment vector projection (coords.cross_along_m).
4. Filter POIs by corridor buffer threshold (cross_track <= buffer_distance_m),
   avoiding costly 2D polygon buffer allocation.
5. Return results as NearbyPOI models, sorted ascending by along_route_m.

Coordinate Conventions
----------------------
- Longitude: East-positive degrees, range [-180, 180].
- Latitude: Planetocentric degrees, range [-90, 90].
- Radius: Mars 2000 Equirectangular Sphere, R = 3,396,190.0 m (Decision D4).

Owner: Dheer | NASA Space Apps Challenge 2026
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import List, Optional

import numpy as np

from backend.app.schemas import Coordinate, NearbyPOI
from backend.app.services.coords import (
    MARS_RADIUS_M as _MARS_RADIUS_M,
    cross_along_m as _cross_along_m,
    local_xy_m as _local_xy_m,
)

# ---------------------------------------------------------------------------
# Constants & Paths
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).resolve().parents[3]
_CATALOGUE_CANDIDATE_PATHS: list[Path] = [
    _REPO_ROOT / "data" / "poi_strictly_sourced.json",
    _REPO_ROOT / "data" / "science_points.json",
    Path(__file__).resolve().parents[2] / "data" / "poi_strictly_sourced.json",
    Path(__file__).resolve().parents[2] / "data" / "science_points.json",
]


def _resolve_default_catalogue_path() -> Path:
    """Find the default science_points.json file."""
    for p in _CATALOGUE_CANDIDATE_PATHS:
        if p.exists():
            return p
    return _CATALOGUE_CANDIDATE_PATHS[0]


# ---------------------------------------------------------------------------
# Catalogue Loading
# ---------------------------------------------------------------------------

def _load_catalogue(path: Optional[Path] = None) -> list[dict]:
    """Load and validate the science-points catalogue.

    Seamlessly supports:
    1. Bundle poi_strictly_sourced.json (with 'note', 'source', 'sol', etc.)
    2. Official data/science_points.json (with top-level 'points' list or flat array)
    3. Test fixture catalogues

    Returns a list of dicts with normalized keys:
      id, name, lon, lat, mission, source_url, significance.
    """
    cat_path = path or _resolve_default_catalogue_path()
    if not cat_path.exists():
        return []

    try:
        with open(cat_path, encoding="utf-8") as fh:
            raw = json.load(fh)
    except (json.JSONDecodeError, OSError):
        return []

    entries: list[dict] = []
    if isinstance(raw, dict) and "points" in raw and isinstance(raw["points"], list):
        entries = raw["points"]
    elif isinstance(raw, list):
        entries = raw
    else:
        return []

    valid: list[dict] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue

        poi_id = entry.get("id")
        poi_name = entry.get("name")
        if not poi_id or not poi_name:
            continue

        # Extract coordinates from either "coordinates": [lon, lat] or "lon"/"lat"
        lon = entry.get("lon")
        lat = entry.get("lat")
        if (lon is None or lat is None) and "coordinates" in entry:
            coords = entry["coordinates"]
            if isinstance(coords, (list, tuple)) and len(coords) >= 2:
                lon, lat = coords[0], coords[1]

        if lon is None or lat is None:
            continue

        try:
            lon_f = float(lon)
            lat_f = float(lat)
        except (ValueError, TypeError):
            continue

        # Normalized metadata fields
        mission = entry.get("mission") or "Mars 2020 (Perseverance)"
        source_url = entry.get("source_url") or entry.get("source") or ""

        # Verbatim raw telemetry note (if present)
        source_note = entry.get("source_note")

        # Safe precedence rule for display description:
        # 1. display_annotation (authored contextual description)
        # 2. legacy note (backward compatibility with older records)
        # 3. source_note (fallback to raw telemetry note)
        # 4. legacy significance / limitation (from legacy catalogues)
        significance = (
            entry.get("display_annotation")
            or entry.get("note")
            or entry.get("source_note")
            or entry.get("significance")
            or entry.get("limitation")
            or ""
        )

        item = dict(entry)
        item["id"] = str(poi_id)
        item["name"] = str(poi_name)
        item["lon"] = lon_f
        item["lat"] = lat_f
        item["mission"] = str(mission)
        item["source_url"] = str(source_url)
        item["significance"] = str(significance)
        if source_note is not None:
            item["source_note"] = str(source_note)
        valid.append(item)

    return valid


# ---------------------------------------------------------------------------
# Metric Projection Helpers
# ---------------------------------------------------------------------------

def _m_per_deg_lat() -> float:
    """Metres per degree of latitude on the Mars sphere."""
    return _MARS_RADIUS_M * math.pi / 180.0


def _m_per_deg_lon(lat_deg: float) -> float:
    """Metres per degree of longitude at *lat_deg* on the Mars sphere."""
    return _MARS_RADIUS_M * math.cos(math.radians(lat_deg)) * math.pi / 180.0


# ---------------------------------------------------------------------------
# Public Service API
# ---------------------------------------------------------------------------

def nearby_pois(
    route_coords: list[Coordinate],
    buffer_distance_m: float = 250.0,
    *,
    catalogue_path: Optional[Path] = None,
) -> list[NearbyPOI]:
    """Return science POIs within *buffer_distance_m* of the route.

    Parameters
    ----------
    route_coords:
        Ordered waypoints defining the route (>= 2 points).
    buffer_distance_m:
        Lateral search distance in metres (50-2000 m; 100/250/500 m in UI).
    catalogue_path:
        Optional override for catalogue file path (useful in tests).

    Returns
    -------
    list[NearbyPOI]
        POIs inside the corridor, sorted ascending by ``along_route_m``.
    """
    catalogue = _load_catalogue(catalogue_path)
    if not catalogue or len(route_coords) < 2:
        return []

    # Standard parallel and origin: mean route coordinates
    lon0 = sum(c.lon for c in route_coords) / len(route_coords)
    lat0 = sum(c.lat for c in route_coords) / len(route_coords)

    # Project route into local metric Cartesian coordinates
    route_lons = [c.lon for c in route_coords]
    route_lats = [c.lat for c in route_coords]
    rx, ry = _local_xy_m(route_lons, route_lats, lon0, lat0)
    route_xy = np.column_stack((rx, ry))

    results: list[NearbyPOI] = []

    for poi in catalogue:
        px, py = _local_xy_m(poi["lon"], poi["lat"], lon0, lat0)
        p = np.array([float(px), float(py)])

        # Analytical vector projection for exact cross-track & along-route distance
        cross_track, along_route = _cross_along_m(route_xy, p)

        if cross_track > buffer_distance_m:
            continue

        results.append(
            NearbyPOI(
                id=poi["id"],
                name=poi["name"],
                mission=poi["mission"],
                cross_track_m=round(cross_track, 2),
                along_route_m=round(along_route, 2),
                source_url=poi["source_url"],
                significance=poi["significance"],
                source_note=poi.get("source_note"),
            )
        )

    results.sort(key=lambda p: p.along_route_m)
    return results


# Backward-compatible alias for previous test suites / callers
nearby_points = nearby_pois
