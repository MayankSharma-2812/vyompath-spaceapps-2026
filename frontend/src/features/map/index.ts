/**
 * index.ts — Public API for Map Visualization Feature
 */

export { MapCanvas, default } from './MapCanvas';
export {
  marsProjection,
  MARS_RADIUS,
  marsRadius,
  MARS_EXTENT,
  marsExtent,
  MARS_HALF_WIDTH,
  MARS_HALF_HEIGHT,
  toGeodetic,
  fromGeodetic,
} from './marsProjection';
export {
  getMarsTileGrid,
  computeTileIndex,
  verifyGoldenAnchor,
  RES0,
  MAX_ZOOM,
} from './tileGrid';
export {
  BASE_LAYER_CONFIGS,
  createMarsTrekLayer,
  createRegionalTileLayer,
  createFootprintLayer,
  createWaypointLayer,
} from './layers';
export {
  createRouteLayer,
  updateRouteSource,
} from './routeLayer';
export {
  setupRouteDrawing,
  type RouteDrawingController,
  type RouteDrawingOptions,
} from './routeInteraction';
export {
  JEZERO_CENTER,
  JEZERO_DTM_FOOTPRINT_COORDINATES,
  ROVER_WAYPOINTS,
  PERSEVERANCE_REFERENCE_WAYPOINTS,
  GEOLOGICAL_EMPTY_STATE_MESSAGE,
} from './waypointData';
export type {
  GeodeticCoordinate,
  RoverWaypoint,
  GeologicalFeature,
  BaseLayerId,
  BaseLayerConfig,
  TileGridConfig,
  RouteGeometry,
  RouteAnalysisData,
  ElevationProfilePoint,
  MapCanvasProps,
} from './types';
