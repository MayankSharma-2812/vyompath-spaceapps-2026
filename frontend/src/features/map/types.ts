/**
 * types.ts — TypeScript Interfaces for Map Features & Planetary Visualization
 */

export interface GeodeticCoordinate {
  lon: number; // Longitude in planetocentric degrees [-180, 180] East-positive
  lat: number; // Latitude in planetocentric degrees [-90, 90] North-positive
}

export interface RoverWaypoint {
  id: string;
  name: string;
  sol: number;
  site?: number;
  drive?: number;
  lon: number;
  lat: number;
  elev_geoid_m?: number;
  inside_footprint: boolean;
  note?: string;
}

export interface GeologicalFeature {
  id: string;
  name: string;
  feature_type: string;
  lon: number;
  lat: number;
  description?: string;
}

export type BaseLayerId = 'mola-colorhillshade' | 'ctx-mosaic' | 'viking-mdim21';

export interface BaseLayerConfig {
  id: BaseLayerId;
  name: string;
  title: string;
  urlTemplate: string;
  attribution: string;
  maxZoom: number;
}

export interface TileGridConfig {
  crs: string;
  radiusMeters: number;
  halfWidthMeters: number;
  halfHeightMeters: number;
  res0MetersPerPx: number;
  tileSizePx: number;
  origin: [number, number]; // Top-left [-HX, HY]
  maxZoom: number;
}

export interface MapCanvasProps {
  className?: string;
  initialCenter?: [number, number]; // [lon, lat] in degrees
  initialZoom?: number;
  activeBaseLayer?: BaseLayerId;
  showRegionalTiles?: boolean;
  showFootprint?: boolean;
  showWaypoints?: boolean;
  selectedSol?: number | null;
  onWaypointSelect?: (waypoint: RoverWaypoint) => void;
  onCoordinateHover?: (coord: GeodeticCoordinate | null) => void;
}
