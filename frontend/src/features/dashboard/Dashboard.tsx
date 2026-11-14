import { useCallback, useEffect, useState } from 'react';
import {
  MapCanvas,
  type GeodeticCoordinate,
  type RouteGeometry,
  type RouteAnalysisData,
  type BaseLayerId,
  type RoverWaypoint,
  GEOLOGICAL_EMPTY_STATE_MESSAGE,
} from '../map';
import { EmptyState, MetricCard, StatusBadge } from '../../components';
import ElevationChart from './ElevationChart';

// Golden reference corridors from scientific fixtures
const PRESET_CORRIDORS: Record<string, { name: string; description: string; coords: GeodeticCoordinate[] }> = {
  jezeroFloor: {
    name: 'Jezero Floor (Sols 386–387)',
    description: 'Crater floor rapid transit corridor between Sol 386 and Sol 387 in HiRISE stereo DTM strip.',
    coords: [
      { lon: 77.46313311, lat: 18.46079140 },
      { lon: 77.46235628, lat: 18.46263369 },
      { lon: 77.46157944, lat: 18.46447597 },
    ],
  },
  jezeroDelta: {
    name: 'Jezero Delta Scarp',
    description: 'Steep delta scarp ingress corridor with significant elevation changes and varied slopes.',
    coords: [
      { lon: 77.54800000, lat: 18.46500000 },
      { lon: 77.55200000, lat: 18.47000000 },
      { lon: 77.55600000, lat: 18.47500000 },
    ],
  },
};

export type RouteAnalysisResponse = RouteAnalysisData;

const rawApiUrl = (import.meta.env.VITE_API_URL as string | undefined)?.trim();
// Strip trailing slash and trailing /api if user accidentally configured .../api
const cleanApiUrl = rawApiUrl
  ? rawApiUrl.replace(/\/api\/?$/, '').replace(/\/+$/, '')
  : undefined;

const API_BASE_URL =
  cleanApiUrl !== undefined && cleanApiUrl !== ''
    ? cleanApiUrl
    : typeof window !== 'undefined' &&
      window.location.hostname !== 'localhost' &&
      window.location.hostname !== '127.0.0.1' &&
      window.location.hostname.includes('onrender.com')
      ? 'https://vyompath-api.onrender.com'
      : typeof window !== 'undefined' &&
        (window.location.port === '80' || window.location.port === '8080')
        ? ''
        : typeof window !== 'undefined' && window.location.hostname === '127.0.0.1'
          ? 'http://127.0.0.1:8000'
          : 'http://localhost:8000';

const COMPARISON_METRICS = [
  { key: 'total_distance_m', title: 'Distance', unit: 'm' },
  { key: 'total_gain_m', title: 'Elevation gain', unit: 'm' },
  { key: 'total_loss_m', title: 'Elevation loss', unit: 'm' },
  { key: 'max_slope_deg', title: 'Maximum slope', unit: '°' },
] as const;

type ComparisonMetricKey = (typeof COMPARISON_METRICS)[number]['key'];

function getMetricValue(
  analysis: RouteAnalysisResponse | null,
  key: ComparisonMetricKey,
): number | null {
  const value = analysis?.[key];
  return typeof value === 'number' && Number.isFinite(value) && value >= 0 ? value : null;
}

function formatMetricValue(value: number | null, unit: string): string {
  if (value === null) {
    return 'Unavailable';
  }
  return `${value.toFixed(1)}${unit === '°' ? '' : ` ${unit}`}`;
}

function formatMagnitude(value: number, unit: string): string {
  const formattedValue = value.toFixed(1);
  const magnitude = Number(formattedValue) === 0 ? '<0.1' : formattedValue;
  return `${magnitude}${unit === '°' ? '' : ` ${unit}`}`;
}

function formatMetricDelta(
  routeAValue: number | null,
  routeBValue: number | null,
  unit: string,
): string {
  if (routeAValue === null || routeBValue === null) {
    return 'Unavailable until both routes are analyzed.';
  }

  const delta = routeBValue - routeAValue;
  if (delta === 0) {
    return `Δ 0.0${unit === '°' ? '' : ` ${unit}`} · No difference`;
  }

  const direction = delta > 0 ? 'Route B higher' : 'Route B lower';
  const sign = delta > 0 ? '+' : '−';

  return `Δ ${sign}${formatMagnitude(Math.abs(delta), unit)} · ${direction}`;
}

const navigationItems = [
  'Explore Map',
  'Route Planner',
  'Mission Layers',
  'Scientific Sites',
  'Terrain Profile',
  'Route Comparison',
  'Data Sources',
];

const NAVIGATION_TARGETS: Record<string, string> = {
  'Explore Map': 'map-section',
  'Route Planner': 'map-section',
  'Mission Layers': 'map-section',
  'Scientific Sites': 'summary-section',
  'Terrain Profile': 'terrain-section',
  'Route Comparison': 'comparison-section',
  'Data Sources': 'provenance-section',
};

interface SidebarProps {
  activeItem: string;
  onNavigate: (item: string) => void;
}

function Sidebar({ activeItem, onNavigate }: SidebarProps) {
  return (
    <aside className="sidebar">
      <a className="brand" href="#dashboard" aria-label="NAKSHATRA-VYOMPATH dashboard">
        <span className="brand-mark" aria-hidden="true">N</span>
        <span>
          <strong>NAKSHATRA</strong>
          <small>VYOMPATH</small>
        </span>
      </a>
      <div className="sidebar-label">WORKSPACE</div>
      <nav aria-label="Main navigation">
        <ul className="navigation-list">
          {navigationItems.map((item) => {
            const isActive = activeItem === item;
            return (
              <li key={item}>
                <button
                  type="button"
                  onClick={() => onNavigate(item)}
                  className={`navigation-item${isActive ? ' is-active' : ''}`}
                  aria-current={isActive ? 'page' : undefined}
                  style={{
                    background: 'none',
                    border: 'none',
                    width: '100%',
                    textAlign: 'left',
                    cursor: 'pointer',
                  }}
                >
                  <span className="navigation-marker" aria-hidden="true" />
                  {item}
                </button>
              </li>
            );
          })}
        </ul>
      </nav>
      <div className="sidebar-footer">
        <span className="status-dot" aria-hidden="true" />
        <span>Scientific workspace</span>
      </div>
    </aside>
  );
}

interface TopToolbarProps {
  backendMode: string | null;
  activePreset: string;
  onSelectPreset: (presetKey: string) => void;
  onClearRoute: () => void;
}

function TopToolbar({
  backendMode,
  activePreset,
  onSelectPreset,
  onClearRoute,
}: TopToolbarProps) {
  const isLive = backendMode === 'production/live' || backendMode === 'live';
  const isOffline = backendMode === 'offline/mock' || backendMode === 'offline';
  const badgeVariant = isLive ? 'success' : isOffline ? 'neutral' : 'neutral';
  const badgeText = isLive
    ? 'LIVE TERRAIN ENGINE'
    : isOffline
      ? 'BACKEND OFFLINE (MOCK)'
      : 'DEVELOPMENT / MOCK BACKEND';

  return (
    <header className="top-toolbar">
      <div className="toolbar-heading">
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <span className="eyebrow">MARS RESEARCH WORKSPACE</span>
          {backendMode && (
            <StatusBadge variant={badgeVariant}>
              {badgeText}
            </StatusBadge>
          )}
        </div>
        <h1>Explore the surface</h1>
      </div>
      <div className="toolbar-controls" style={{ display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}>
        <div className="preset-selector" style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
          <button
            type="button"
            onClick={() => onSelectPreset('jezeroFloor')}
            style={{
              padding: '6px 10px',
              fontSize: '11px',
              fontWeight: 600,
              borderRadius: '4px',
              border: activePreset === 'jezeroFloor' ? '1px solid #d88a2d' : '1px solid #cbd5e1',
              background: activePreset === 'jezeroFloor' ? '#fef3c7' : '#ffffff',
              color: activePreset === 'jezeroFloor' ? '#92400e' : '#334155',
              cursor: 'pointer',
            }}
          >
            Floor Corridor (Sol 386–387)
          </button>
          <button
            type="button"
            onClick={() => onSelectPreset('jezeroDelta')}
            style={{
              padding: '6px 10px',
              fontSize: '11px',
              fontWeight: 600,
              borderRadius: '4px',
              border: activePreset === 'jezeroDelta' ? '1px solid #d88a2d' : '1px solid #cbd5e1',
              background: activePreset === 'jezeroDelta' ? '#fef3c7' : '#ffffff',
              color: activePreset === 'jezeroDelta' ? '#92400e' : '#334155',
              cursor: 'pointer',
            }}
          >
            Delta Scarp
          </button>
          <button
            type="button"
            onClick={onClearRoute}
            style={{
              padding: '6px 10px',
              fontSize: '11px',
              borderRadius: '4px',
              border: '1px solid #cbd5e1',
              background: '#ffffff',
              color: '#64748b',
              cursor: 'pointer',
            }}
          >
            Clear / Draw Freehand
          </button>
        </div>
        <div className="region-indicator">
          <span className="region-label">STUDY REGION</span>
          <strong>Jezero Crater AOI</strong>
        </div>
      </div>
    </header>
  );
}

interface MapContainerProps {
  drawnRoute: GeodeticCoordinate[] | null;
  routeB: GeodeticCoordinate[] | null;
  analysis: RouteAnalysisResponse | null;
  isAnalyzing: boolean;
  analysisError: string | null;
  activeBaseLayer: BaseLayerId;
  showRegionalTiles: boolean;
  showFootprint: boolean;
  showWaypoints: boolean;
  onChangeBaseLayer: (layer: BaseLayerId) => void;
  onToggleRegionalTiles: () => void;
  onToggleFootprint: () => void;
  onToggleWaypoints: () => void;
  onRouteDrawn: (coords: GeodeticCoordinate[]) => void;
  onRouteClear: () => void;
  onWaypointSelect?: (waypoint: RoverWaypoint) => void;
}

function MapContainer({
  drawnRoute,
  routeB,
  analysis,
  isAnalyzing,
  analysisError,
  activeBaseLayer,
  showRegionalTiles,
  showFootprint,
  showWaypoints,
  onChangeBaseLayer,
  onToggleRegionalTiles,
  onToggleFootprint,
  onToggleWaypoints,
  onRouteDrawn,
  onRouteClear,
  onWaypointSelect,
}: MapContainerProps) {
  const [hoverCoords, setHoverCoords] = useState<GeodeticCoordinate | null>(null);

  const routeAGeometry: RouteGeometry | null =
    drawnRoute && drawnRoute.length >= 2
      ? {
          id: 'route-a',
          name: 'Traverse Route A',
          coordinates: drawnRoute,
          style: 'route-a',
        }
      : null;

  const routeBGeometry: RouteGeometry | null =
    routeB && routeB.length >= 2
      ? {
          id: 'route-b',
          name: 'Comparison Route B',
          coordinates: routeB,
          style: 'route-b',
        }
      : null;

  return (
    <section className="panel map-panel" id="map-section" aria-labelledby="map-title">
      <div className="panel-heading" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <span className="eyebrow">MAP WORKSPACE</span>
          <h2 id="map-title">Martian Surface Explorer</h2>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <label style={{ fontSize: '11px', display: 'flex', alignItems: 'center', gap: '4px', color: '#475569' }}>
            Base Layer:
            <select
              value={activeBaseLayer}
              onChange={(e) => onChangeBaseLayer(e.target.value as BaseLayerId)}
              style={{
                fontSize: '11px',
                padding: '3px 6px',
                borderRadius: '4px',
                border: '1px solid #cbd5e1',
                background: '#ffffff',
              }}
            >
              <option value="mola-colorhillshade">MOLA Color Shaded Relief</option>
              <option value="ctx-mosaic">CTX Visible Mosaic</option>
              <option value="viking-mdim21">Viking MDIM 2.1</option>
            </select>
          </label>
          <button
            type="button"
            onClick={onToggleRegionalTiles}
            style={{
              fontSize: '10px',
              padding: '4px 7px',
              borderRadius: '4px',
              border: '1px solid #cbd5e1',
              background: showRegionalTiles ? '#e0f2fe' : '#ffffff',
              color: showRegionalTiles ? '#0369a1' : '#64748b',
              cursor: 'pointer',
            }}
          >
            HiRISE DTM
          </button>
          <button
            type="button"
            onClick={onToggleFootprint}
            style={{
              fontSize: '10px',
              padding: '4px 7px',
              borderRadius: '4px',
              border: '1px solid #cbd5e1',
              background: showFootprint ? '#fef3c7' : '#ffffff',
              color: showFootprint ? '#92400e' : '#64748b',
              cursor: 'pointer',
            }}
          >
            Footprint
          </button>
          <button
            type="button"
            onClick={onToggleWaypoints}
            style={{
              fontSize: '10px',
              padding: '4px 7px',
              borderRadius: '4px',
              border: '1px solid #cbd5e1',
              background: showWaypoints ? '#dcfce7' : '#ffffff',
              color: showWaypoints ? '#15803d' : '#64748b',
              cursor: 'pointer',
            }}
          >
            Waypoints
          </button>
        </div>
      </div>
      <div className="map-stage" style={{ position: 'relative' }}>
        <MapCanvas
          activeBaseLayer={activeBaseLayer}
          showRegionalTiles={showRegionalTiles}
          showFootprint={showFootprint}
          showWaypoints={showWaypoints}
          routeA={routeAGeometry}
          routeB={routeBGeometry}
          analysisResponse={analysis}
          isAnalyzing={isAnalyzing}
          analysisError={analysisError}
          onRouteDrawn={onRouteDrawn}
          onRouteClear={onRouteClear}
          onWaypointSelect={onWaypointSelect}
          onCoordinateHover={setHoverCoords}
          onBaseLayerChange={onChangeBaseLayer}
          onToggleFootprint={onToggleFootprint}
          onToggleWaypoints={onToggleWaypoints}
          onToggleRegionalTiles={onToggleRegionalTiles}
        />
      </div>
      <div className="map-statusbar" aria-label="Map telemetry status">
        {hoverCoords ? (
          <span>
            {hoverCoords.lat >= 0 ? `${hoverCoords.lat.toFixed(4)}°N` : `${Math.abs(hoverCoords.lat).toFixed(4)}°S`},{' '}
            {hoverCoords.lon >= 0 ? `${hoverCoords.lon.toFixed(4)}°E` : `${Math.abs(hoverCoords.lon).toFixed(4)}°W`}
          </span>
        ) : (
          <span>Hover map for coordinates · Click & drag on map to draw route</span>
        )}
        <span>Mars 2000 Equirectangular (R=3,396,190m)</span>
      </div>
    </section>
  );
}

function RouteComparison({
  analysis,
  routeBAnalysis,
  isLoading,
  error,
  onSetAsRouteB,
  onClearRouteB,
}: {
  analysis: RouteAnalysisResponse | null;
  routeBAnalysis: RouteAnalysisResponse | null;
  isLoading: boolean;
  error: string | null;
  onSetAsRouteB: () => void;
  onClearRouteB?: () => void;
}) {
  const routeStatus = error
    ? `Route A analysis unavailable: ${error}`
    : isLoading
      ? 'Loading Route A analysis...'
      : analysis
        ? 'Route A analysis loaded.'
        : 'No Route A drawn. Draw a route or select a corridor to analyze Route A.';

  return (
    <section className="panel comparison-panel" id="comparison-section" aria-labelledby="comparison-title">
      <div className="panel-heading" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <span className="eyebrow">ROUTE ANALYSIS</span>
          <h2 id="comparison-title">Route A vs Route B Comparison</h2>
        </div>
        <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
          {analysis && (
            <button
              type="button"
              onClick={onSetAsRouteB}
              style={{
                padding: '4px 8px',
                fontSize: '11px',
                borderRadius: '4px',
                border: '1px solid #d88a2d',
                background: '#fff',
                color: '#d88a2d',
                fontWeight: 600,
                cursor: 'pointer',
              }}
            >
              Pin Current as Route B
            </button>
          )}
          {routeBAnalysis && onClearRouteB && (
            <button
              type="button"
              onClick={onClearRouteB}
              style={{
                padding: '4px 8px',
                fontSize: '11px',
                borderRadius: '4px',
                border: '1px solid #cbd5e1',
                background: '#fff',
                color: '#64748b',
                fontWeight: 500,
                cursor: 'pointer',
              }}
            >
              Clear Route B
            </button>
          )}
        </div>
      </div>
      <div className="comparison-cards">
        {[
          { label: 'Route A', route: analysis },
          { label: 'Route B', route: routeBAnalysis },
        ].map(({ label, route }) => (
          <article className="comparison-route-card" key={label} aria-label={`${label} metrics`}>
            <h3>{label}</h3>
            <p className="comparison-route-status">
              {label === 'Route A'
                ? routeStatus
                : route
                  ? 'Route B analysis pinned.'
                  : 'No distinct Route B pinned. Draw another route or select a preset, then pin as Route B.'}
            </p>
            <div className="comparison-metrics">
              {COMPARISON_METRICS.map((metric) => (
                <MetricCard
                  key={metric.key}
                  title={metric.title}
                  value={formatMetricValue(getMetricValue(route, metric.key), metric.unit)}
                />
              ))}
            </div>
          </article>
        ))}
      </div>
      <div className="comparison-deltas" aria-label="Route metric differences">
        <h3>Differences <span>Δ = Route B − Route A</span></h3>
        <p className="comparison-note">
          Direction is descriptive only; whether a higher or lower value is preferable depends on mission criteria. Traversability outputs are advisory risk indicators.
        </p>
        <dl>
          {COMPARISON_METRICS.map((metric) => {
            const routeAValue = getMetricValue(analysis, metric.key);
            const routeBValue = getMetricValue(routeBAnalysis, metric.key);
            const delta = routeAValue !== null && routeBValue !== null
              ? routeBValue - routeAValue
              : null;

            return (
              <div className="comparison-delta" key={metric.key}>
                <dt>{metric.title}</dt>
                <dd className={delta === 0 ? 'is-zero' : undefined}>
                  {formatMetricDelta(routeAValue, routeBValue, metric.unit)}
                </dd>
              </div>
            );
          })}
        </dl>
      </div>
    </section>
  );
}

interface TerrainProfileProps {
  analysis: RouteAnalysisResponse | null;
  isLoading: boolean;
  error: string | null;
}

function TerrainProfile({ analysis, isLoading, error }: TerrainProfileProps) {
  // Safe filtering of null elevation values
  const validProfile = (analysis?.elevation_profile ?? []).filter(
    (point) =>
      point.elevation_m !== null &&
      point.elevation_m !== undefined &&
      point.distance_m !== null &&
      point.distance_m !== undefined &&
      Number.isFinite(Number(point.elevation_m)) &&
      Number.isFinite(Number(point.distance_m)) &&
      Number(point.distance_m) >= 0,
  );

  const maxElevation = validProfile.length
    ? Math.max(...validProfile.map((point) => Number(point.elevation_m)))
    : null;
  const minElevation = validProfile.length
    ? Math.min(...validProfile.map((point) => Number(point.elevation_m)))
    : null;

  const isMock = Boolean(
    analysis?.is_mock ||
    !analysis?.dtm_source ||
    analysis.dtm_source.toLowerCase().includes('mock') ||
    analysis.dtm_source.toLowerCase().includes('stub') ||
    analysis.dtm_source.toLowerCase().includes('synthetic')
  );

  const coverageStatus = analysis?.coverage_status ?? 'complete';
  const hasCoverageGap = coverageStatus === 'partial_gap';
  const isOutOfBounds = coverageStatus === 'out_of_bounds';

  const badgeVariant = error
    ? 'error'
    : isLoading
      ? 'warning'
      : isOutOfBounds
        ? 'error'
        : hasCoverageGap
          ? 'warning'
          : isMock
            ? 'neutral'
            : 'success';

  const badgeText = error
    ? 'DATA ERROR'
    : isLoading
      ? 'LOADING DATA'
      : isOutOfBounds
        ? 'OUT OF COVERAGE'
        : hasCoverageGap
          ? 'PARTIAL DTM GAP'
          : isMock
            ? 'DEVELOPMENT / MOCK'
            : 'LIVE DTM DATA';

  return (
    <div className="terrain-analysis-stack" id="terrain-section">
      <section className="panel terrain-panel" aria-labelledby="terrain-title">
        <div className="panel-heading">
          <div>
            <span className="eyebrow">ELEVATION ANALYSIS</span>
            <h2 id="terrain-title">Terrain Elevation Profile</h2>
          </div>
          <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
            {hasCoverageGap && (
              <StatusBadge variant="warning">PARTIAL GAP</StatusBadge>
            )}
            <StatusBadge className="panel-tag" variant={badgeVariant}>
              {badgeText}
            </StatusBadge>
          </div>
        </div>
        <div className="chart-layout">
          <span className="axis-label axis-label-y">Elevation (m)</span>
          <div className="chart-plot" role="img" aria-label="Terrain elevation profile chart">
            <ElevationChart data={analysis?.elevation_profile ?? []} isLoading={isLoading} error={error} />
            <span className="axis-label axis-label-x">Distance along traverse</span>
          </div>
        </div>
        <div className="terrain-metrics" aria-label="Terrain metrics">
          <MetricCard title="Elevation Gain" value={analysis ? `${analysis.total_gain_m.toFixed(1)} m` : 'Awaiting data'} />
          <MetricCard title="Elevation Loss" value={analysis ? `${analysis.total_loss_m.toFixed(1)} m` : 'Awaiting data'} />
          <MetricCard title="Max Elevation" value={maxElevation !== null ? `${maxElevation.toFixed(1)} m` : (analysis ? 'No valid samples' : 'Awaiting data')} />
          <MetricCard title="Min Elevation" value={minElevation !== null ? `${minElevation.toFixed(1)} m` : (analysis ? 'No valid samples' : 'Awaiting data')} />
        </div>
      </section>
    </div>
  );
}

function RouteSummary({
  analysis,
  onSelectPreset,
}: {
  analysis: RouteAnalysisResponse | null;
  onSelectPreset?: (presetKey: string) => void;
}) {
  const nearbyPois = analysis?.nearby_pois ?? [];
  const limitations = analysis?.limitations ?? [];

  return (
    <section className="panel summary-panel" id="summary-section" aria-labelledby="summary-title">
      <div className="panel-heading">
        <div>
          <span className="eyebrow">MISSION ANALYSIS</span>
          <h2 id="summary-title">Route summary & science transparency</h2>
        </div>
      </div>

      <div className="summary-section">
        <h3>Route metrics</h3>
        {analysis ? (
          <div className="summary-metrics-grid" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
            <MetricCard
              title="Total distance"
              value={
                analysis.total_distance_m >= 1000
                  ? `${(analysis.total_distance_m / 1000).toFixed(2)} km`
                  : `${analysis.total_distance_m.toFixed(1)} m`
              }
            />
            <MetricCard
              title="Coverage status"
              value={
                analysis.coverage_status === 'complete'
                  ? 'Complete (100% Valid)'
                  : analysis.coverage_status === 'partial_gap'
                    ? 'Partial Gap (NoData crossing)'
                    : 'Out of Bounds'
              }
            />
            <MetricCard
              title="DTM ground resolution"
              value={analysis.dtm_posting_m ? `${analysis.dtm_posting_m.toFixed(2)} m/px` : 'N/A (Synthetic)'}
            />
            <MetricCard
              title="Max slope (baseline)"
              value={`${analysis.max_slope_deg.toFixed(1)}° (${analysis.slope_window_m ?? 50}m window)`}
            />
          </div>
        ) : (
          <EmptyState
            title="No route metrics yet"
            description="Draw a route on the Mars map or choose a preset corridor to calculate terrain metrics."
            action={
              onSelectPreset
                ? {
                    label: 'Load Jezero Floor Corridor',
                    onClick: () => onSelectPreset('jezeroFloor'),
                  }
                : undefined
            }
          />
        )}
      </div>

      <div className="summary-section">
        <h3>Perseverance Rover Waypoints (Sols 383–387)</h3>
        {nearbyPois.length > 0 ? (
          <ul style={{ listStyle: 'none', padding: 0, margin: 0, display: 'grid', gap: '6px' }}>
            {nearbyPois.map((poi: any, idx: number) => (
              <li
                key={poi.id || idx}
                style={{
                  padding: '8px 10px',
                  background: 'rgba(255, 255, 255, 0.8)',
                  border: '1px solid #cbd5e1',
                  borderRadius: '6px',
                  fontSize: '11px',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <strong>{poi.name || poi.id}</strong>
                  <span style={{ color: '#0369a1', fontSize: '10px' }}>
                    Offset: {poi.cross_track_m?.toFixed(1) ?? 0}m
                  </span>
                </div>
                {poi.significance && (
                  <p style={{ margin: '3px 0 0', color: '#64748b', fontSize: '10px' }}>{poi.significance}</p>
                )}
              </li>
            ))}
          </ul>
        ) : (
          <div style={{ padding: '10px', background: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: '6px' }}>
            <p style={{ margin: 0, fontSize: '11px', color: '#475569', lineHeight: 1.5 }}>
              {GEOLOGICAL_EMPTY_STATE_MESSAGE}
            </p>
          </div>
        )}
      </div>

      {limitations.length > 0 && (
        <div className="summary-section" id="provenance-section">
          <h3>Scientific limitations & data provenance</h3>
          <ul
            style={{
              listStyle: 'none',
              padding: 0,
              margin: 0,
              display: 'grid',
              gap: '6px',
              fontSize: '10.5px',
              color: '#475569',
            }}
          >
            {limitations.map((lim, idx) => (
              <li
                key={idx}
                style={{
                  padding: '6px 8px',
                  background: '#fefce8',
                  border: '1px solid #fef08a',
                  borderRadius: '4px',
                  lineHeight: 1.4,
                }}
              >
                {lim}
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}

function Dashboard() {
  const [activePreset, setActivePreset] = useState<string>('jezeroFloor');
  const [drawnRoute, setDrawnRoute] = useState<GeodeticCoordinate[] | null>(PRESET_CORRIDORS.jezeroFloor.coords);
  const [routeB, setRouteB] = useState<GeodeticCoordinate[] | null>(null);
  const [analysis, setAnalysis] = useState<RouteAnalysisResponse | null>(null);
  const [routeBAnalysis, setRouteBAnalysis] = useState<RouteAnalysisResponse | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState<boolean>(true);
  const [analysisError, setAnalysisError] = useState<string | null>(null);
  const [backendMode, setBackendMode] = useState<string | null>(null);

  // Layer visibility state
  const [activeBaseLayer, setActiveBaseLayer] = useState<BaseLayerId>('mola-colorhillshade');
  const [showRegionalTiles, setShowRegionalTiles] = useState<boolean>(true);
  const [showFootprint, setShowFootprint] = useState<boolean>(true);
  const [showWaypoints, setShowWaypoints] = useState<boolean>(true);

  // Fetch /api/health to confirm backend operational mode
  useEffect(() => {
    let isMounted = true;
    const checkHealth = async () => {
      try {
        const res = await fetch(`${API_BASE_URL}/api/health`);
        if (res.ok) {
          const data = await res.json();
          if (isMounted) {
            setBackendMode(data.mode ?? 'development/mock');
          }
        }
      } catch {
        if (isMounted) {
          setBackendMode('offline/mock');
        }
      }
    };
    void checkHealth();
    return () => {
      isMounted = false;
    };
  }, []);

  const runAnalysis = useCallback(async (coords: GeodeticCoordinate[]): Promise<RouteAnalysisResponse | null> => {
    if (!coords || coords.length < 2) {
      setAnalysis(null);
      setIsAnalyzing(false);
      return null;
    }

    setIsAnalyzing(true);
    setAnalysisError(null);

    try {
      const response = await fetch(`${API_BASE_URL}/api/routes/analyze`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          route_id: `traverse-${Date.now().toString().slice(-4)}`,
          coordinates: coords,
          buffer_distance_m: 250,
        }),
      });

      if (!response.ok) {
        if (response.status === 422) {
          const errJson = await response.json().catch(() => null);
          const detail = errJson?.detail;
          const msg = typeof detail === 'string'
            ? detail
            : Array.isArray(detail)
              ? detail.map((d: any) => d.msg || (typeof d === 'string' ? d : JSON.stringify(d))).join(', ')
              : 'Route exceeds maximum allowed length of 25.0 km or contains invalid coordinates.';
          throw new Error(msg);
        }
        throw new Error(`Request failed with status ${response.status}`);
      }

      const payload = (await response.json()) as RouteAnalysisResponse;
      setAnalysis(payload);
      return payload;
    } catch (requestError) {
      const errorMsg = requestError instanceof Error
        ? requestError.message
        : 'Unable to load elevation data from the terrain service.';
      setAnalysisError(errorMsg);
      return null;
    } finally {
      setIsAnalyzing(false);
    }
  }, []);

  // Initial analysis on mount with the default preset corridor
  useEffect(() => {
    void runAnalysis(PRESET_CORRIDORS.jezeroFloor.coords);
  }, [runAnalysis]);

  // Handle route drawn callback from MapCanvas
  const handleRouteDrawn = useCallback(
    (coords: GeodeticCoordinate[]) => {
      setActivePreset('');
      setDrawnRoute(coords);
      void runAnalysis(coords);
    },
    [runAnalysis],
  );

  // Handle route clear callback from MapCanvas
  const handleRouteClear = useCallback(() => {
    setActivePreset('');
    setDrawnRoute(null);
    setAnalysis(null);
    setAnalysisError(null);
  }, []);

  // Preset selector
  const handleSelectPreset = useCallback(
    (presetKey: string) => {
      const preset = PRESET_CORRIDORS[presetKey];
      if (!preset) return;
      setActivePreset(presetKey);
      setDrawnRoute(preset.coords);
      void runAnalysis(preset.coords);
    },
    [runAnalysis],
  );

  // Pin current route as Route B for comparison
  const handleSetAsRouteB = useCallback(() => {
    if (drawnRoute && analysis) {
      setRouteB(drawnRoute);
      setRouteBAnalysis(analysis);
    }
  }, [drawnRoute, analysis]);

  // Clear Route B comparison
  const handleClearRouteB = useCallback(() => {
    setRouteB(null);
    setRouteBAnalysis(null);
  }, []);

  // Active navigation tracking and smooth scrolling
  const [activeNav, setActiveNav] = useState<string>('Explore Map');

  const handleNavigate = useCallback((item: string) => {
    setActiveNav(item);
    const targetId = NAVIGATION_TARGETS[item];
    if (targetId) {
      const el = document.getElementById(targetId);
      if (el) {
        el.scrollIntoView({ behavior: 'smooth' });
      }
    }
  }, []);

  return (
    <div className="dashboard-layout" id="dashboard">
      <Sidebar activeItem={activeNav} onNavigate={handleNavigate} />
      <main className="dashboard-main">
        <TopToolbar
          backendMode={backendMode}
          activePreset={activePreset}
          onSelectPreset={handleSelectPreset}
          onClearRoute={handleRouteClear}
        />
        <div className="dashboard-content">
          <MapContainer
            drawnRoute={drawnRoute}
            routeB={routeB}
            analysis={analysis}
            isAnalyzing={isAnalyzing}
            analysisError={analysisError}
            activeBaseLayer={activeBaseLayer}
            showRegionalTiles={showRegionalTiles}
            showFootprint={showFootprint}
            showWaypoints={showWaypoints}
            onChangeBaseLayer={setActiveBaseLayer}
            onToggleRegionalTiles={() => setShowRegionalTiles((prev) => !prev)}
            onToggleFootprint={() => setShowFootprint((prev) => !prev)}
            onToggleWaypoints={() => setShowWaypoints((prev) => !prev)}
            onRouteDrawn={handleRouteDrawn}
            onRouteClear={handleRouteClear}
          />
          <div className="analysis-grid">
            <TerrainProfile
              analysis={analysis}
              isLoading={isAnalyzing}
              error={analysisError}
            />
            <RouteComparison
              analysis={analysis}
              routeBAnalysis={routeBAnalysis}
              isLoading={isAnalyzing}
              error={analysisError}
              onSetAsRouteB={handleSetAsRouteB}
              onClearRouteB={handleClearRouteB}
            />
            <RouteSummary
              analysis={analysis}
              onSelectPreset={handleSelectPreset}
            />
          </div>
        </div>
      </main>
    </div>
  );
}

export default Dashboard;