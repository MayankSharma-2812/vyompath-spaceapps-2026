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

export interface RouteGeometry {
  id?: string;
  name?: string;
  coordinates: GeodeticCoordinate[];
  style?: 'route-a' | 'route-b';
}

export interface ElevationProfilePoint {
  distance_m: number;
  elevation_m: number;
}

export interface RouteAnalysisData {
  route_id: string;
  total_distance_m: number;
  elevation_profile: ElevationProfilePoint[];
  total_gain_m: number;
  total_loss_m: number;
  max_slope_deg: number;
  slope_window_m?: number;
  coverage_status: 'complete' | 'partial_gap' | 'out_of_bounds' | 'not_applicable';
  dtm_source: string;
  dtm_posting_m?: number;
  nearby_pois?: any[];
  limitations?: string[];
  analysis_mode?: 'real_dtm' | 'mock';
  is_mock?: boolean;
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
  // Route Drawing & API Overlay Props
  routeA?: RouteGeometry | null;
  routeB?: RouteGeometry | null;
  analysisResponse?: RouteAnalysisData | null;
  isAnalyzing?: boolean;
  analysisError?: string | null;
  onRouteDrawn?: (coordinates: GeodeticCoordinate[]) => void;
  onRouteClear?: () => void;
  // Analytical Overlay & Basemap Callbacks
  onBaseLayerChange?: (layer: BaseLayerId) => void;
  onToggleFootprint?: (visible: boolean) => void;
  onToggleWaypoints?: (visible: boolean) => void;
  onToggleRegionalTiles?: (visible: boolean) => void;
}
