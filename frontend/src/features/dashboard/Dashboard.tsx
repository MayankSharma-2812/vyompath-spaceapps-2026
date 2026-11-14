import { useEffect, useState } from 'react';
import { MapCanvas } from '../map';
import { EmptyState, MetricCard, StatusBadge } from '../../components';
import ElevationChart, { type ElevationChartPoint } from './ElevationChart';

const SAMPLE_ROUTE = [
  { lon: 77.51, lat: 18.44 },
  { lon: 77.56, lat: 18.47 },
  { lon: 77.62, lat: 18.5 },
  { lon: 77.68, lat: 18.53 },
];

interface RouteAnalysisResponse {
  route_id: string;
  total_distance_m: number;
  elevation_profile: Array<{ distance_m: number; elevation_m: number }>;
  total_gain_m: number;
  total_loss_m: number;
  max_slope_deg: number;
  slope_window_m: number;
  dtm_source?: string;
  dtm_posting_m?: number;
  coverage_status: 'complete' | 'partial_gap' | 'out_of_bounds';
  limitations: string[];
}

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

function Sidebar() {
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
          {navigationItems.map((item, index) => (
            <li key={item}>
              <span
                className={`navigation-item${index === 0 ? ' is-active' : ''}`}
                aria-current={index === 0 ? 'page' : undefined}
              >
                <span className="navigation-marker" aria-hidden="true" />
                {item}
              </span>
            </li>
          ))}
        </ul>
      </nav>
      <div className="sidebar-footer">
        <span className="status-dot" aria-hidden="true" />
        <span>Scientific workspace</span>
      </div>
    </aside>
  );
}

function TopToolbar() {
  return (
    <header className="top-toolbar">
      <div className="toolbar-heading">
        <span className="eyebrow">MARS RESEARCH WORKSPACE</span>
        <h1>Explore the surface</h1>
      </div>
      <div className="toolbar-controls">
        <label className="search-field">
          <span className="search-icon" aria-hidden="true" />
          <input
            type="search"
            placeholder="Location search coming soon"
            aria-label="Martian location search"
            disabled
          />
        </label>
        <div className="region-indicator">
          <span className="region-label">STUDY REGION</span>
          <strong>Not selected</strong>
        </div>
      </div>
    </header>
  );
}

function MapContainer() {
  return (
    <section className="panel map-panel" aria-labelledby="map-title">
      <div className="panel-heading">
        <div>
          <span className="eyebrow">MAP WORKSPACE</span>
          <h2 id="map-title">Martian Surface Explorer</h2>
        </div>
        <StatusBadge className="panel-tag">MAP DATA NOT CONNECTED</StatusBadge>
      </div>
      <div className="map-stage">
        <MapCanvas />
        <EmptyState
          className="map-empty-state"
          icon={<span className="map-empty-icon" />}
          title="Interactive Mars map will be integrated here"
          description="Connect a validated basemap and mission layers to begin exploring."
        />
        <div className="map-layer-placeholder">
          <span className="region-label">LAYER CONTROLS</span>
          <span>Available when map layers are connected</span>
        </div>
      </div>
      <div className="map-statusbar" aria-label="Map information placeholders">
        <span>Zoom controls reserved</span>
        <span>Scale unavailable</span>
        <span>Coordinates unavailable</span>
      </div>
    </section>
  );
}

function RouteComparison({
  analysis,
  routeB = null,
  isLoading,
  error,
}: {
  analysis: RouteAnalysisResponse | null;
  routeB?: RouteAnalysisResponse | null;
  isLoading: boolean;
  error: string | null;
}) {
  const routeStatus = error
    ? `Route A analysis unavailable: ${error}`
    : isLoading && !analysis
      ? 'Loading Route A analysis.'
      : 'Route A analysis loaded.';

  return (
    <section className="panel comparison-panel" aria-labelledby="comparison-title">
      <div className="panel-heading">
        <div>
          <span className="eyebrow">ROUTE ANALYSIS</span>
          <h2 id="comparison-title">Route A vs Route B</h2>
        </div>
      </div>
      <div className="comparison-cards">
        {[
          { label: 'Route A', route: analysis },
          { label: 'Route B', route: routeB },
        ].map(({ label, route }) => (
          <article className="comparison-route-card" key={label} aria-label={`${label} metrics`}>
            <h3>{label}</h3>
            <p className="comparison-route-status">
              {label === 'Route A'
                ? routeStatus
                : route
                  ? 'Route B analysis loaded.'
                  : 'No distinct Route B has been selected. The dashboard has no route-selection flow yet.'}
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
          Direction is descriptive only; whether a higher or lower value is preferable depends on the mission.
        </p>
        <dl>
          {COMPARISON_METRICS.map((metric) => {
            const routeAValue = getMetricValue(analysis, metric.key);
            const routeBValue = getMetricValue(routeB, metric.key);
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

function TerrainProfile({ route = SAMPLE_ROUTE }: { route?: Array<{ lon: number; lat: number }> }) {
  const [analysis, setAnalysis] = useState<RouteAnalysisResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;

    const runAnalysis = async () => {
      setIsLoading(true);
      setError(null);

      try {
        const response = await fetch('http://localhost:8000/api/routes/analyze', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            route_id: 'demo-route',
            coordinates: route,
            buffer_distance_m: 250,
          }),
        });

        if (!response.ok) {
          throw new Error(`Request failed with status ${response.status}`);
        }

        const payload = (await response.json()) as RouteAnalysisResponse;

        if (isMounted) {
          setAnalysis(payload);
        }
      } catch (requestError) {
        if (isMounted) {
          setError(
            requestError instanceof Error
              ? requestError.message
              : 'Unable to load elevation data from the terrain service.',
          );
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    };

    void runAnalysis();

    return () => {
      isMounted = false;
    };
  }, [route]);

  const profile: ElevationChartPoint[] = (analysis?.elevation_profile ?? []).map((point) => ({
    distance: Number(point.distance_m),
    elevation: Number(point.elevation_m),
  }));

  const validProfile = profile.filter(
    (point) => Number.isFinite(point.distance) && Number.isFinite(point.elevation) && point.distance >= 0,
  );

  const maxElevation = validProfile.length
    ? Math.max(...validProfile.map((point) => point.elevation))
    : null;
  const minElevation = validProfile.length
    ? Math.min(...validProfile.map((point) => point.elevation))
    : null;

  const isMock = Boolean(
    !analysis?.dtm_source ||
    analysis.dtm_source.toLowerCase().includes('mock') ||
    analysis.dtm_source.toLowerCase().includes('stub') ||
    analysis.dtm_source.toLowerCase().includes('synthetic')
  );
  const badgeVariant = error ? 'error' : isLoading ? 'warning' : isMock ? 'neutral' : 'success';
  const badgeText = error ? 'DATA ERROR' : isLoading ? 'LOADING DATA' : isMock ? 'DEVELOPMENT / MOCK' : 'LIVE DTM DATA';

  return (
    <div className="terrain-analysis-stack">
      <section className="panel terrain-panel" aria-labelledby="terrain-title">
        <div className="panel-heading">
          <div>
            <span className="eyebrow">ELEVATION ANALYSIS</span>
            <h2 id="terrain-title">Terrain Elevation Profile</h2>
          </div>
          <StatusBadge className="panel-tag" variant={badgeVariant}>
            {badgeText}
          </StatusBadge>
        </div>
        <div className="chart-layout">
          <span className="axis-label axis-label-y">Elevation</span>
          <div className="chart-plot" role="img" aria-label="Terrain elevation profile chart">
            <ElevationChart data={analysis?.elevation_profile ?? []} isLoading={isLoading} error={error} />
            <span className="axis-label axis-label-x">Distance</span>
          </div>
        </div>
        <div className="terrain-metrics" aria-label="Terrain metrics">
          <MetricCard title="Gain" value={analysis ? `${analysis.total_gain_m.toFixed(1)} m` : 'Awaiting data'} />
          <MetricCard title="Loss" value={analysis ? `${analysis.total_loss_m.toFixed(1)} m` : 'Awaiting data'} />
          <MetricCard title="Maximum elevation" value={maxElevation !== null ? `${maxElevation.toFixed(1)} m` : 'Awaiting data'} />
          <MetricCard title="Minimum elevation" value={minElevation !== null ? `${minElevation.toFixed(1)} m` : 'Awaiting data'} />
        </div>
      </section>
      <RouteComparison analysis={analysis} isLoading={isLoading} error={error} />
    </div>
  );
}

function RouteSummary() {
  return (
    <section className="panel summary-panel" aria-labelledby="summary-title">
      <div className="panel-heading">
        <div>
          <span className="eyebrow">MISSION ANALYSIS</span>
          <h2 id="summary-title">Route summary</h2>
        </div>
      </div>
      <div className="summary-section">
        <h3>Route metrics</h3>
        <EmptyState
          title="No route metrics yet"
          description="Metrics will be available when a validated route is loaded."
        />
      </div>
      <div className="summary-section">
        <h3>Scientific points of interest</h3>
        <EmptyState
          title="No sites to display"
          description="Verified site data will appear here when a study region is selected."
        />
      </div>
    </section>
  );
}

function Dashboard() {
  return (
    <div className="dashboard-layout" id="dashboard">
      <Sidebar />
      <main className="dashboard-main">
        <TopToolbar />
        <div className="dashboard-content">
          <MapContainer />
          <div className="analysis-grid">
            <TerrainProfile />
            <RouteSummary />
          </div>
        </div>
      </main>
    </div>
  );
}

export default Dashboard;
