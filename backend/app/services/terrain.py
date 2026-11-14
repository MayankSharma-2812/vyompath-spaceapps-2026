"""VyomPath — Terrain Service: Geospatial Calculation & Raster Engine.

This module implements:
  - Mars 2000 spherical-geometry and distance wrappers.
  - Coordinate normalization and input validation.
  - Equirectangular DTM ground spacing adjustments (accounting for standard parallel 15°N).
  - Baseline pixel window calculation for slope scales (20 m, 50 m, 100 m).
  - 2D terrain slope gradient calculation.

Owner: Pranav (Terrain Service & Raster Sampling Lead).
"""

from __future__ import annotations

import math
import os
from typing import Any, Dict, Optional, Sequence, Tuple, Union
import numpy as np

from backend.app.schemas import Coordinate, ElevationPoint
from backend.app.services.coords import (
    MARS_RADIUS_M,
    MARS_CIRCUMFERENCE_M,
    normalize_longitude,
    haversine_m as coords_haversine_m,
    surface_distance_3d_m,
)


# ---------------------------------------------------------------------------
# DTM Geospatial Projection & Spacing Constants
# ---------------------------------------------------------------------------

#: The HiRISE/MOLA DTM standard parallel for regional products in degrees.
#: At standard parallel 15°N, scale factor is 1.0.
LAT_TS_DEG: float = 15.0


# ---------------------------------------------------------------------------
# Input Validation Helpers
# ---------------------------------------------------------------------------

def _validate_coordinate(coord: Coordinate, label: str = "coordinate") -> None:
    """Raise ValueError if a Coordinate falls outside planetary bounds."""
    if not (-180.0 <= coord.lon <= 180.0):
        raise ValueError(
            f"{label}: longitude {coord.lon!r} is outside [-180, 180]. "
            "Normalise with normalize_longitude() before calling."
        )
    if not (-90.0 <= coord.lat <= 90.0):
        raise ValueError(
            f"{label}: latitude {coord.lat!r} is outside [-90, 90]."
        )


def _validate_route(coords: Sequence[Coordinate]) -> None:
    """Raise ValueError if the coordinate sequence has fewer than 2 points."""
    if len(coords) < 2:
        raise ValueError(
            f"A route requires at least 2 coordinates; got {len(coords)}."
        )


# ---------------------------------------------------------------------------
# Haversine Distance Wrappers for Coordinate Objects
# ---------------------------------------------------------------------------

def haversine_m(a: Coordinate, b: Coordinate) -> float:
    """Compute great-circle distance between two Coordinate objects in metres.

    Uses Mars 2000 Sphere (R = 3,396,190 m).
    Clamped against numerical precision overflow in arcsin.
    """
    _validate_coordinate(a, label="point a")
    _validate_coordinate(b, label="point b")
    return float(coords_haversine_m(a.lon, a.lat, b.lon, b.lat))


def segment_distances_m(coords: Sequence[Coordinate]) -> list[float]:
    """Return great-circle length of each consecutive segment in metres."""
    _validate_route(coords)
    return [
        haversine_m(coords[i], coords[i + 1])
        for i in range(len(coords) - 1)
    ]


def route_distance_m(coords: Sequence[Coordinate]) -> float:
    """Return total great-circle length of a multi-waypoint route in metres."""
    return sum(segment_distances_m(coords))


# ---------------------------------------------------------------------------
# Ground Spacing and Slope Calculations (Master Manual v3 § 5.3)
# ---------------------------------------------------------------------------

def ground_spacing_m(
    px_x: float,
    px_y: float,
    lat_deg: float,
    lat_ts_deg: float = LAT_TS_DEG,
) -> Tuple[float, float]:
    """Calculate actual ground resolution (dx, dy) in metres for an equirectangular DTM.

    For Mars equirectangular projections with standard parallel lat_ts (typically 15°N):
        dx = px_x * cos(lat) / cos(lat_ts)
        dy = px_y

    Example:
        At lat = 18.3°N with lat_ts = 15°N, dx ≈ 0.983 * px_x.

    Args:
        px_x: Pixel spacing in X from raster geotransform (metres).
        px_y: Pixel spacing in Y from raster geotransform (metres).
        lat_deg: Target latitude on Mars in planetocentric degrees.
        lat_ts_deg: Standard parallel latitude of the projection (default: 15.0°N).

    Returns:
        (dx, dy) ground spacing in metres.
    """
    lat_rad = np.radians(lat_deg)
    lat_ts_rad = np.radians(lat_ts_deg)
    dx = float(px_x * np.cos(lat_rad) / np.cos(lat_ts_rad))
    dy = float(px_y)
    return dx, dy


def baseline_px(window_m: float, pixel_m: float) -> int:
    """Calculate the half-window size in pixels for a given metric window in metres.

    Ensures at least 1 pixel is used on each side of the evaluation point.

    Args:
        window_m: Target analysis window in ground metres (e.g. 20.0, 50.0, 100.0).
        pixel_m: Effective pixel resolution in ground metres.

    Returns:
        Integer pixel count for each side of the point (>= 1).
    """
    return max(1, round(window_m / 2.0 / pixel_m))


def terrain_slope_deg(
    z: np.ndarray,
    dx: float,
    dy: float,
) -> np.ndarray:
    """Calculate 2D surface slope angle in degrees from an elevation grid.

    Calculates horizontal gradients using central differences:
        gy, gx = np.gradient(z, dy, dx)
        slope = arctan(hypot(gx, gy)) * 180 / pi

    Args:
        z: 2D NumPy array of elevation values in metres (NaN for NoData).
        dx: Ground spacing in X (east-west) in metres.
        dy: Ground spacing in Y (north-south) in metres.

    Returns:
        2D NumPy array of slope values in degrees.
    """
    z_arr = np.asarray(z, dtype=float)
    gy, gx = np.gradient(z_arr, dy, dx)
    hyp = np.hypot(gx, gy)
    slope_deg = np.degrees(np.arctan(hyp))
    return slope_deg


# ---------------------------------------------------------------------------
# LTTB Downsampling Algorithm (Master Manual v3.1 § 5.1 & § 5.5)
# ---------------------------------------------------------------------------

def lttb_downsample(
    points: Sequence[Tuple[float, float]],
    threshold: int = 500,
) -> list[Tuple[float, float]]:
    """Downsample a series of (x, y) 2D points using Largest Triangle Three Buckets.

    Preserves peaks, valleys, and visual topography for frontend rendering
    without changing the underlying full-resolution profile.

    Args:
        points: Ordered sequence of (distance_m, elevation_m) tuples.
        threshold: Target maximum number of points to retain (>= 3).

    Returns:
        Downsampled list of (distance_m, elevation_m) tuples with length <= threshold.
    """
    n = len(points)
    if n <= threshold or threshold <= 2:
        return list(points)

    sampled: list[Tuple[float, float]] = [points[0]]

    # Bucket size: exclude the first and last points
    every = (n - 2) / (threshold - 2)

    a_idx = 0  # Index of the previously chosen point

    for i in range(threshold - 2):
        # Calculate the bucket range
        bucket_start = int(math.floor((i + 0) * every) + 1)
        bucket_end = int(math.floor((i + 1) * every) + 1)
        bucket_end = min(bucket_end, n)

        # Calculate the next bucket range for the average point
        next_start = int(math.floor((i + 1) * every) + 1)
        next_end = int(math.floor((i + 2) * every) + 1)
        next_end = min(next_end, n)

        # Average point of the next bucket
        if next_start < next_end:
            avg_x = sum(points[j][0] for j in range(next_start, next_end)) / (next_end - next_start)
            avg_y = sum(points[j][1] for j in range(next_start, next_end)) / (next_end - next_start)
        else:
            avg_x, avg_y = points[-1]

        # Point A coordinates
        ax, ay = points[a_idx]

        max_area = -1.0
        max_idx = bucket_start

        # Find point in current bucket maximizing the triangle area with A and average next
        for j in range(bucket_start, bucket_end):
            bx, by = points[j]
            # Area of triangle: 0.5 * |ax(by - cy) + bx(cy - ay) + cx(ay - by)|
            area = abs(
                (ax - avg_x) * (by - ay) - (ax - bx) * (avg_y - ay)
            ) * 0.5
            if area > max_area:
                max_area = area
                max_idx = j

        sampled.append(points[max_idx])
        a_idx = max_idx

    sampled.append(points[-1])
    return sampled


# ---------------------------------------------------------------------------
# Along-Track Grade (Slope at scale W, Master Manual v3.1 § 5.3)
# ---------------------------------------------------------------------------

def along_track_grades(
    distances_m: Sequence[float],
    elevations_m: Sequence[float],
    window_m: float = 50.0,
    source_mask: Optional[Sequence[Any]] = None,
) -> Tuple[float, list[float]]:
    """Compute along-track grade at baseline evaluation window W metres.

    For each evaluation point s along the route:
        grade(s) = arctan((z(s + W/2) - z(s - W/2)) / W) in degrees

    Args:
        distances_m: Cumulative 1D distance array along the route (strictly ascending).
        elevations_m: Elevation array at each distance sample (metres, NaN allowed).
        window_m: Baseline span W in metres (e.g. 20.0, 50.0, 100.0).
        source_mask: Optional sequence of dataset source identifiers at each sample.
            When adjacent samples have differing source identifiers, the segment
            between them is treated as a seam transition, and any evaluation window
            intersecting that segment is marked unavailable (NaN).

    Returns:
        (max_grade_deg, grades_list):
          - max_grade_deg: Maximum absolute grade observed along the route in degrees,
            or NaN if no evaluation window has a valid grade.
          - grades_list: Grade in degrees evaluated at each profile point (NaN if unavailable).

    Raises:
        ValueError: If distances_m and elevations_m lengths differ, or if source_mask
            is provided and its length differs from distances_m.
    """
    n = len(distances_m)
    if len(elevations_m) != n:
        raise ValueError(
            f"distances_m length ({n}) does not match elevations_m length ({len(elevations_m)})."
        )
    if source_mask is not None and len(source_mask) != n:
        raise ValueError(
            f"source_mask length ({len(source_mask)}) does not match distances_m length ({n})."
        )

    if n < 2:
        return float("nan"), [float("nan")] * n

    dist_arr = np.asarray(distances_m, dtype=float)
    elev_arr = np.asarray(elevations_m, dtype=float)

    # Detect seam transition segments where source_mask changes
    seam_segments: list[Tuple[float, float]] = []
    if source_mask is not None:
        for j in range(n - 1):
            if source_mask[j] != source_mask[j + 1]:
                seam_segments.append((dist_arr[j], dist_arr[j + 1]))

    half_w = window_m / 2.0
    grades: list[float] = []

    for i in range(n):
        s_cur = dist_arr[i]
        s_back = max(dist_arr[0], s_cur - half_w)
        s_fwd = min(dist_arr[-1], s_cur + half_w)
        span = s_fwd - s_back

        if span <= 1e-3:
            grades.append(0.0)
            continue

        # Check if evaluation window [s_back, s_fwd] intersects any seam transition segment [s_j, s_j+1]
        # Overlap occurs if s_back < s_seg_end and s_fwd > s_seg_start (with tolerance for boundary touching)
        intersects_seam = False
        for s_seg_start, s_seg_end in seam_segments:
            if s_back < s_seg_end - 1e-9 and s_fwd > s_seg_start + 1e-9:
                intersects_seam = True
                break

        if intersects_seam:
            grades.append(float("nan"))
            continue

        # Interpolate elevation at s_back and s_fwd
        z_back = float(np.interp(s_back, dist_arr, elev_arr))
        z_fwd = float(np.interp(s_fwd, dist_arr, elev_arr))

        if np.isnan(z_back) or np.isnan(z_fwd):
            grades.append(float("nan"))
        else:
            dz = z_fwd - z_back
            grade = float(np.degrees(np.arctan(dz / span)))
            grades.append(grade)

    valid_abs_grades = [abs(g) for g in grades if not np.isnan(g)]
    max_grade = max(valid_abs_grades) if valid_abs_grades else float("nan")

    return max_grade, grades


# ---------------------------------------------------------------------------
# Route Densification (5 m Spacing, Terrain Spec v3.1 § 3.2)
# ---------------------------------------------------------------------------

def densify_route(
    coords: Sequence[Coordinate],
    step_m: float = 5.0,
) -> list[Coordinate]:
    """Densify a polyline of Coordinates to uniform step_m intervals.

    Args:
        coords: Sequence of >= 2 Coordinate waypoints.
        step_m: Target sampling interval in metres (default: 5.0 m).

    Returns:
        List of interpolated Coordinate objects spaced <= step_m apart.
    """
    _validate_route(coords)
    densified: list[Coordinate] = [coords[0]]

    for i in range(len(coords) - 1):
        c1, c2 = coords[i], coords[i + 1]
        seg_dist = haversine_m(c1, c2)

        if seg_dist <= step_m:
            densified.append(c2)
            continue

        num_steps = int(math.ceil(seg_dist / step_m))
        for step in range(1, num_steps):
            frac = step / float(num_steps)
            interp_lon = c1.lon + frac * (c2.lon - c1.lon)
            interp_lat = c1.lat + frac * (c2.lat - c1.lat)
            densified.append(Coordinate(lon=normalize_longitude(interp_lon), lat=interp_lat))
        densified.append(c2)

    return densified


# ---------------------------------------------------------------------------
# Raster Sampling & Strict 4-Neighbor NoData Handling (Spec v3.1 § 3.4)
# ---------------------------------------------------------------------------

def sample_point_bilinear(
    data: np.ndarray,
    col_f: float,
    row_f: float,
    nodata: float = -3.4028227e+38,
) -> float:
    """Sample elevation using strict 4-neighbor bilinear interpolation.

    Strict NoData Rule:
        If ANY of the 4 surrounding pixels (c0, r0), (c1, r0), (c0, r1), (c1, r1)
        is equal to nodata, NaN, or outside raster bounds, returns NaN.

    Args:
        data: 2D numpy array of elevations (height x width).
        col_f: Floating-point pixel column coordinate.
        row_f: Floating-point pixel row coordinate.
        nodata: NoData sentinel value.

    Returns:
        Interpolated elevation in metres, or NaN if any neighbor is invalid.
    """
    h, w = data.shape
    c0 = int(math.floor(col_f))
    r0 = int(math.floor(row_f))
    c1 = c0 + 1
    r1 = r0 + 1

    if c0 < 0 or r0 < 0 or c1 >= w or r1 >= h:
        return float("nan")

    z00 = data[r0, c0]
    z10 = data[r0, c1]
    z01 = data[r1, c0]
    z11 = data[r1, c1]

    for val in (z00, z10, z01, z11):
        if np.isnan(val) or val == nodata or abs(val - nodata) < 1e-4:
            return float("nan")

    dc = col_f - c0
    dr = row_f - r0

    top = (1.0 - dc) * z00 + dc * z10
    bot = (1.0 - dc) * z01 + dc * z11
    return float((1.0 - dr) * top + dr * bot)


# ---------------------------------------------------------------------------
# Gap Processing & Gain / Loss Accumulation (Spec v3.1 § 3.5)
# ---------------------------------------------------------------------------

def process_elevation_gaps(
    elevations: Sequence[float],
    step_m: float = 5.0,
    max_fill_m: float = 15.0,
) -> Tuple[list[float], str, float, float]:
    """Process NoData gaps and compute elevation gain / loss.

    Rules:
        - Gaps <= max_fill_m (<= 3 steps at 5 m) are filled linearly.
        - Gaps > max_fill_m are left as NaN and trigger 'partial_gap'.
        - If all samples are NaN, returns 'out_of_bounds'.
        - If all samples are valid (or filled), returns 'complete'.
        - Gain and loss are summed over consecutive valid samples.

    Returns:
        (processed_elevations, coverage_status, total_gain_m, total_loss_m)
    """
    raw = list(elevations)
    n = len(raw)

    valid_count = sum(1 for z in raw if not np.isnan(z))
    if valid_count == 0:
        return [float("nan")] * n, "out_of_bounds", 0.0, 0.0

    filled = list(raw)
    has_large_gap = False
    max_fill_steps = int(max_fill_m // step_m)

    # Detect gaps and fill short ones
    idx = 0
    while idx < n:
        if np.isnan(filled[idx]):
            start = idx
            while idx < n and np.isnan(filled[idx]):
                idx += 1
            gap_len = idx - start
            # If bounded by valid points on both ends and gap <= max_fill_steps
            if start > 0 and idx < n and gap_len <= max_fill_steps:
                z_start = filled[start - 1]
                z_end = filled[idx]
                for k in range(gap_len):
                    frac = (k + 1) / float(gap_len + 1)
                    filled[start + k] = float(z_start + frac * (z_end - z_start))
            else:
                has_large_gap = True
        else:
            idx += 1

    # Determine coverage status
    if any(np.isnan(z) for z in filled):
        coverage_status = "partial_gap"
    else:
        coverage_status = "complete"

    # Gain and loss accumulation across valid steps
    total_gain = 0.0
    total_loss = 0.0

    for i in range(len(filled) - 1):
        z1, z2 = filled[i], filled[i + 1]
        if not np.isnan(z1) and not np.isnan(z2):
            dz = z2 - z1
            if dz > 0.0:
                total_gain += dz
            else:
                total_loss += abs(dz)

    return filled, coverage_status, float(total_gain), float(total_loss)


# ---------------------------------------------------------------------------
# Multi-Scale Slope & Grade Spread Evaluation (Spec v3.1 § 4.4 & § 4.5)
# ---------------------------------------------------------------------------

def multi_scale_along_track_grades(
    distances_m: Sequence[float],
    elevations_m: Sequence[float],
    windows_m: Sequence[float] = (20.0, 50.0, 100.0),
) -> Dict[str, Any]:
    """Compute along-track grade metrics across multi-scale baseline evaluation windows.

    Evaluates rover along-track grade across multiple baseline spans (default: 20 m, 50 m, 100 m)
    and reports the values at each scale along with the spread (max grade minus min grade across scales).

    Args:
        distances_m: Cumulative 1D distance array along the route (strictly ascending).
        elevations_m: Elevation array at each distance sample (metres, NaN allowed).
        windows_m: Sequence of evaluation window spans in metres (default: 20, 50, 100 m).

    Returns:
        Dict containing:
          - "by_window": Mapping of window_m -> {"max_grade_deg": float, "grades": list[float]}
          - "default_max_grade_deg": Max grade at 50 m baseline window (or middle window)
          - "min_scale_grade_deg": Minimum across evaluated scale maxima
          - "max_scale_grade_deg": Maximum across evaluated scale maxima
          - "grade_spread_deg": Difference between max and min scale maxima
    """
    by_window: Dict[float, Dict[str, Any]] = {}
    scale_maxima: list[float] = []

    for w in windows_m:
        max_g, grades = along_track_grades(distances_m, elevations_m, window_m=float(w))
        by_window[float(w)] = {
            "max_grade_deg": float(max_g),
            "grades": grades,
        }
        scale_maxima.append(float(max_g))

    default_window = 50.0 if 50.0 in by_window else float(windows_m[len(windows_m) // 2])
    min_scale = min(scale_maxima) if scale_maxima else 0.0
    max_scale = max(scale_maxima) if scale_maxima else 0.0
    spread = max_scale - min_scale

    return {
        "by_window": by_window,
        "default_max_grade_deg": by_window[default_window]["max_grade_deg"],
        "min_scale_grade_deg": min_scale,
        "max_scale_grade_deg": max_scale,
        "grade_spread_deg": spread,
    }


# ---------------------------------------------------------------------------
# Real DTM Raster Sampling & Analysis Pipeline (Issue #7)
# ---------------------------------------------------------------------------

def sample_route_dtm(
    coords: Sequence[Coordinate],
    dem_path: Optional[str] = None,
    step_m: float = 5.0,
    slope_window_m: float = 50.0,
) -> Optional[Dict[str, Any]]:
    """Sample continuous elevations and calculate terrain metrics from a real DTM raster.

    Args:
        coords: Sequence of >= 2 Coordinate waypoints defining the route.
        dem_path: Optional path to GeoTIFF DTM file. If None, reads $VYOMPATH_DEM_PATH.
        step_m: Sampling interval along the route in metres (default: 5.0 m).
        slope_window_m: Baseline evaluation window for primary max slope in metres (default: 50.0 m).

    Returns:
        Dict containing sampled elevation profile, metrics, DTM metadata and coverage status,
        or None if no DTM is configured, the file does not exist, or cannot be opened as a raster.
    """
    _validate_route(coords)

    if dem_path is None:
        dem_path = os.environ.get("VYOMPATH_DEM_PATH")

    if not dem_path or not os.path.isfile(dem_path):
        return None

    try:
        import rasterio
        import rasterio.windows
        import pyproj
    except ImportError:
        return None

    try:
        with rasterio.open(dem_path) as src:
            if src.count < 1 or src.width < 1 or src.height < 1:
                return None

            tags = src.tags()
            product_id = tags.get("PRODUCT_ID", "HiRISE Stereo DTM").strip('"')
            dtm_source = (
                f"USGS/NASA HiRISE {product_id}"
                if "HiRISE" not in product_id
                else f"USGS/NASA {product_id}"
            )
            dtm_posting_m = round(float(src.res[0]), 4)
            nodata = float(src.nodata) if src.nodata is not None else -3.4028227e+38
            gt = src.transform
            width = src.width
            height = src.height

            # Transformer: transforms (lon, lat) East-positive degrees to raster native projected CRS
            crs_raster = pyproj.CRS.from_wkt(src.crs.to_wkt())
            transformer = pyproj.Transformer.from_crs(
                crs_raster.geodetic_crs, crs_raster, always_xy=True
            )

            # Densify route polyline to uniform step_m
            densified = densify_route(coords, step_m=step_m)
            n_dens = len(densified)

            # Calculate cumulative 2D haversine distances
            dists: list[float] = [0.0]
            for i in range(n_dens - 1):
                d = haversine_m(densified[i], densified[i + 1])
                dists.append(dists[-1] + d)

            # Transform geodetic degrees to native projected coordinates (metres)
            lons = [c.lon for c in densified]
            lats = [c.lat for c in densified]
            xs, ys = transformer.transform(lons, lats)

            # Convert projected metres to floating-point raster pixel coordinates
            cols_f = [(x - gt.c) / gt.a for x in xs]
            rows_f = [(y - gt.f) / gt.e for y in ys]

            inside_mask = [
                0 <= cf < width and 0 <= rf < height
                for cf, rf in zip(cols_f, rows_f)
            ]

            # If entire traverse lies outside the raster bounds
            if not any(inside_mask):
                pts_2d = [(dists[i], float("nan")) for i in range(n_dens)]
                downsampled_pts = lttb_downsample(pts_2d, threshold=500)
                profile = [
                    ElevationPoint(
                        distance_m=round(d, 2),
                        elevation_m=None,
                    )
                    for d, _ in downsampled_pts
                ]
                return {
                    "elevation_profile": profile,
                    "total_gain_m": 0.0,
                    "total_loss_m": 0.0,
                    "max_slope_deg": 0.0,
                    "slope_window_m": slope_window_m,
                    "dtm_source": dtm_source,
                    "dtm_posting_m": dtm_posting_m,
                    "coverage_status": "out_of_bounds",
                    "limitations": [
                        "OUT OF BOUNDS: Route coordinates lie entirely outside the valid HiRISE stereo DTM footprint.",
                        "ELEVATION DATA: Uncovered segments retain null elevation values.",
                        "SCIENCE POIs: POI search is not integrated in this milestone (owner: Dheer). Returned nearby_pois is empty.",
                        "VERTICAL DATUM: Native HiRISE elevations reference the MOLA Areoid equipotential surface.",
                    ],
                }

            # Bounding box for windowed raster read
            valid_c = [cols_f[i] for i in range(n_dens) if inside_mask[i]]
            valid_r = [rows_f[i] for i in range(n_dens) if inside_mask[i]]

            min_c = max(0, int(math.floor(min(valid_c))) - 1)
            max_c = min(width - 1, int(math.ceil(max(valid_c))) + 2)
            min_r = max(0, int(math.floor(min(valid_r))) - 1)
            max_r = min(height - 1, int(math.ceil(max(valid_r))) + 2)

            win_w = max_c - min_c + 1
            win_h = max_r - min_r + 1
            win = rasterio.windows.Window(min_c, min_r, win_w, win_h)
            data_win = src.read(1, window=win)

            # Sample subpixel elevations with 4-neighbor bilinear interpolation
            raw_elevations: list[float] = []
            for cf, rf, ins in zip(cols_f, rows_f, inside_mask):
                if ins and min_c <= cf <= max_c - 1 and min_r <= rf <= max_r - 1:
                    loc_c = cf - min_c
                    loc_r = rf - min_r
                    z = sample_point_bilinear(data_win, loc_c, loc_r, nodata=nodata)
                else:
                    z = float("nan")
                raw_elevations.append(z)

            # Gap processing, coverage classification, and gain/loss accumulation
            filled, status, gain, loss = process_elevation_gaps(
                raw_elevations, step_m=step_m, max_fill_m=15.0
            )

            # Multi-scale slope evaluation at slope_window_m (and 20m, 100m)
            grades_res = multi_scale_along_track_grades(
                dists, filled, windows_m=(20.0, slope_window_m, 100.0)
            )
            max_slope = grades_res["by_window"].get(slope_window_m, {}).get("max_grade_deg", 0.0)
            if math.isnan(max_slope):
                max_slope = 0.0

            # LTTB downsampling to preserve key topological features within 500 samples
            pts_2d = [(dists[i], filled[i]) for i in range(n_dens)]
            downsampled_pts = lttb_downsample(pts_2d, threshold=500)
            profile = [
                ElevationPoint(
                    distance_m=round(d, 2),
                    elevation_m=None if math.isnan(z) else round(float(z), 2),
                )
                for d, z in downsampled_pts
            ]

            limitations: list[str] = [
                f"DTM SAMPLING: Sampled from {dtm_source} ({dtm_posting_m:.4f} m/px posting) using bilinear 4-neighbor interpolation.",
                "VERTICAL DATUM: Native HiRISE elevations reference the MOLA Areoid equipotential surface.",
                "SCIENCE POIs: POI search is not integrated in this milestone (owner: Dheer). Returned nearby_pois is empty.",
            ]
            if status == "partial_gap":
                limitations.append(
                    "PARTIAL COVERAGE: Route traversed NoData areas exceeding 15.0 m gap tolerance; missing segments retain null elevation."
                )
            elif status == "complete":
                limitations.append(
                    "COVERAGE: 100% of route sample points fell within valid DTM stereo elevation data."
                )

            return {
                "elevation_profile": profile,
                "total_gain_m": round(gain, 2),
                "total_loss_m": round(loss, 2),
                "max_slope_deg": round(abs(max_slope), 2),
                "slope_window_m": slope_window_m,
                "dtm_source": dtm_source,
                "dtm_posting_m": dtm_posting_m,
                "coverage_status": status,
                "limitations": limitations,
            }
    except Exception:
        # In case of corrupted raster file or read failure, return None to trigger truthful mock fallback
        return None



