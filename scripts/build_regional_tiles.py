#!/usr/bin/env python3
"""VyomPath — Regional Map Tile Generation Engine.

Co-authored by:
  Shyam Sharma (NASA Data & Metadata Lead)
  Pranav Sharma (Terrain Service & Raster Sampling Lead)

Reference:
  Coding Master Manual v3.1, Section 5.4 (Mars 2000 Equirectangular 2x1 Grid)
  Complete Build Timeline v3.1, Section 5.1 & Section 5.5 (Gate G1 / G2)

Grid Specification:
  - Datum: Mars 2000 Sphere (+proj=eqc +lat_ts=0 +lat_0=0 +lon_0=0 +R=3396190 +units=m)
  - Radius: R = 3,396,190.0 m (Identical to backend MARS_RADIUS_M)
  - Half World Dimensions:
      HX = pi * R = 10,669,445.55409 m
      HY = HX / 2 = 5,334,722.77705 m
  - Zoom 0 Layout: 2 columns x 1 row (2x1 aspect ratio)
  - Tile Size: 256 x 256 pixels
  - Zoom 0 Resolution: RES0 = (2 * HX) / 512 = 41,677.52169567 m/pixel
  - Origin: Top-Left (-180° lon, +90° lat), Y grows downward
  - Format: 256 px PNG with transparent NoData (RGBA alpha=0)
"""

from __future__ import annotations

import argparse
import json
import math
import os
import pathlib
import sys
from typing import Any, Dict, List, Optional, Tuple

# Single source of truth radius
MARS_RADIUS_M: float = 3_396_190.0
HX: float = math.pi * MARS_RADIUS_M
HY: float = HX / 2.0
RES0: float = (2.0 * HX) / 512.0  # 41,677.52169567039 m/px


# ---------------------------------------------------------------------------
# Core Geodetic Tile Mathematics
# ---------------------------------------------------------------------------

def tile_index(lon: float, lat: float, z: int) -> Tuple[int, int, int]:
    """Compute (z, tile_x, tile_y) on the shared Mars equirectangular grid.

    Formula from Coding Master Manual v3.1 § 5.4:
        X, Y = radians(lon) * R, radians(lat) * R
        t = 256 * RES0 / (2 ** z)
        tile_x = int((X + HX) // t)
        tile_y = int((HY - Y) // t)

    Args:
        lon: Longitude in degrees [-180.0, 180.0].
        lat: Latitude in planetocentric degrees [-90.0, 90.0].
        z: Zoom level integer (>= 0).

    Returns:
        (z, tile_x, tile_y) coordinates.
    """
    x = math.radians(lon) * MARS_RADIUS_M
    y = math.radians(lat) * MARS_RADIUS_M
    tile_span_m = 256.0 * RES0 / (2.0 ** z)

    # Clamping at boundary extremes
    max_x = (2 ** (z + 1)) - 1
    max_y = (2 ** z) - 1

    tx = int((x + HX) // tile_span_m)
    ty = int((HY - y) // tile_span_m)

    tx = max(0, min(tx, max_x))
    ty = max(0, min(ty, max_y))

    return z, tx, ty


def tile_bounds_projected(z: int, x: int, y: int) -> Tuple[float, float, float, float]:
    """Return projected bounding box in metres: (min_x, min_y, max_x, max_y)."""
    tile_span_m = 256.0 * RES0 / (2.0 ** z)
    min_x = -HX + x * tile_span_m
    max_x = min_x + tile_span_m
    max_y = HY - y * tile_span_m
    min_y = max_y - tile_span_m
    return min_x, min_y, max_x, max_y


def tile_bounds_lonlat(z: int, x: int, y: int) -> Tuple[float, float, float, float]:
    """Return geographic bounding box in degrees: (min_lon, min_lat, max_lon, max_lat)."""
    min_x, min_y, max_x, max_y = tile_bounds_projected(z, x, y)
    min_lon = math.degrees(min_x / MARS_RADIUS_M)
    max_lon = math.degrees(max_x / MARS_RADIUS_M)
    min_lat = math.degrees(min_y / MARS_RADIUS_M)
    max_lat = math.degrees(max_y / MARS_RADIUS_M)
    return min_lon, min_lat, max_lon, max_lat


def get_tile_range_for_bounds(
    min_lon: float, min_lat: float, max_lon: float, max_lat: float, z: int
) -> Tuple[int, int, int, int]:
    """Return (min_x, min_y, max_x, max_y) tile index ranges covering the bounding box."""
    _, min_tx, max_ty = tile_index(min_lon, min_lat, z)
    _, max_tx, min_ty = tile_index(max_lon, max_lat, z)
    return min(min_tx, max_tx), min(min_ty, max_ty), max(min_tx, max_tx), max(min_ty, max_ty)


# ---------------------------------------------------------------------------
# TileJSON Specification Generator (TileJSON 3.0.0)
# ---------------------------------------------------------------------------

def generate_tiles_json(
    name: str,
    description: str,
    version: str,
    min_zoom: int,
    max_zoom: int,
    bounds_lonlat: Tuple[float, float, float, float],
    center_lonlat_zoom: Tuple[float, float, int],
    tiles_url_template: str,
    attribution: str = "NASA/JPL-Caltech/MSSS/USGS/Team NAKSHATRA X",
) -> Dict[str, Any]:
    """Generate TileJSON 3.0.0 metadata dictionary."""
    min_lon, min_lat, max_lon, max_lat = bounds_lonlat
    center_lon, center_lat, center_z = center_lonlat_zoom
    return {
        "tilejson": "3.0.0",
        "name": name,
        "description": description,
        "version": version,
        "attribution": attribution,
        "scheme": "xyz",
        "tiles": [tiles_url_template],
        "minzoom": min_zoom,
        "maxzoom": max_zoom,
        "bounds": [round(min_lon, 6), round(min_lat, 6), round(max_lon, 6), round(max_lat, 6)],
        "center": [round(center_lon, 6), round(center_lat, 6), center_z],
        "format": "png",
    }


# ---------------------------------------------------------------------------
# Test-Pattern Generator (Arya Alignment Tooling)
# ---------------------------------------------------------------------------

def create_test_pattern_png(z: int, x: int, y: int) -> bytes:
    """Generate a diagnostic 256x256 PNG showing tile coordinates and border.

    Falls back to a minimal pure-Python 256x256 RGBA PNG if PIL is not installed.
    """
    try:
        from PIL import Image, ImageDraw

        img = Image.new("RGBA", (256, 256), (20, 20, 30, 200))
        draw = ImageDraw.Draw(img)
        # 1px border
        draw.rectangle([0, 0, 255, 255], outline=(255, 120, 0, 255), width=2)
        # Crosshairs
        draw.line([(0, 128), (256, 128)], fill=(100, 100, 120, 150), width=1)
        draw.line([(128, 0), (128, 256)], fill=(100, 100, 120, 150), width=1)
        # Coordinate labels
        label = f"z={z}\nx={x}\ny={y}"
        draw.text((15, 15), label, fill=(255, 255, 255, 255))
        min_lon, min_lat, max_lon, max_lat = tile_bounds_lonlat(z, x, y)
        coord_text = f"{min_lon:.2f}E, {min_lat:.2f}N"
        draw.text((15, 220), coord_text, fill=(200, 200, 200, 220))

        import io
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()
    except ImportError:
        # Minimal valid 1x1 transparent PNG fallback if Pillow is absent
        import zlib
        import struct

        raw_data = b"\x00" + b"\x80\x20\x00\xFF"  # single pixel
        compressed = zlib.compress(raw_data)
        ihdr = struct.pack(">IIBBBBB", 1, 1, 8, 6, 0, 0, 0)
        png = (
            b"\x89PNG\r\n\x1a\n"
            + struct.pack(">I", 13) + b"IHDR" + ihdr + struct.pack(">I", zlib.crc32(b"IHDR" + ihdr))
            + struct.pack(">I", len(compressed)) + b"IDAT" + compressed + struct.pack(">I", zlib.crc32(b"IDAT" + compressed))
            + struct.pack(">I", 0) + b"IEND" + struct.pack(">I", zlib.crc32(b"IEND"))
        )
        return png


# ---------------------------------------------------------------------------
# CLI Command
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="VyomPath Regional Tile Generator (Mars 2000 Equirectangular Grid)"
    )
    parser.add_argument("--output-dir", default="data/tiles", help="Directory to save tile pyramid")
    parser.add_argument("--min-zoom", type=int, default=12, help="Minimum zoom level")
    parser.add_argument("--max-zoom", type=int, default=15, help="Maximum zoom level")
    parser.add_argument("--test-pattern", action="store_true", help="Generate diagnostic test-pattern tiles")
    parser.add_argument("--dry-run", action="store_true", help="Calculate tile counts without writing files")

    # Bounding box options (defaults to Jezero AOI v2)
    parser.add_argument("--min-lon", type=float, default=77.44, help="Min longitude in degrees")
    parser.add_argument("--max-lon", type=float, default=77.58, help="Max longitude in degrees")
    parser.add_argument("--min-lat", type=float, default=18.36, help="Min latitude in degrees")
    parser.add_argument("--max-lat", type=float, default=18.50, help="Max latitude in degrees")

    args = parser.parse_args()

    print("=================================================================")
    print("VyomPath Regional Tile Generator — MARS:2000 Grid Specification")
    print(f"Radius: {MARS_RADIUS_M:,.1f} m | Aspect: 2x1 | Tile: 256x256 px")
    print(f"Zoom range: z{args.min_zoom} to z{args.max_zoom}")
    print(f"Bounding box: [{args.min_lon}°E, {args.min_lat}°N] to [{args.max_lon}°E, {args.max_lat}°N]")
    print("=================================================================")

    total_tiles = 0
    zoom_stats = {}

    for z in range(args.min_zoom, args.max_zoom + 1):
        min_tx, min_ty, max_tx, max_ty = get_tile_range_for_bounds(
            args.min_lon, args.min_lat, args.max_lon, args.max_lat, z
        )
        count_x = max_tx - min_tx + 1
        count_y = max_ty - min_ty + 1
        z_count = count_x * count_y
        total_tiles += z_count
        zoom_stats[z] = {
            "x_range": (min_tx, max_tx),
            "y_range": (min_ty, max_ty),
            "count": z_count,
        }
        print(f"Zoom {z:2d}: x=[{min_tx}..{max_tx}] ({count_x} cols), y=[{min_ty}..{max_ty}] ({count_y} rows) -> {z_count:5d} tiles")

    print(f"Total tile count: {total_tiles} tiles")

    if args.dry_run:
        print("Dry run complete: no tiles generated.")
        return

    # Write tiles.json
    out_dir = pathlib.Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    center_lon = (args.min_lon + args.max_lon) / 2.0
    center_lat = (args.min_lat + args.max_lat) / 2.0
    tiles_json = generate_tiles_json(
        name="Jezero Crater Regional Display",
        description="Regional display tiles for Jezero Crater on the MARS:2000 Equirectangular 2x1 grid.",
        version="1.0.0",
        min_zoom=args.min_zoom,
        max_zoom=args.max_zoom,
        bounds_lonlat=(args.min_lon, args.min_lat, args.max_lon, args.max_lat),
        center_lonlat_zoom=(center_lon, center_lat, args.min_zoom),
        tiles_url_template="/tiles/jezero_aoi_v2/hillshade/{z}/{x}/{y}.png",
    )
    with open(out_dir / "tiles.json", "w") as f:
        json.dump(tiles_json, f, indent=2)
    print(f"Wrote metadata: {out_dir / 'tiles.json'}")

    if args.test_pattern:
        print("Generating test pattern tiles...")
        generated = 0
        for z, stats in zoom_stats.items():
            min_tx, max_tx = stats["x_range"]
            min_ty, max_ty = stats["y_range"]
            for tx in range(min_tx, max_tx + 1):
                tile_col_dir = out_dir / str(z) / str(tx)
                tile_col_dir.mkdir(parents=True, exist_ok=True)
                for ty in range(min_ty, max_ty + 1):
                    png_bytes = create_test_pattern_png(z, tx, ty)
                    with open(tile_col_dir / f"{ty}.png", "wb") as pf:
                        pf.write(png_bytes)
                    generated += 1
        print(f"Generated {generated} test pattern tiles into {out_dir}")


if __name__ == "__main__":
    main()
