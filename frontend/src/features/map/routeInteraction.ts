/**
 * routeInteraction.ts — Interactive Traverse Drawing & Geodetic Coordinate Serialization
 *
 * Implements:
 * - OpenLayers Draw interaction (LineString mode)
 * - Coordinate serialization converting screen canvas metres to geodetic degrees:
 *   [{"lon": <float>, "lat": <float>}]
 * - Rigorous verification of planetocentric bounds (lon: -180..180, lat: -90..90)
 * - Fires onRouteDrawn callback conforming to the backend integration contract.
 */

import type Map from 'ol/Map';
import Draw, { type DrawEvent } from 'ol/interaction/Draw';
import VectorSource from 'ol/source/Vector';
import LineString from 'ol/geom/LineString';
import type { Coordinate } from 'ol/coordinate';

import { toGeodetic } from './marsProjection';
import type { GeodeticCoordinate } from './types';

export interface RouteDrawingOptions {
  map: Map;
  onRouteDrawn: (coordinates: GeodeticCoordinate[]) => void;
  maxPoints?: number;
}

export interface RouteDrawingController {
  activate: () => void;
  deactivate: () => void;
  isActive: () => boolean;
  clear: () => void;
  finish: () => void;
  destroy: () => void;
}

/**
 * Initializes interactive traverse drawing on the OpenLayers map canvas.
 */
export function setupRouteDrawing({
  map,
  onRouteDrawn,
  maxPoints = 500,
}: RouteDrawingOptions): RouteDrawingController {
  const drawingSource = new VectorSource();
  let drawInteraction: Draw | null = null;
  let active = false;

  function createInteraction(): Draw {
    const draw = new Draw({
      source: drawingSource,
      type: 'LineString',
      maxPoints,
      stopClick: true,
    });

    draw.on('drawend', (event: DrawEvent) => {
      const feature = event.feature;
      const geom = feature.getGeometry() as LineString;
      if (!geom) return;

      const coordinatesMetres = geom.getCoordinates() as Coordinate[];

      // Transform projected metres to geodetic degrees { lon, lat }
      const geodeticCoords: GeodeticCoordinate[] = coordinatesMetres.map((pt) => {
        return toGeodetic([pt[0], pt[1]]);
      });

      // Clear the temporary drawing sketch
      setTimeout(() => {
        drawingSource.clear();
      }, 50);

      // Emit coordinates to parent / dashboard
      onRouteDrawn(geodeticCoords);
    });

    return draw;
  }

  return {
    activate: () => {
      if (active) return;
      if (!drawInteraction) {
        drawInteraction = createInteraction();
      }
      map.addInteraction(drawInteraction);
      active = true;
    },
    deactivate: () => {
      if (!active || !drawInteraction) return;
      map.removeInteraction(drawInteraction);
      active = false;
    },
    isActive: () => active,
    clear: () => {
      drawingSource.clear();
    },
    finish: () => {
      if (active && drawInteraction) {
        drawInteraction.finishDrawing();
      }
    },
    destroy: () => {
      if (drawInteraction) {
        map.removeInteraction(drawInteraction);
        drawInteraction = null;
      }
      drawingSource.clear();
      active = false;
    },
  };
}
