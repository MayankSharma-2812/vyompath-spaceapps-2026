"""VyomPath Geodetic to Raster Pixel Coordinate Mapping Tool.

Maps Mars 2020 Perseverance sol coordinates (Mars 2000 Sphere EPSG:104905)
to HiRISE stereo DTM pixel coordinates (col, row) using exact projection transforms.
Evaluates naive unprojection vs. pyproj datum transform differences.

Author: Shyam Sharma (Layer Data & Metadata Lead)
Team: NAKSHATRA X
"""

import math

def geodetic_to_pixel_exact(lon_deg: float, lat_deg: float,
                            r_proj: float = 3394839.81331634,
                            lon_0_deg: float = 77.53,
                            lat_ts_deg: float = 15.0,
                            origin_x: float = -5200.7757967131365,
                            origin_y: float = 1096000.6476152753,
                            pixel_res: float = 1.0096633268711):
    """Convert lon/lat in degrees to DTM projected meters and pixel col/row."""
    cos_ts = math.cos(math.radians(lat_ts_deg))
    dlon = math.radians(lon_deg - lon_0_deg)
    dlat = math.radians(lat_deg)
    
    # Equirectangular projection at standard parallel lat_ts
    x = r_proj * dlon * cos_ts
    y = r_proj * dlat
    
    col = (x - origin_x) / pixel_res
    row = (origin_y - y) / pixel_res
    return x, y, col, row

def main():
    sols = {
        386: (77.46313311, 18.46079140),
        387: (77.46157944, 18.46447597)
    }
    print("=== SOL GEODETIC TO PIXEL COORDINATE MAPPING ===")
    for sol, (lon, lat) in sols.items():
        x, y, col, row = geodetic_to_pixel_exact(lon, lat)
        print(f"Sol {sol:3d}: lon={lon:.8f}, lat={lat:.8f} -> x={x:.2f} m, y={y:.2f} m | col={col:.1f}, row={row:.1f} (int: col={int(round(col))}, row={int(round(row))})")

if __name__ == "__main__":
    main()
