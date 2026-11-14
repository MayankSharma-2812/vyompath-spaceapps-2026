/**
 * MapCanvas.tsx — Primary Interactive OpenLayers Canvas for Mars Visualization
 *
 * Implements:
 * - MARS:2000 Equirectangular Projection Engine (R = 3,396,190 m)
 * - 2x1 Slippy Map Tile Grid (RES0 = 41677.52 m/px, Top-Left Origin)
 * - Mars Trek WMTS Base Layers (MOLA Shaded Relief, CTX Mosaic, Viking MDIM2.1)
 * - Regional HiRISE DTM Tile Layer with transparent NoData fallback
 * - Canonical Jezero DTM Vector Boundary (98 vertices from jezero_dtm.geojson)
 * - Mars 2020 Perseverance Rover Waypoints (Sols 383–387) with decluttering & popup
 * - Interactive Route Drawing with Geodetic Degree Serialization [{"lon": ..., "lat": ...}]
 * - Dual Route A (Solid Blue) and Route B (Dashed Amber) Visualization
 * - API Response Overlays (Distance, Elevation Gain/Loss, Slope, Coverage Status)
 * - Transparent Truthful Mock Mode Indicator Banner
 * - StrictMode lifecycle isolation & ResizeObserver handling
 */

import React, { useEffect, useRef, useState, useCallback } from 'react';
import 'ol/ol.css';
import Map from 'ol/Map';
import View from 'ol/View';
import type { Coordinate } from 'ol/coordinate';
import type BaseLayer from 'ol/layer/Base';
import type VectorLayer from 'ol/layer/Vector';
import type VectorSource from 'ol/source/Vector';

import {
  marsProjection,
  MARS_EXTENT,
  toGeodetic,
  fromGeodetic,
} from './marsProjection';
import {
  createMarsTrekLayer,
  createRegionalTileLayer,
  createFootprintLayer,
  createWaypointLayer,
  BASE_LAYER_CONFIGS,
} from './layers';
import {
  createRouteLayer,
  updateRouteSource,
} from './routeLayer';
import {
  setupRouteDrawing,
  type RouteDrawingController,
} from './routeInteraction';
import {
  JEZERO_CENTER,
  GEOLOGICAL_EMPTY_STATE_MESSAGE,
} from './waypointData';
import type {
  MapCanvasProps,
  BaseLayerId,
  RoverWaypoint,
  GeodeticCoordinate,
} from './types';

export const MapCanvas: React.FC<MapCanvasProps> = ({
  className = '',
  initialCenter = JEZERO_CENTER,
  initialZoom = 12,
  activeBaseLayer = 'mola-colorhillshade',
  showRegionalTiles = true,
  showFootprint = true,
  showWaypoints = true,
  routeA = null,
  routeB = null,
  analysisResponse = null,
  isAnalyzing = false,
  analysisError = null,
  onRouteDrawn,
  onRouteClear,
  onWaypointSelect,
  onCoordinateHover,
}) => {
  const mapElementRef = useRef<HTMLDivElement | null>(null);
  const mapInstanceRef = useRef<Map | null>(null);
  const drawingControllerRef = useRef<RouteDrawingController | null>(null);

  // Callback refs to prevent stale closures in mount-only useEffect listeners
  const onCoordinateHoverRef = useRef(onCoordinateHover);
  const onWaypointSelectRef = useRef(onWaypointSelect);

  useEffect(() => {
    onCoordinateHoverRef.current = onCoordinateHover;
  }, [onCoordinateHover]);

  useEffect(() => {
    onWaypointSelectRef.current = onWaypointSelect;
  }, [onWaypointSelect]);

  // Layer references
  const baseLayersRef = useRef<Record<BaseLayerId, BaseLayer | null>>({
    'mola-colorhillshade': null,
    'ctx-mosaic': null,
    'viking-mdim21': null,
  });
  const regionalLayerRef = useRef<BaseLayer | null>(null);
  const footprintLayerRef = useRef<BaseLayer | null>(null);
  const waypointLayerRef = useRef<BaseLayer | null>(null);
  const routeLayerRef = useRef<VectorLayer<VectorSource> | null>(null);

  // Component state
  const [selectedBaseLayer, setSelectedBaseLayer] = useState<BaseLayerId>(activeBaseLayer);
  const [isRegionalVisible, setIsRegionalVisible] = useState(showRegionalTiles);
  const [isFootprintVisible, setIsFootprintVisible] = useState(showFootprint);
  const [isWaypointsVisible, setIsWaypointsVisible] = useState(showWaypoints);
  const [cursorCoords, setCursorCoords] = useState<GeodeticCoordinate | null>(null);
  const [selectedWaypoint, setSelectedWaypoint] = useState<RoverWaypoint | null>(null);
  const [showDisclaimer, setShowDisclaimer] = useState(true);
  const [isLegendOpen, setIsLegendOpen] = useState(true);
  const [isDrawingMode, setIsDrawingMode] = useState(false);
  const [drawnCoordinates, setDrawnCoordinates] = useState<GeodeticCoordinate[]>([]);

  // Switch base layer
  const handleBaseLayerSelect = useCallback((layerId: BaseLayerId) => {
    setSelectedBaseLayer(layerId);
    (Object.keys(baseLayersRef.current) as BaseLayerId[]).forEach((id) => {
      const layer = baseLayersRef.current[id];
      if (layer) {
        layer.setVisible(id === layerId);
      }
    });
  }, []);

  // Internal route drawn handler
  const handleInternalRouteDrawn = useCallback(
    (coords: GeodeticCoordinate[]) => {
      setDrawnCoordinates(coords);
      setIsDrawingMode(false);
      if (drawingControllerRef.current) {
        drawingControllerRef.current.deactivate();
      }
      if (onRouteDrawn) {
        onRouteDrawn(coords);
      }
    },
    [onRouteDrawn]
  );

  // Toggle route drawing mode
  const toggleDrawingMode = useCallback(() => {
    if (!drawingControllerRef.current) return;
    if (isDrawingMode) {
      drawingControllerRef.current.deactivate();
      setIsDrawingMode(false);
    } else {
      drawingControllerRef.current.activate();
      setIsDrawingMode(true);
    }
  }, [isDrawingMode]);

  // Clear routes
  const handleClearRoutes = useCallback(() => {
    setDrawnCoordinates([]);
    if (drawingControllerRef.current) {
      drawingControllerRef.current.clear();
      drawingControllerRef.current.deactivate();
    }
    setIsDrawingMode(false);
    if (routeLayerRef.current) {
      routeLayerRef.current.getSource()?.clear();
    }
    if (onRouteClear) {
      onRouteClear();
    }
  }, [onRouteClear]);

  // Initialize Map
  useEffect(() => {
    if (!mapElementRef.current) return;

    // Create Base Layers
    const molaLayer = createMarsTrekLayer('mola-colorhillshade');
    const ctxLayer = createMarsTrekLayer('ctx-mosaic');
    const vikingLayer = createMarsTrekLayer('viking-mdim21');

    baseLayersRef.current['mola-colorhillshade'] = molaLayer;
    baseLayersRef.current['ctx-mosaic'] = ctxLayer;
    baseLayersRef.current['viking-mdim21'] = vikingLayer;

    // Visibility defaults
    molaLayer.setVisible(selectedBaseLayer === 'mola-colorhillshade');
    ctxLayer.setVisible(selectedBaseLayer === 'ctx-mosaic');
    vikingLayer.setVisible(selectedBaseLayer === 'viking-mdim21');

    // Regional DTM tile layer
    const regionalLayer = createRegionalTileLayer();
    regionalLayer.setVisible(isRegionalVisible);
    regionalLayerRef.current = regionalLayer;

    // Footprint Layer
    const footprintLayer = createFootprintLayer();
    footprintLayer.setVisible(isFootprintVisible);
    footprintLayerRef.current = footprintLayer;

    // Waypoint Layer
    const waypointLayer = createWaypointLayer();
    waypointLayer.setVisible(isWaypointsVisible);
    waypointLayerRef.current = waypointLayer;

    // Route Layer
    const routeLayer = createRouteLayer();
    routeLayerRef.current = routeLayer;

    // Projected center
    const centerMetres = fromGeodetic(initialCenter[0], initialCenter[1]);

    const map = new Map({
      target: mapElementRef.current,
      layers: [
        molaLayer,
        ctxLayer,
        vikingLayer,
        regionalLayer,
        footprintLayer,
        waypointLayer,
        routeLayer,
      ],
      view: new View({
        projection: marsProjection,
        center: centerMetres,
        zoom: initialZoom,
        minZoom: 1,
        maxZoom: 15,
        extent: MARS_EXTENT,
      }),
      controls: [], // Clean minimalist UI
    });

    mapInstanceRef.current = map;

    // Initialize Route Drawing Controller
    const controller = setupRouteDrawing({
      map,
      onRouteDrawn: handleInternalRouteDrawn,
    });
    drawingControllerRef.current = controller;

    // Cursor position handler
    map.on('pointermove', (evt) => {
      if (evt.dragging) return;
      const coords = evt.coordinate as Coordinate;
      const geodetic = toGeodetic([coords[0], coords[1]]);
      setCursorCoords(geodetic);
      if (onCoordinateHoverRef.current) {
        onCoordinateHoverRef.current(geodetic);
      }
    });

    // Click handler for waypoint selection
    map.on('click', (evt) => {
      if (drawingControllerRef.current?.isActive()) return;

      let clickedWp: RoverWaypoint | null = null;
      map.forEachFeatureAtPixel(evt.pixel, (feature) => {
        const wp = feature.get('waypoint') as RoverWaypoint | undefined;
        if (wp) {
          clickedWp = wp;
          return true; // Stop searching
        }
        return false;
      });

      if (clickedWp) {
        setSelectedWaypoint(clickedWp);
        if (onWaypointSelectRef.current) {
          onWaypointSelectRef.current(clickedWp);
        }
      } else {
        setSelectedWaypoint(null);
      }
    });

    // ResizeObserver for reliable responsive canvas sizing
    const resizeObserver = new ResizeObserver(() => {
      map.updateSize();
    });
    resizeObserver.observe(mapElementRef.current);

    return () => {
      resizeObserver.disconnect();
      controller.destroy();
      map.setTarget(undefined);
      mapInstanceRef.current = null;
    };
  }, [handleInternalRouteDrawn]);

  // Sync incoming props from parent dashboard controls to internal state
  useEffect(() => {
    if (activeBaseLayer && activeBaseLayer !== selectedBaseLayer) {
      handleBaseLayerSelect(activeBaseLayer);
    }
  }, [activeBaseLayer, handleBaseLayerSelect, selectedBaseLayer]);

  useEffect(() => {
    setIsRegionalVisible(showRegionalTiles);
  }, [showRegionalTiles]);

  useEffect(() => {
    setIsFootprintVisible(showFootprint);
  }, [showFootprint]);

  useEffect(() => {
    setIsWaypointsVisible(showWaypoints);
  }, [showWaypoints]);

  // Sync layer visibility
  useEffect(() => {
    if (regionalLayerRef.current) {
      regionalLayerRef.current.setVisible(isRegionalVisible);
    }
  }, [isRegionalVisible]);

  useEffect(() => {
    if (footprintLayerRef.current) {
      footprintLayerRef.current.setVisible(isFootprintVisible);
    }
  }, [isFootprintVisible]);

  useEffect(() => {
    if (waypointLayerRef.current) {
      waypointLayerRef.current.setVisible(isWaypointsVisible);
    }
  }, [isWaypointsVisible]);

  // Sync route geometries to route layer source
  useEffect(() => {
    if (!routeLayerRef.current) return;
    const source = routeLayerRef.current.getSource();
    if (source) {
      updateRouteSource(source, routeA, routeB, drawnCoordinates);
    }
  }, [routeA, routeB, drawnCoordinates]);

  return (
    <div
      className={`mars-map-canvas relative w-full h-full min-h-[365px] bg-slate-950 overflow-hidden select-none font-sans text-slate-100 ${className}`}
      data-testid="mars-map-canvas"
    >
      {/* Map Viewport Container */}
      <div
        ref={mapElementRef}
        className={`w-full h-full ${isDrawingMode ? 'cursor-crosshair' : 'cursor-default'}`}
      />

      {/* Top Floating Controls: Basemap & Layer Switchers */}
      <div className="absolute top-4 left-4 z-20 flex flex-col gap-2 max-w-sm">
        {/* Route Drawing Action Toolbar */}
        <div className="bg-slate-900/90 backdrop-blur-md border border-cyan-500/50 rounded-lg p-2 shadow-2xl flex items-center gap-2">
          <button
            type="button"
            onClick={toggleDrawingMode}
            className={`px-3 py-1.5 text-xs font-semibold rounded-md transition-all flex items-center gap-1.5 ${
              isDrawingMode
                ? 'bg-rose-600 text-white animate-pulse shadow-md'
                : 'bg-cyan-600 hover:bg-cyan-500 text-white shadow-sm'
            }`}
          >
            <span>{isDrawingMode ? '⏹ Cancel Drawing' : '✏️ Draw Route'}</span>
          </button>
          {(drawnCoordinates.length > 0 || routeA || routeB) && (
            <button
              type="button"
              onClick={handleClearRoutes}
              className="px-2.5 py-1.5 text-xs font-medium rounded-md bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white transition-all border border-slate-700"
            >
              Clear
            </button>
          )}
          {isDrawingMode && (
            <span className="text-[11px] text-cyan-300 italic px-1 animate-pulse">
              Click points on map; double-click to finish.
            </span>
          )}
        </div>

        {/* Basemap Selector */}
        <div className="bg-slate-900/90 backdrop-blur-md border border-slate-700/80 rounded-lg p-2 shadow-2xl">
          <div className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider mb-1.5 px-1">
            Mars Basemap (WMTS)
          </div>
          <div className="grid grid-cols-3 gap-1">
            {(Object.keys(BASE_LAYER_CONFIGS) as BaseLayerId[]).map((id) => (
              <button
                key={id}
                type="button"
                onClick={() => handleBaseLayerSelect(id)}
                className={`px-2 py-1 text-xs font-medium rounded transition-all ${
                  selectedBaseLayer === id
                    ? 'bg-cyan-600 text-white shadow-sm'
                    : 'bg-slate-800/80 text-slate-300 hover:bg-slate-700 hover:text-white'
                }`}
              >
                {BASE_LAYER_CONFIGS[id].name.split(' ')[0]}
              </button>
            ))}
          </div>
        </div>

        {/* Analytical Layers Toggle */}
        <div className="bg-slate-900/90 backdrop-blur-md border border-slate-700/80 rounded-lg p-2 shadow-2xl flex flex-col gap-1.5">
          <div className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider px-1">
            Analytical Overlays
          </div>
          <label className="flex items-center gap-2 px-1 text-xs text-slate-300 hover:text-white cursor-pointer">
            <input
              type="checkbox"
              checked={isFootprintVisible}
              onChange={(e) => setIsFootprintVisible(e.target.checked)}
              className="rounded bg-slate-800 border-slate-600 text-amber-500 focus:ring-0 focus:ring-offset-0"
            />
            <span className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-sm border border-dashed border-amber-400 bg-amber-400/20" />
              HiRISE DTM Footprint (63.16%)
            </span>
          </label>
          <label className="flex items-center gap-2 px-1 text-xs text-slate-300 hover:text-white cursor-pointer">
            <input
              type="checkbox"
              checked={isWaypointsVisible}
              onChange={(e) => setIsWaypointsVisible(e.target.checked)}
              className="rounded bg-slate-800 border-slate-600 text-cyan-500 focus:ring-0 focus:ring-offset-0"
            />
            <span className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-cyan-400" />
              Rover Waypoints (Sols 383–387)
            </span>
          </label>
          <label className="flex items-center gap-2 px-1 text-xs text-slate-300 hover:text-white cursor-pointer">
            <input
              type="checkbox"
              checked={isRegionalVisible}
              onChange={(e) => setIsRegionalVisible(e.target.checked)}
              className="rounded bg-slate-800 border-slate-600 text-emerald-500 focus:ring-0 focus:ring-offset-0"
            />
            <span className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-sm bg-emerald-500/30 border border-emerald-400" />
              Regional DTM Tiles (z12–15)
            </span>
          </label>
        </div>
      </div>

      {/* Top-Right: Map Legend Overlay */}
      <div className="absolute top-4 right-4 z-20">
        <div className="bg-slate-900/90 backdrop-blur-md border border-slate-700/80 rounded-lg p-2.5 shadow-2xl text-xs max-w-xs">
          <div className="flex items-center justify-between gap-4 mb-2 pb-1 border-b border-slate-800">
            <span className="font-semibold text-slate-200">Map Symbology</span>
            <button
              type="button"
              onClick={() => setIsLegendOpen(!isLegendOpen)}
              className="text-slate-400 hover:text-white text-[10px]"
            >
              {isLegendOpen ? 'Collapse' : 'Expand'}
            </button>
          </div>
          {isLegendOpen && (
            <div className="flex flex-col gap-2 text-[11px] text-slate-300">
              <div className="flex items-center gap-2">
                <span className="w-4 h-3 rounded-sm border border-dashed border-amber-400 bg-amber-400/20" />
                <span>HiRISE Stereo DTM (Analytical Boundary)</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="w-3 h-3 rounded-full bg-cyan-400 border border-white" />
                <span>Perseverance Waypoint (Inside Footprint)</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="w-3 h-3 rounded-full bg-slate-500 border border-slate-300" />
                <span>Historical Waypoint (Landing Vicinity / Outside)</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="w-5 h-1 bg-blue-600 rounded" />
                <span>Route A (Primary Traverse)</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="w-5 h-1 border-t-2 border-dashed border-amber-500" />
                <span>Route B (Candidate / Alternate)</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-emerald-500" />
                <span className="w-2.5 h-2.5 rounded-full bg-rose-500 ml-1" />
                <span className="ml-1">Start / End Coordinates</span>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Center-Top: Analyzing Spinner Overlay */}
      {isAnalyzing && (
        <div className="absolute top-4 left-1/2 -translate-x-1/2 z-30">
          <div className="bg-slate-900/95 border border-cyan-500/60 rounded-full px-4 py-1.5 shadow-2xl flex items-center gap-2.5 text-xs text-cyan-200">
            <div className="w-3.5 h-3.5 border-2 border-cyan-400 border-t-transparent rounded-full animate-spin" />
            <span className="font-medium">Evaluating Martian Terrain Profile...</span>
          </div>
        </div>
      )}

      {/* Center-Top: Error Banner */}
      {analysisError && (
        <div className="absolute top-16 left-1/2 -translate-x-1/2 z-30 max-w-lg w-[90%]">
          <div className="bg-rose-950/95 border border-rose-500/70 rounded-lg p-2.5 shadow-2xl flex items-center justify-between text-xs text-rose-200">
            <div className="flex items-center gap-2">
              <span className="font-bold text-rose-400">⚠️ ERROR:</span>
              <span>{analysisError}</span>
            </div>
          </div>
        </div>
      )}

      {/* Bottom Center: Route Analysis Response Overlay Card */}
      {analysisResponse && (
        <div className="absolute bottom-10 left-1/2 -translate-x-1/2 z-25 max-w-2xl w-[92%]">
          <div className="bg-slate-900/95 backdrop-blur-md border border-cyan-500/50 rounded-xl p-3 shadow-2xl space-y-2">
            {/* Header with Mode & Status Badges */}
            <div className="flex items-center justify-between pb-1.5 border-b border-slate-800">
              <div className="flex items-center gap-2">
                <span className="font-bold text-slate-200 text-xs">{analysisResponse.route_id}</span>
                <span
                  className={`text-[10px] px-2 py-0.5 rounded-full font-semibold uppercase tracking-wider ${
                    analysisResponse.coverage_status === 'not_applicable' || analysisResponse.is_mock
                      ? 'bg-slate-800 text-slate-300 border border-slate-600'
                      : analysisResponse.coverage_status === 'complete'
                      ? 'bg-emerald-950 text-emerald-300 border border-emerald-500/50'
                      : analysisResponse.coverage_status === 'partial_gap'
                      ? 'bg-amber-950 text-amber-300 border border-amber-500/50'
                      : 'bg-rose-950 text-rose-300 border border-rose-500/50'
                  }`}
                >
                  {analysisResponse.coverage_status === 'not_applicable' || analysisResponse.is_mock
                    ? 'Coverage: Not Applicable (Synthetic)'
                    : analysisResponse.coverage_status === 'complete'
                    ? 'Coverage: 100% In-Footprint'
                    : analysisResponse.coverage_status === 'partial_gap'
                    ? 'Coverage: Partial HiRISE Gap'
                    : 'Coverage: Out of Stereo Bounds'}
                </span>
              </div>
              <span
                className={`text-[10px] font-mono px-2 py-0.5 rounded border ${
                  analysisResponse.is_mock
                    ? 'bg-amber-950/70 border-amber-500/40 text-amber-300'
                    : 'bg-emerald-950/70 border-emerald-500/40 text-emerald-300'
                }`}
              >
                {analysisResponse.is_mock ? 'DEVELOPMENT / MOCK DATA' : 'LIVE HiRISE DTM'}
              </span>
            </div>

            {/* Metrics Grid */}
            <div className="grid grid-cols-4 gap-2 text-center text-xs">
              <div className="bg-slate-800/60 p-1.5 rounded-lg border border-slate-700/60">
                <div className="text-[10px] text-slate-400">Total Distance</div>
                <div className="font-mono font-bold text-cyan-300">
                  {analysisResponse.total_distance_m >= 1000
                    ? `${(analysisResponse.total_distance_m / 1000).toFixed(2)} km`
                    : `${analysisResponse.total_distance_m.toFixed(1)} m`}
                </div>
              </div>
              <div className="bg-slate-800/60 p-1.5 rounded-lg border border-slate-700/60">
                <div className="text-[10px] text-slate-400">Elevation Gain</div>
                <div className="font-mono font-bold text-emerald-400">
                  +{analysisResponse.total_gain_m.toFixed(1)} m
                </div>
              </div>
              <div className="bg-slate-800/60 p-1.5 rounded-lg border border-slate-700/60">
                <div className="text-[10px] text-slate-400">Elevation Loss</div>
                <div className="font-mono font-bold text-amber-400">
                  -{analysisResponse.total_loss_m.toFixed(1)} m
                </div>
              </div>
              <div className="bg-slate-800/60 p-1.5 rounded-lg border border-slate-700/60">
                <div className="text-[10px] text-slate-400">Max Slope</div>
                <div className="font-mono font-bold text-rose-300">
                  {analysisResponse.max_slope_deg.toFixed(1)}°
                </div>
              </div>
            </div>

            {/* Scientific limitations notice per Section 7.2 of contract */}
            {analysisResponse.limitations && analysisResponse.limitations.length > 0 && (
              <div className="text-[10px] text-slate-400 italic bg-slate-950/50 p-1.5 rounded border border-slate-800">
                {analysisResponse.limitations[0]}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Geological POI Disclaimer Banner (when no analysis is displayed) */}
      {!analysisResponse && showDisclaimer && (
        <div className="absolute bottom-10 left-1/2 -translate-x-1/2 z-20 max-w-xl w-[90%]">
          <div className="bg-slate-900/95 backdrop-blur-md border border-amber-500/40 rounded-lg p-2 px-3 shadow-xl flex items-center justify-between gap-3 text-xs text-amber-200">
            <div className="flex items-center gap-2">
              <span className="text-amber-400 font-bold">ℹ️ NOTE:</span>
              <span className="text-[11px] leading-tight text-slate-300">{GEOLOGICAL_EMPTY_STATE_MESSAGE}</span>
            </div>
            <button
              type="button"
              onClick={() => setShowDisclaimer(false)}
              className="text-slate-400 hover:text-white text-xs px-1"
              title="Dismiss note"
            >
              ✕
            </button>
          </div>
        </div>
      )}

      {/* Waypoint Telemetry Modal / Card */}
      {selectedWaypoint && (
        <div className="absolute top-20 right-4 z-30 w-72 bg-slate-900/95 backdrop-blur-md border border-cyan-500/60 rounded-xl p-3.5 shadow-2xl text-xs">
          <div className="flex items-center justify-between pb-2 mb-2 border-b border-slate-800">
            <span className="font-bold text-cyan-300">{selectedWaypoint.name}</span>
            <button
              type="button"
              onClick={() => setSelectedWaypoint(null)}
              className="text-slate-400 hover:text-white"
            >
              ✕
            </button>
          </div>
          <div className="space-y-1.5 text-slate-300 text-[11px]">
            <div className="flex justify-between">
              <span className="text-slate-400">Mission Sol:</span>
              <span className="font-mono text-cyan-400">{selectedWaypoint.sol}</span>
            </div>
            {selectedWaypoint.site !== undefined && (
              <div className="flex justify-between">
                <span className="text-slate-400">Site / Drive:</span>
                <span className="font-mono">{selectedWaypoint.site} / {selectedWaypoint.drive ?? 0}</span>
              </div>
            )}
            <div className="flex justify-between">
              <span className="text-slate-400">Longitude:</span>
              <span className="font-mono">{selectedWaypoint.lon.toFixed(6)}° E</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Latitude:</span>
              <span className="font-mono">{selectedWaypoint.lat.toFixed(6)}° N</span>
            </div>
            {selectedWaypoint.elev_geoid_m !== undefined && (
              <div className="flex justify-between">
                <span className="text-slate-400">MOLA Elevation:</span>
                <span className="font-mono">{selectedWaypoint.elev_geoid_m.toFixed(2)} m</span>
              </div>
            )}
            <div className="flex justify-between">
              <span className="text-slate-400">Coverage Status:</span>
              <span
                className={`font-semibold ${
                  selectedWaypoint.inside_footprint ? 'text-emerald-400' : 'text-amber-400'
                }`}
              >
                {selectedWaypoint.inside_footprint ? 'Inside Stereo DTM' : 'Outside Stereo Footprint'}
              </span>
            </div>
            {selectedWaypoint.note && (
              <div className="pt-1 text-[10px] text-slate-400 italic">
                {selectedWaypoint.note}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Bottom Status Bar: Cursor Coordinates & Planetary Projection Info */}
      <div className="absolute bottom-0 left-0 right-0 z-20 bg-slate-950/90 backdrop-blur-md border-t border-slate-800 px-3 py-1 flex items-center justify-between text-[11px] font-mono text-slate-400">
        <div className="flex items-center gap-4">
          <span>CRS: <strong className="text-slate-200">MARS:2000 (IAU Sphere R=3,396,190m)</strong></span>
          <span>Extent: <strong className="text-slate-200">2:1 Equirectangular</strong></span>
        </div>
        <div className="flex items-center gap-3">
          <span>
            Lon:{' '}
            <strong className="text-cyan-300">
              {cursorCoords ? `${cursorCoords.lon.toFixed(5)}° E` : '--.-----°'}
            </strong>
          </span>
          <span>
            Lat:{' '}
            <strong className="text-cyan-300">
              {cursorCoords ? `${cursorCoords.lat.toFixed(5)}° N` : '--.-----°'}
            </strong>
          </span>
        </div>
      </div>
    </div>
  );
};

export default MapCanvas;
