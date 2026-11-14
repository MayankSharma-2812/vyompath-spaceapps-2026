/**
 * layers.ts — Base Map, Regional Tile Grid, Footprint & Rover Waypoint Layers
 *
 * Implements:
 * - Mars Trek WMTS base layers (MOLA Shaded Relief, CTX Global, Viking MDIM2.1)
 *   with custom tileUrlFunction correcting NASA Trek's {z}/{y}/{x} row/col inversion.
 * - Regional HiRISE DTM tile layer (zooms 12–15) with graceful transparent NoData fallback.
 * - Canonical Jezero DTM vector footprint (gold dashed line).
 * - Mars 2020 Perseverance rover telemetry waypoints with marker decluttering.
 */

import TileLayer from 'ol/layer/Tile';
import VectorLayer from 'ol/layer/Vector';
import XYZ from 'ol/source/XYZ';
import VectorSource from 'ol/source/Vector';
import Feature from 'ol/Feature';
import Polygon from 'ol/geom/Polygon';
import Point from 'ol/geom/Point';
import { Style, Stroke, Fill, Circle as CircleStyle, Text } from 'ol/style';
import type { TileCoord } from 'ol/tilecoord';

import { fromGeodetic } from './marsProjection';
import { getMarsTileGrid } from './tileGrid';
import {
  JEZERO_DTM_FOOTPRINT_COORDINATES,
  ROVER_WAYPOINTS,
} from './waypointData';
import type { BaseLayerId, BaseLayerConfig, RoverWaypoint } from './types';

// Transparent 1x1 PNG for graceful NoData tile fallback
export const EMPTY_TILE_DATA_URI =
  'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=';

export const BASE_LAYER_CONFIGS: Record<BaseLayerId, BaseLayerConfig> = {
  'mola-colorhillshade': {
    id: 'mola-colorhillshade',
    name: 'MOLA Shaded Relief',
    title: 'MGS MOLA Colorized Shaded Relief Global 463m',
    urlTemplate:
      'https://trek.nasa.gov/tiles/Mars/EQ/Mars_MGS_MOLA_ClrShade_merge_global_463m/1.0.0/default/default028mm/{z}/{y}/{x}.jpg',
    attribution: '© NASA / GSFC / JPL Solar System Treks (MOLA)',
    maxZoom: 10,
  },
  'ctx-mosaic': {
    id: 'ctx-mosaic',
    name: 'CTX Visible Mosaic',
    title: 'MRO CTX Global Grayscale Mosaic (~6m)',
    urlTemplate:
      'https://trek.nasa.gov/tiles/Mars/EQ/Mars_MRO_CTX_Mosaic_global_6m/1.0.0/default/default028mm/{z}/{y}/{x}.jpg',
    attribution: '© NASA / JPL-Caltech / MSSS / Murray Lab (CTX)',
    maxZoom: 14,
  },
  'viking-mdim21': {
    id: 'viking-mdim21',
    name: 'Viking MDIM 2.1',
    title: 'Viking Mars Digital Image Mosaic 2.1 (232m)',
    urlTemplate:
      'https://trek.nasa.gov/tiles/Mars/EQ/Mars_Viking_MDIM21_ClrMosaic_global_232m/1.0.0/default/default028mm/{z}/{y}/{x}.jpg',
    attribution: '© USGS Astrogeology Science Center / NASA PDS (Viking)',
    maxZoom: 10,
  },
};

/**
 * Creates an OpenLayers TileLayer for NASA Mars Trek WMTS base maps.
 * Handles row/column inversion: Mars Trek uses {z}/{y}/{x}.jpg where y is row and x is col.
 */
export function createMarsTrekLayer(layerId: BaseLayerId): TileLayer<XYZ> {
  const config = BASE_LAYER_CONFIGS[layerId];
  const tileGrid = getMarsTileGrid();

  const source = new XYZ({
    tileGrid,
    wrapX: false,
    maxZoom: config.maxZoom,
    tileUrlFunction: (tileCoord: TileCoord): string | undefined => {
      const z = tileCoord[0];
      const x = tileCoord[1];
      const y = tileCoord[2];

      if (z > config.maxZoom || z < 0) return undefined;

      // Mars Trek WMTS uses {z}/{y}/{x}.jpg
      return config.urlTemplate
        .replace('{z}', String(z))
        .replace('{y}', String(y))
        .replace('{x}', String(x));
    },
  });

  return new TileLayer({
    source,
    properties: { id: layerId, title: config.title },
  });
}

/**
 * Creates a regional tile layer for high-resolution Jezero HiRISE DTM tiles (zooms 12–15).
 * Falls back safely to empty transparent tiles if offline tile bundles are not staged on disk.
 */
export function createRegionalTileLayer(): TileLayer<XYZ> {
  const tileGrid = getMarsTileGrid();

  const source = new XYZ({
    tileGrid,
    wrapX: false,
    minZoom: 12,
    maxZoom: 15,
    tileUrlFunction: (tileCoord: TileCoord): string | undefined => {
      const z = tileCoord[0];
      const x = tileCoord[1];
      const y = tileCoord[2];

      if (z < 12 || z > 15) return undefined;

      // Client request URL scheme from integration contract
      return `/tiles/jezero_aoi_v2/ortho/${z}/${x}/${y}.png`;
    },
  });

  return new TileLayer({
    source,
    properties: { id: 'regional-jezero-dtm', title: 'HiRISE Regional DTM Tiles' },
    zIndex: 5,
  });
}

/**
 * Creates a vector layer rendering the canonical 98-vertex Jezero DTM boundary footprint.
 * Styled with a distinct gold dashed border (#eab308) and 8% amber fill.
 */
export function createFootprintLayer(): VectorLayer<VectorSource> {
  const projectedCoords = JEZERO_DTM_FOOTPRINT_COORDINATES.map(([lon, lat]) =>
    fromGeodetic(lon, lat)
  );

  const polygon = new Polygon([projectedCoords]);
  const feature = new Feature({
    geometry: polygon,
    name: 'Jezero HiRISE Stereo DTM Analytical Boundary (63.16% Coverage)',
  });

  const vectorSource = new VectorSource({
    features: [feature],
  });

  return new VectorLayer({
    source: vectorSource,
    properties: { id: 'dtm-footprint' },
    zIndex: 10,
    style: new Style({
      stroke: new Stroke({
        color: '#eab308', // Gold / Amber
        width: 2.5,
        lineDash: [6, 4],
      }),
      fill: new Fill({
        color: 'rgba(234, 179, 8, 0.08)',
      }),
    }),
  });
}

/**
 * Creates a vector layer for Perseverance rover waypoints (Sols 383–387).
 * Uses OpenLayers decluttering and vertical label offsets to prevent label collision
 * between Sols 384 and 385 (separated by 13.56m).
 */
export function createWaypointLayer(): VectorLayer<VectorSource> {
  const features = ROVER_WAYPOINTS.map((wp) => {
    const coords = fromGeodetic(wp.lon, wp.lat);
    const feature = new Feature({
      geometry: new Point(coords),
      waypoint: wp,
    });
    return feature;
  });

  const vectorSource = new VectorSource({ features });

  return new VectorLayer({
    source: vectorSource,
    properties: { id: 'rover-waypoints' },
    zIndex: 20,
    declutter: true, // Prevents label collision in crowded clusters
    style: (feature) => {
      const wp = feature.get('waypoint') as RoverWaypoint;
      const isOffsetSol385 = wp.sol === 385;
      const inFootprint = wp.inside_footprint;

      return new Style({
        image: new CircleStyle({
          radius: inFootprint ? 6 : 4,
          fill: new Fill({
            color: inFootprint ? '#06b6d4' : '#64748b', // Cyan for inside, slate for outside
          }),
          stroke: new Stroke({
            color: '#ffffff',
            width: 2,
          }),
        }),
        text: new Text({
          text: `Sol ${wp.sol}`,
          font: 'bold 11px Inter, sans-serif',
          offsetY: isOffsetSol385 ? 18 : -18, // Offset Sol 385 downward to prevent collision with Sol 384
          fill: new Fill({ color: inFootprint ? '#a5f3fc' : '#cbd5e1' }),
          stroke: new Stroke({ color: '#0f172a', width: 3 }),
        }),
      });
    },
  });
}
