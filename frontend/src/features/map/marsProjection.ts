import proj4 from 'proj4';
import { register } from 'ol/proj/proj4';
import { get as getProjection, type Projection } from 'ol/proj';
import type { Extent } from 'ol/extent';

/**
 * Mars volumetric mean radius in meters (IAU/IAG working group).
 */
export const MARS_RADIUS = 3396190;
export const marsRadius = MARS_RADIUS;

/**
 * Equirectangular projection extent for Mars 2000:
 * [-πR, -πR/2, πR, πR/2]
 */
export const MARS_EXTENT: Extent = [
  -Math.PI * MARS_RADIUS,
  (-Math.PI * MARS_RADIUS) / 2,
  Math.PI * MARS_RADIUS,
  (Math.PI * MARS_RADIUS) / 2,
];
export const marsExtent = MARS_EXTENT;

// 1. Define the Mars 2000 equirectangular sphere with proj4
proj4.defs('MARS:2000', '+proj=eqc +lat_ts=0 +lat_0=0 +lon_0=0 +R=3396190 +units=m +no_defs');

// 2. Register proj4 with OpenLayers
register(proj4);

// 3. Retrieve projection and guard against null
const proj = getProjection('MARS:2000');
if (!proj) {
  throw new Error('Failed to register or retrieve MARS:2000 projection from OpenLayers.');
}

// 4. Explicitly set projection extent
proj.setExtent(MARS_EXTENT);

export const marsProjection: Projection = proj;
export default marsProjection;
