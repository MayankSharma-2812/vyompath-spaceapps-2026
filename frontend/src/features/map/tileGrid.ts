/**
 * tileGrid.ts — 2x1 Equirectangular Tile Grid for Mars 2000
 *
 * Implements the IAU 2000 Equirectangular 2x1 Slippy Map pyramid:
 * - Radius: R = 3,396,190.0 m
 * - Half-width: HX = π * R = 10,669,445.5540916 m
 * - Half-height: HY = HX / 2 = 5,334,722.7770458 m
 * - Aspect Ratio: 2:1 (2 tiles wide x 1 tile high at zoom 0)
 * - Tile Size: 256 x 256 pixels
 * - Base Resolution (z=0): RES0 = (2 * HX) / 512 = 41,677.52169567 m/px
 * - Origin: Top-Left [-HX, HY] (-180° lon, +90° lat)
 */

import TileGrid from 'ol/tilegrid/TileGrid';
import { MARS_HALF_WIDTH, MARS_HALF_HEIGHT, MARS_RADIUS } from './marsProjection';

export const RES0 = (2.0 * MARS_HALF_WIDTH) / 512.0; // 41677.52169567039 m/pixel
export const MAX_ZOOM = 15;

/**
 * Pre-computes the 16 zoom-level resolutions for the 2x1 Mars grid.
 */
export const MARS_RESOLUTIONS: number[] = Array.from(
  { length: MAX_ZOOM + 1 },
  (_, z) => RES0 / Math.pow(2, z)
);

let cachedTileGrid: TileGrid | null = null;

/**
 * Returns the singleton OpenLayers TileGrid instance for the Mars 2000 2x1 grid.
 */
export function getMarsTileGrid(): TileGrid {
  if (!cachedTileGrid) {
    cachedTileGrid = new TileGrid({
      origin: [-MARS_HALF_WIDTH, MARS_HALF_HEIGHT], // Top-Left origin
      resolutions: MARS_RESOLUTIONS,
      tileSize: [256, 256],
      extent: [-MARS_HALF_WIDTH, -MARS_HALF_HEIGHT, MARS_HALF_WIDTH, MARS_HALF_HEIGHT],
    });
  }
  return cachedTileGrid;
}

/**
 * Returns an OpenLayers TileGrid for NASA Mars Trek WMTS base layers (MOLA, Viking)
 * restricted to the layer's native max zoom (e.g. z=7).
 * Capping resolutions at maxZoom allows OpenLayers to smoothly overzoom (stretch)
 * tiles when the map view is at higher zoom levels (e.g. z=8–15).
 */
export function getMarsTrekTileGrid(maxZoom: number = 7): TileGrid {
  return new TileGrid({
    origin: [-MARS_HALF_WIDTH, MARS_HALF_HEIGHT],
    resolutions: MARS_RESOLUTIONS.slice(0, maxZoom + 1),
    tileSize: [256, 256],
    extent: [-MARS_HALF_WIDTH, -MARS_HALF_HEIGHT, MARS_HALF_WIDTH, MARS_HALF_HEIGHT],
  });
}

/**
 * CTX Global Mosaic (Murray Lab / USGS Astrogeology / Esri) 512x512 tile grid.
 * - Spheroid: IAU Mars 2000 Sphere (R = 3,396,190m)
 * - Origin: [-MARS_HALF_WIDTH, MARS_HALF_HEIGHT] (-180° lon, +90° lat)
 * - Level 0: 2 tiles wide x 1 tile high (512x512 px each) -> RES0_CTX = MARS_HALF_WIDTH / 512 = 20,838.76 m/px
 * - Available Levels: 0 through 12
 */
export const RES0_CTX = MARS_HALF_WIDTH / 512.0;
export const CTX_MAX_ZOOM = 12;
export const CTX_RESOLUTIONS: number[] = Array.from(
  { length: CTX_MAX_ZOOM + 1 },
  (_, z) => RES0_CTX / Math.pow(2, z)
);

let cachedCtxTileGrid: TileGrid | null = null;

export function getCtxTileGrid(): TileGrid {
  if (!cachedCtxTileGrid) {
    cachedCtxTileGrid = new TileGrid({
      origin: [-MARS_HALF_WIDTH, MARS_HALF_HEIGHT],
      resolutions: CTX_RESOLUTIONS,
      tileSize: [512, 512],
      extent: [-MARS_HALF_WIDTH, -MARS_HALF_HEIGHT, MARS_HALF_WIDTH, MARS_HALF_HEIGHT],
    });
  }
  return cachedCtxTileGrid;
}

/**
 * Computes the (z, x, y) tile coordinates for a given (lon, lat) at zoom z.
 * Matches Master Coding Guide v3.1 § 5.4:
 *   tile_index(77.45, 18.44, 15) -> [15, 46867, 13027]
 */
export function computeTileIndex(lon: number, lat: number, z: number): [number, number, number] {
  if (z < 0) {
    throw new Error(`Zoom level must be >= 0, got ${z}`);
  }

  const X = (lon * Math.PI / 180.0) * MARS_RADIUS;
  const Y = (lat * Math.PI / 180.0) * MARS_RADIUS;
  const t = 256.0 * RES0 / Math.pow(2, z);

  let x = Math.floor((X + MARS_HALF_WIDTH) / t);
  let y = Math.floor((MARS_HALF_HEIGHT - Y) / t);

  const maxX = Math.pow(2, z + 1) - 1;
  const maxY = Math.pow(2, z) - 1;

  // Clamp edge cases (+180° anti-meridian and -90° South Pole)
  x = Math.max(0, Math.min(x, maxX));
  y = Math.max(0, Math.min(y, maxY));

  return [z, x, y];
}

/**
 * Validates the golden Perseverance landing claim against § 5.4.
 */
export function verifyGoldenAnchor(): boolean {
  const [z, x, y] = computeTileIndex(77.45, 18.44, 15);
  return z === 15 && x === 46867 && y === 13027;
}
