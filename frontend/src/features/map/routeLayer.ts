/**
 * routeLayer.ts — Route A, Route B and Start/End Pin Vector Layer Styling
 *
 * Implements:
 * - Route A: Solid Blue (#2563eb), 3.5px width with 1.5px dark casing (#0f172a).
 * - Route B: Dashed Amber (#f59e0b, [8, 6] pattern), 3.5px width with 1.5px dark casing.
 * - Start Point Marker: Emerald (#22c55e) circle with white border and "START" badge.
 * - End Point Marker: Rose (#ef4444) circle with white border and "END" badge.
 * - Coordinates converted from geodetic degrees to MARS:2000 projected metres.
 */

import VectorLayer from 'ol/layer/Vector';
import VectorSource from 'ol/source/Vector';
import Feature from 'ol/Feature';
import LineString from 'ol/geom/LineString';
import Point from 'ol/geom/Point';
import { Style, Stroke, Fill, Circle as CircleStyle, Text } from 'ol/style';

import { fromGeodetic } from './marsProjection';
import type { RouteGeometry, GeodeticCoordinate } from './types';

/**
 * Creates styles for route paths with dark high-contrast casing.
 */
function createRouteStyles(styleType: 'route-a' | 'route-b' | 'drawn') {
  const isRouteB = styleType === 'route-b';
  const color = isRouteB ? '#f59e0b' : '#2563eb'; // Amber for B, Blue for A/drawn
  const lineDash = isRouteB ? [8, 6] : undefined;

  return [
    // Outer casing for high contrast on Mars terrain
    new Style({
      stroke: new Stroke({
        color: '#0f172a',
        width: 6,
        lineCap: 'round',
        lineJoin: 'round',
      }),
    }),
    // Main inner stroke
    new Style({
      stroke: new Stroke({
        color,
        width: 3.5,
        lineCap: 'round',
        lineJoin: 'round',
        lineDash,
      }),
    }),
  ];
}

/**
 * Creates styles for Start / End point markers.
 */
function createPinStyle(type: 'START' | 'END') {
  const isStart = type === 'START';
  const color = isStart ? '#22c55e' : '#ef4444'; // Emerald / Rose

  return new Style({
    image: new CircleStyle({
      radius: 7,
      fill: new Fill({ color }),
      stroke: new Stroke({ color: '#ffffff', width: 2.5 }),
    }),
    text: new Text({
      text: type,
      font: 'bold 10px Inter, sans-serif',
      offsetY: isStart ? -16 : 16,
      fill: new Fill({ color: isStart ? '#bbf7d0' : '#fecdd3' }),
      stroke: new Stroke({ color: '#0f172a', width: 3 }),
    }),
  });
}

/**
 * Creates an empty vector layer dedicated to route paths and markers.
 */
export function createRouteLayer(): VectorLayer<VectorSource> {
  const source = new VectorSource();
  return new VectorLayer({
    source,
    properties: { id: 'route-layer' },
    zIndex: 30, // Above waypoints and footprint
  });
}

/**
 * Updates features on the route vector source based on active routes.
 */
export function updateRouteSource(
  source: VectorSource,
  routeA?: RouteGeometry | null,
  routeB?: RouteGeometry | null,
  drawnCoords?: GeodeticCoordinate[] | null
): void {
  source.clear();

  const addRouteFeature = (
    coords: GeodeticCoordinate[],
    styleType: 'route-a' | 'route-b' | 'drawn'
  ) => {
    if (!coords || coords.length < 2) return;

    const projectedCoords = coords.map((c) => fromGeodetic(c.lon, c.lat));
    const lineFeature = new Feature({
      geometry: new LineString(projectedCoords),
    });
    lineFeature.setStyle(createRouteStyles(styleType));
    source.addFeature(lineFeature);

    // Start Pin
    const startPt = projectedCoords[0];
    const startFeature = new Feature({ geometry: new Point(startPt) });
    startFeature.setStyle(createPinStyle('START'));
    source.addFeature(startFeature);

    // End Pin
    const endPt = projectedCoords[projectedCoords.length - 1];
    const endFeature = new Feature({ geometry: new Point(endPt) });
    endFeature.setStyle(createPinStyle('END'));
    source.addFeature(endFeature);
  };

  // Add Route A
  if (routeA && routeA.coordinates && routeA.coordinates.length >= 2) {
    addRouteFeature(routeA.coordinates, routeA.style || 'route-a');
  }

  // Add Route B
  if (routeB && routeB.coordinates && routeB.coordinates.length >= 2) {
    addRouteFeature(routeB.coordinates, routeB.style || 'route-b');
  }

  // Add user drawn route if not already included in Route A
  if (drawnCoords && drawnCoords.length >= 2 && (!routeA || routeA.coordinates.length === 0)) {
    addRouteFeature(drawnCoords, 'drawn');
  }
}
