#!/usr/bin/env python3
"""
Regression check: does terrain_rules sample the real DTM the same way your existing fixtures did?

  python tools/compare_fixture.py --fixture tests/fixtures/demo_route_flat_5m.json --dem E:/DATASETS/_phase2/jezero_aoi_v2.tif

It reads each fixture sample point's [lon, lat] and elevation_m, samples the DEM at the same coordinates, and prints
(1) elevation agreement, (2) distance agreement, (3) raw gain/loss recomputed from the fixture, and (4) what the
proposed rules give for the same polyline. It writes nothing. If (1) is off by many metres, the lon/lat -> pixel
mapping differs (the usual cause is the wrong sphere radius, which shifts rows by ~430 px at 18.4 N).
The polyline used for (4) is the fixture's own sample points, a stand-in for the original route.
"""
import argparse
import json
import math
import sys
from pathlib import Path
from typing import Optional

import numpy as np

try:
    import terrain_rules as tr
except ImportError:
    proposals_dir = Path(__file__).resolve().parent.parent / "backend" / "proposals"
    if proposals_dir.exists():
        sys.path.append(str(proposals_dir))
        try:
            import terrain_rules as tr
        except ImportError:
            tr = None
    else:
        tr = None


def make_rasterio_sampler(path: str, band: int = 1, nodata: Optional[float] = None):
    """Create a sampling function that queries a raster DTM using rasterio and pyproj."""
    import rasterio
    from pyproj import CRS, Transformer

    src = rasterio.open(path)
    crs = CRS.from_user_input(src.crs.to_wkt())
    to_raster = Transformer.from_crs(crs.geodetic_crs, crs, always_xy=True)
    nd = src.nodata if nodata is None else nodata
    left, bottom, right, top = src.bounds

    def sampler(lon, lat):
        lon_arr = np.atleast_1d(np.asarray(lon, dtype=float))
        lat_arr = np.atleast_1d(np.asarray(lat, dtype=float))
        x, y = to_raster.transform(lon_arr, lat_arr)
        x = np.atleast_1d(x)
        y = np.atleast_1d(y)
        inside = (x >= left) & (x <= right) & (y >= bottom) & (y <= top)
        out = np.full(len(lon_arr), np.nan)
        if np.any(inside):
            pts = zip(x[inside], y[inside])
            vals = np.array([v[0] for v in src.sample(pts, indexes=band)], dtype=float)
            if nd is not None:
                vals[vals == nd] = np.nan
            vals[~np.isfinite(vals)] = np.nan
            out[inside] = vals
        return out

    return sampler


def _haversine_chainage(coords: np.ndarray, radius_m: float = 3396190.0) -> np.ndarray:
    """Calculate cumulative chainage along lon/lat vertex sequence using Mars sphere radius."""
    n = len(coords)
    dists = np.zeros(n, dtype=float)
    for i in range(1, n):
        lon1, lat1 = math.radians(coords[i - 1, 0]), math.radians(coords[i - 1, 1])
        lon2, lat2 = math.radians(coords[i, 0]), math.radians(coords[i, 1])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = math.sin(dlat / 2.0) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2.0) ** 2
        dists[i] = dists[i - 1] + radius_m * 2.0 * math.atan2(math.sqrt(a), math.sqrt(max(0.0, 1.0 - a)))
    return dists


def compare(fx, sampler, tol=0.01):
    pts = [p for p in fx["sample_points"] if p.get("status", "ok") == "ok"]
    lon = np.array([p["coordinates"][0] for p in pts])
    lat = np.array([p["coordinates"][1] for p in pts])
    z_fx = np.array([p["elevation_m"] for p in pts], float)
    d_fx = np.array([p["cumulative_distance_m"] for p in pts], float)

    out = {"n_points": len(pts)}
    z_new = np.asarray(sampler(lon, lat), float)
    diff = z_new - z_fx
    ok = ~np.isnan(diff)
    out["elevation_nan_count"] = int((~ok).sum())
    out["elevation_max_abs_diff_m"] = float(np.max(np.abs(diff[ok]))) if ok.any() else None
    out["elevation_mean_abs_diff_m"] = float(np.mean(np.abs(diff[ok]))) if ok.any() else None
    out["elevation_points_over_tol"] = int((np.abs(diff[ok]) > tol).sum())

    coords = np.column_stack([lon, lat])
    if tr is not None and hasattr(tr, "vertex_chainage"):
        cum = tr.vertex_chainage(coords)
    else:
        cum = _haversine_chainage(coords)

    out["distance_max_abs_diff_m"] = float(np.max(np.abs(cum - d_fx)))
    out["fixture_total_distance_m"] = fx.get("total_distance_m")
    out["last_sample_distance_m"] = float(d_fx[-1])
    out["polyline_length_m"] = float(cum[-1])

    dz = np.diff(z_fx)
    out["raw_gain_recomputed_m"] = float(dz[dz > 0].sum())
    out["raw_loss_recomputed_m"] = float(-dz[dz < 0].sum())
    m = fx.get("elevation_metrics", {})
    out["raw_gain_in_fixture_m"] = m.get("total_gain_raw_m")
    out["raw_loss_in_fixture_m"] = m.get("total_loss_raw_m")

    if tr is not None and hasattr(tr, "analyze_route"):
        new = tr.analyze_route(coords.tolist(), sampler)
        out["proposed"] = {k: new[k] for k in ("distance_m", "gain_m", "loss_m", "net_change_m",
                                               "max_grade_pct", "coverage_fraction", "seam_crossings")}
    else:
        out["proposed"] = "proposal_module_not_loaded"

    out["fixture_grade_pct"] = m.get("max_along_track_grade_50m_window_pct")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fixture", required=True)
    ap.add_argument("--dem", required=True)
    ap.add_argument("--tol", type=float, default=0.01)
    a = ap.parse_args()
    fx = json.load(open(a.fixture, encoding="utf-8"))
    if tr is not None and hasattr(tr, "make_rasterio_sampler"):
        sampler = tr.make_rasterio_sampler(a.dem)
    else:
        sampler = make_rasterio_sampler(a.dem)
    res = compare(fx, sampler, a.tol)
    print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
