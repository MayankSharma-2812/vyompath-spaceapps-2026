/**
 * marsProjection.ts — Authoritative Mars 2000 Equirectangular Projection Engine
 *
 * Implements the IAU 2000 spherical coordinate system for Mars:
 * - Semi-major / Semi-minor Radius: R = 3,396,190.0 m (IAU 2000 Mars Sphere)
 * - Half World Dimensions:
 *     HX = pi * R = 10,669,445.5540916 m
 *     HY = HX / 2 = 5,334,722.7770458 m
 * - Projected Extent: [-HX, -HY, HX, HY]
 * - Proj4 Definition: +proj=eqc +lat_ts=0 +lat_0=0 +lon_0=0 +R=3396190 +units=m +no_defs
 *
 * Provides high-precision linear forward and unprojection functions bypassing
 * trigonometric round-off and Proj4 pole singularities.
 */

import proj4 from 'proj4';
import { register } from 'ol/proj/proj4';
import { get as getProjection, type Projection } from 'ol/proj';
import type { Extent } from 'ol/extent';
import type { GeodeticCoordinate } from './types';

export const MARS_RADIUS = 3396190;
export const marsRadius = MARS_RADIUS;

export const MARS_HALF_WIDTH = Math.PI * MARS_RADIUS; // 10,669,445.5540916 m
export const MARS_HALF_HEIGHT = MARS_HALF_WIDTH / 2.0; // 5,334,722.7770458 m

export const MARS_EXTENT: Extent = [
  -MARS_HALF_WIDTH,
  -MARS_HALF_HEIGHT,
  MARS_HALF_WIDTH,
  MARS_HALF_HEIGHT,
];
export const marsExtent = MARS_EXTENT;

// Register MARS:2000 Equirectangular projection with Proj4 and OpenLayers
export const MARS_PROJ4_DEF = '+proj=eqc +lat_ts=0 +lat_0=0 +lon_0=0 +R=3396190 +units=m +no_defs';
proj4.defs('MARS:2000', MARS_PROJ4_DEF);
register(proj4);

const proj = getProjection('MARS:2000');
if (!proj) {
  throw new Error('Failed to register or retrieve MARS:2000 projection from OpenLayers.');
}
proj.setExtent(MARS_EXTENT);

export const marsProjection: Projection = proj;

/**
 * Pure linear spherical unprojection from MARS:2000 projected metres to geodetic degrees.
 * Bypasses trigonometric functions and Proj4 pole singularity bugs.
 * Longitude is normalized to [-180, 180] deg E; Latitude clamped to [-90, 90] deg N.
 */
export function toGeodetic(coords: [number, number]): GeodeticCoordinate {
  let lon = (coords[0] / MARS_HALF_WIDTH) * 180.0;
  let lat = (coords[1] / MARS_HALF_HEIGHT) * 90.0;

  // Wrap longitude to [-180, 180]
  lon = ((lon + 180.0) % 360.0 + 360.0) % 360.0 - 180.0;
  // Clamp latitude to [-90, 90]
  lat = Math.max(-90.0, Math.min(90.0, lat));

  return { lon, lat };
}

/**
 * Pure linear forward projection from geodetic degrees to MARS:2000 projected metres.
 */
export function fromGeodetic(lon: number, lat: number): [number, number] {
  const x = (lon / 180.0) * MARS_HALF_WIDTH;
  const y = (lat / 90.0) * MARS_HALF_HEIGHT;
  return [x, y];
}

export default marsProjection;
