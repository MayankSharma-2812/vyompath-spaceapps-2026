"""VyomPath — Coordinate Mathematics & Planetary Projection Service.

This module is the single mathematical source of truth for:
  - Mars reference radius (MARS_RADIUS_M = 3_396_190.0)
  - Great-circle Haversine distance calculation (scalar & vectorized)
  - Longitude normalization to [-180, 180)
  - Local tangent plane projection (local_xy_m) for corridors < 50 km
  - Cross-track and along-track projection (cross_along_m) for POIs and corridors

Reference datum:
  Mars 2000 Sphere (USGS / IAU2000:49900)
  Equatorial / volumetric radius R = 3,396,190.0 m.
"""

from __future__ import annotations

import math
from typing import Sequence, Tuple, Union
import numpy as np


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: Single source of truth for the Mars reference radius in metres.
#: Matches the Mars 2000 Sphere (+proj=eqc +R=3396190 +units=m).
MARS_RADIUS_M: float = 3_396_190.0

#: Mars equatorial circumference in metres.
MARS_CIRCUMFERENCE_M: float = 2.0 * math.pi * MARS_RADIUS_M


# ---------------------------------------------------------------------------
# Longitude Normalization
# ---------------------------------------------------------------------------

def normalize_longitude(lon: Union[float, np.ndarray]) -> Union[float, np.ndarray]:
    """Wrap any longitude value into canonical [-180.0, 180.0) degrees.

    Uses the formula ((lon + 180.0) % 360.0) - 180.0.
    Works for both scalar floats and NumPy arrays.
    """
    arr = np.asarray(lon, dtype=float)
    normalized = ((arr + 180.0) % 360.0) - 180.0
    if np.ndim(lon) == 0:
        return float(normalized)
    return normalized


# ---------------------------------------------------------------------------
# Haversine Distance (Mars 2000 Sphere)
# ---------------------------------------------------------------------------

def haversine_m(
    lon1: Union[float, np.ndarray],
    lat1: Union[float, np.ndarray],
    lon2: Union[float, np.ndarray],
    lat2: Union[float, np.ndarray],
) -> Union[float, np.ndarray]:
    """Compute the great-circle distance on the Mars 2000 sphere in metres.

    Accepts coordinates in degrees (lon, lat).
    Works with scalar floats as well as NumPy arrays of identical shape.

    Args:
        lon1: Longitude of start point(s) in degrees.
        lat1: Latitude of start point(s) in degrees.
        lon2: Longitude of end point(s) in degrees.
        lat2: Latitude of end point(s) in degrees.

    Returns:
        Distance in metres (float if inputs are scalar, np.ndarray otherwise).
    """
    p1 = np.radians(lat1)
    p2 = np.radians(lat2)
    dlon = np.radians(np.asarray(lon2, dtype=float) - np.asarray(lon1, dtype=float))
    dlat = p2 - p1

    a = np.sin(dlat / 2.0) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(dlon / 2.0) ** 2

    # Guard against floating-point precision overflow past 1.0 (e.g. identical points)
    a = np.clip(a, 0.0, 1.0)
    dist = 2.0 * MARS_RADIUS_M * np.arcsin(np.sqrt(a))

    if np.ndim(dist) == 0:
        return float(dist)
    return dist


# ---------------------------------------------------------------------------
# 3D Surface Distance ([v3.1])
# ---------------------------------------------------------------------------

def surface_distance_3d_m(
    d2d_m: Union[float, Sequence[float], np.ndarray],
    dz_m: Union[float, Sequence[float], np.ndarray],
) -> Union[float, np.ndarray]:
    """Compute 3D along-ground surface distance for profile segment(s).

    Combines 2D horizontal step distance with vertical displacement:
        d_3d = sqrt(d_2d^2 + dz^2)

    Args:
        d2d_m: 2D horizontal step distance in metres.
        dz_m: Elevation delta (z2 - z1) in metres.

    Returns:
        3D surface distance in metres (scalar float or ndarray).
    """
    res = np.hypot(np.asarray(d2d_m, dtype=float), np.asarray(dz_m, dtype=float))
    if np.ndim(d2d_m) == 0 and np.ndim(dz_m) == 0:
        return float(res)
    return res


# ---------------------------------------------------------------------------
# Local Cartesian Tangent Plane
# ---------------------------------------------------------------------------

def local_xy_m(
    lon: Union[float, Sequence[float], np.ndarray],
    lat: Union[float, Sequence[float], np.ndarray],
    lon0: float,
    lat0: float,
) -> Tuple[np.ndarray, np.ndarray]:
    """Convert planetary lon/lat degrees into metres east and north of (lon0, lat0).

    Uses an equirectangular approximation centered at (lon0, lat0):
        x = (lon - lon0) * cos(lat0) * R
        y = (lat - lat0) * R

    Accurate to within sub-metre tolerances for corridors under ~50 km.

    Args:
        lon: Longitude(s) in degrees.
        lat: Latitude(s) in degrees.
        lon0: Center origin longitude in degrees.
        lat0: Center origin latitude in degrees.

    Returns:
        (x_m, y_m): Metres east and metres north as float or ndarray.
    """
    x = np.radians(np.asarray(lon, dtype=float) - lon0) * np.cos(np.radians(lat0)) * MARS_RADIUS_M
    y = np.radians(np.asarray(lat, dtype=float) - lat0) * MARS_RADIUS_M
    return x, y


# ---------------------------------------------------------------------------
# Cross-Track and Along-Track Projections
# ---------------------------------------------------------------------------

def cross_along_m(
    route_xy: np.ndarray,
    p: Sequence[float] | np.ndarray,
) -> Tuple[float, float]:
    """Calculate perpendicular cross-track distance and cumulative along-route distance.

    Args:
        route_xy: (N, 2) array of route waypoints in projected metres (x, y).
                  Requires N >= 2 vertices.
        p: (2,) target point in projected metres [x, y].

    Returns:
        (cross_track_m, along_route_m):
          - cross_track_m: Shortest distance from point p to the route polyline (>= 0.0).
          - along_route_m: Distance along the route from the start to the projected point.
    """
    route_xy = np.asarray(route_xy, dtype=float)
    p = np.asarray(p, dtype=float)

    if len(route_xy) < 2:
        raise ValueError("route_xy must have at least 2 vertices")

    a = route_xy[:-1]  # Start points of segments (N-1, 2)
    b = route_xy[1:]   # End points of segments (N-1, 2)
    ab = b - a         # Segment vectors (N-1, 2)

    seg_lens = np.hypot(ab[:, 0], ab[:, 1])

    # Projection parameter t clamped to segment interval [0.0, 1.0]
    denom = np.maximum(seg_lens ** 2, 1e-9)
    proj_num = ((p - a) * ab).sum(axis=1)
    t = np.clip(proj_num / denom, 0.0, 1.0)

    # Projected points on each segment
    proj_pts = a + ab * t[:, None]
    dists = np.hypot(p[0] - proj_pts[:, 0], p[1] - proj_pts[:, 1])

    # Find the nearest segment
    i = int(np.argmin(dists))
    along_m = float(seg_lens[:i].sum() + t[i] * seg_lens[i])
    cross_m = float(dists[i])

    return cross_m, along_m
