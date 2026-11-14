#!/usr/bin/env python3
"""
Offline checks that validate_data.py does not make. Every POI must be inside a VALID-DATA footprint
(not just a bounding box), have a usable source, and sensible text.

  # authoritative: containment in the exact valid-pixel footprints (Decision 39), one or more
  python validate_poi_aoi.py data/science_points.json ^
      --footprint jezero_aoi_v2=PATH\\jezero_aoi_v2_valid_footprint.geojson ^
      --footprint jezero=PATH\\jezero_valid_footprint.geojson ^
      --footprint syrtis=PATH\\syrtis_valid_footprint.geojson

  # also check a demo route (lon,lat;lon,lat;...) stays inside a footprint along its whole length
  python validate_poi_aoi.py data/science_points.json --footprint jezero_aoi_v2=... ^
      --route "77.51,18.44;77.56,18.47"

  # coarse fallback when no footprint is given, and optional per-point DTM pixel check
  python validate_poi_aoi.py data/science_points.json --bbox 77.4391 18.3119 77.5981 18.4975 --dtm X.tif

Use *_valid_footprint.geojson, never the simplified *_2m files (they leak NoData and must not be safety masks).
Exit code 1 on any ERROR. It cannot tell whether a citation is TRUE: open each source link and DOI yourself.
"""
import argparse
import json
import re
import sys
from urllib.parse import urlparse

DEFAULT_BBOX = (77.4391, 18.3119, 77.5981, 18.4975)   # matches gdalinfo corners of jezero_aoi_v2.tif


# ------------------------------------------------------------------ geometry ----
def load_footprint(path):
    g = json.load(open(path, encoding="utf-8"))
    polys = []

    def walk(o):
        t = o.get("type")
        if t == "FeatureCollection":
            for f in o["features"]:
                walk(f)
        elif t == "Feature":
            walk(o["geometry"])
        elif t == "GeometryCollection":
            for x in o["geometries"]:
                walk(x)
        elif t == "Polygon":
            polys.append(o["coordinates"])
        elif t == "MultiPolygon":
            polys.extend(o["coordinates"])

    walk(g)
    return polys


def _in_ring(x, y, ring):
    inside, j = False, len(ring) - 1
    for i in range(len(ring)):
        xi, yi, xj, yj = ring[i][0], ring[i][1], ring[j][0], ring[j][1]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
            inside = not inside
        j = i
    return inside


def contains(polys, x, y):
    return any(_in_ring(x, y, p[0]) and not any(_in_ring(x, y, h) for h in p[1:]) for p in polys)


def looks_like_degrees(polys):
    return all(abs(c[0]) <= 360 and abs(c[1]) <= 90 for p in polys for c in p[0])


def route_inside(points, polys, n=200):
    """Walk every segment; return (fraction inside, first exit as (lon, lat) or None)."""
    total = inside = 0
    first_exit = None
    for (x0, y0), (x1, y1) in zip(points[:-1], points[1:]):
        for k in range(n + 1):
            t = k / n
            x, y = x0 + t * (x1 - x0), y0 + t * (y1 - y0)
            total += 1
            if contains(polys, x, y):
                inside += 1
            elif first_exit is None:
                first_exit = (round(x, 5), round(y, 5))
    return inside / max(total, 1), first_exit


# ------------------------------------------------------------------- POIs ----
def load_points(path):
    data = json.load(open(path, encoding="utf-8"))
    if isinstance(data, dict):
        data = data.get("points") or data.get("features") or data.get("pois") or []
    out = []
    for item in data:
        if isinstance(item, dict) and item.get("type") == "Feature":
            p = dict(item.get("properties", {}))
            p["coordinates"] = item.get("geometry", {}).get("coordinates")
            out.append(p)
        else:
            out.append(item)
    return out


def lonlat(p):
    c = p.get("coordinates")
    if isinstance(c, (list, tuple)) and len(c) >= 2:
        return float(c[0]), float(c[1])
    if "lon" in p and "lat" in p:
        return float(p["lon"]), float(p["lat"])
    return None


def source_of(p):
    for k in ("source_url", "url", "citation_url", "source", "citation"):
        if p.get(k):
            return p[k]
    return None


def check(points, bbox=None, dtm=None, footprints=None):
    errors, warnings, report = [], [], []
    footprints = footprints or {}
    seen = set()
    sampler = None
    if dtm:
        try:
            from terrain_rules import make_rasterio_sampler
            sampler = make_rasterio_sampler(dtm)
        except Exception as e:                                  # noqa: BLE001
            warnings.append(f"DTM pixel check skipped ({e!r})")
    for name_, polys in footprints.items():
        if not looks_like_degrees(polys):
            errors.append(f"footprint '{name_}' is not in lon/lat degrees; reproject it first")
    for i, p in enumerate(points):
        name = p.get("id") or p.get("name") or f"#{i}"
        if name in seen:
            errors.append(f"{name}: duplicate id/name")
        seen.add(name)
        ll = lonlat(p)
        if ll is None:
            errors.append(f"{name}: no coordinates")
            continue
        lon, lat = ll
        if not (-180 <= lon < 180 and -90 <= lat <= 90):
            errors.append(f"{name}: coordinates out of range ({lon}, {lat})")
            continue
        if footprints:
            hit = [n for n, polys in footprints.items() if contains(polys, lon, lat)]
            report.append(f"{name}: inside {hit if hit else 'NONE'}")
            if not hit:
                errors.append(f"{name}: ({lon}, {lat}) is outside every valid-data footprint given")
        elif bbox and not (bbox[0] <= lon <= bbox[2] and bbox[1] <= lat <= bbox[3]):
            errors.append(f"{name}: ({lon}, {lat}) is OUTSIDE the AOI bbox {bbox}")
        src = source_of(p)
        if not src:
            errors.append(f"{name}: no source/citation")
        elif str(src).startswith("http"):
            if urlparse(str(src)).scheme != "https":
                errors.append(f"{name}: source URL is not https")
        else:
            warnings.append(f"{name}: source is text, not a URL; add a link someone can open")
        cit = str(p.get("citation", ""))
        if len(re.findall(r"et al", cit)) > 1:
            warnings.append(f"{name}: citation has more than one 'et al' (garbled?): {cit[:70]}...")
        if re.search(r"[A-Z]{2}[a-z][A-Z]", str(p.get("name", ""))):
            warnings.append(f"{name}: name looks garbled: {p.get('name')!r}")
        if not p.get("kind") and not p.get("type"):
            warnings.append(f"{name}: no kind (science target vs rover waypoint vs landmark)")
        if sampler is not None:
            import numpy as np
            z = sampler(np.array([lon]), np.array([lat]))[0]
            if np.isnan(z):
                errors.append(f"{name}: no valid DTM pixel at ({lon}, {lat})")
    return errors, warnings, report


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("points")
    ap.add_argument("--bbox", nargs=4, type=float, default=None,
                    metavar=("MINLON", "MINLAT", "MAXLON", "MAXLAT"))
    ap.add_argument("--footprint", action="append", default=[], metavar="NAME=PATH")
    ap.add_argument("--route", help='"lon,lat;lon,lat;..." checked along every segment')
    ap.add_argument("--dtm")
    a = ap.parse_args()

    fps = {}
    for spec in a.footprint:
        name, _, path = spec.partition("=")
        if "simplified" in path.lower() or "_2m" in path.lower():
            print(f"WARN  '{path}' looks like a simplified boundary; use the *_valid_footprint.geojson")
        fps[name] = load_footprint(path)
    bbox = tuple(a.bbox) if a.bbox else (None if fps else DEFAULT_BBOX)

    pts = load_points(a.points)
    errors, warnings, report = check(pts, bbox, a.dtm, fps)
    print(f"{len(pts)} points checked")
    for r in report:
        print("INFO ", r)
    if a.route:
        route = [tuple(float(v) for v in s.split(",")) for s in a.route.split(";")]
        for name, polys in fps.items():
            frac, exit_pt = route_inside(route, polys)
            msg = f"route inside '{name}': {frac * 100:.1f}%" + (f", first exit near {exit_pt}" if exit_pt else "")
            print("INFO ", msg)
        if fps and not any(route_inside(route, polys)[0] == 1.0 for polys in fps.values()):
            errors.append("route is not fully inside any single footprint given")
    for w in warnings:
        print("WARN ", w)
    for e in errors:
        print("ERROR", e)
    print("FAIL" if errors else "OK (offline checks only; sources and citations NOT verified)")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
