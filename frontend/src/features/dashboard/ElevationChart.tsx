import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { EmptyState } from '../../components';

export type ElevationChartPoint = {
  distance: number;
  elevation: number;
};

type RawElevationPoint = {
  distance_m?: number | string;
  elevation_m?: number | string;
  distance?: number | string;
  elevation?: number | string;
};

interface ElevationChartProps {
  data?: RawElevationPoint[] | null;
  isLoading?: boolean;
  error?: string | null;
}

const toFiniteNumber = (value: number | string | undefined): number | null => {
  if (value === undefined || value === null || value === '') {
    return null;
  }

  const numericValue = typeof value === 'number' ? value : Number(value);
  return Number.isFinite(numericValue) ? numericValue : null;
};

export function normalizeElevationPoints(
  input?: RawElevationPoint[] | null,
): ElevationChartPoint[] {
  return (input ?? [])
    .map((point) => {
      const distance = toFiniteNumber(point.distance_m ?? point.distance);
      const elevation = toFiniteNumber(point.elevation_m ?? point.elevation);

      if (distance === null || elevation === null || distance < 0) {
        return null;
      }

      return { distance, elevation };
    })
    .filter((point): point is ElevationChartPoint => point !== null)
    .sort((left, right) => left.distance - right.distance)
    .filter((point, index, points) => index === 0 || point.distance !== points[index - 1].distance);
}

export function ElevationChart({ data, isLoading = false, error = null }: ElevationChartProps) {
  const chartData = normalizeElevationPoints(data);

  if (isLoading) {
    return (
      <div className="chart-empty-state">
        <EmptyState
          title="Loading elevation profile"
          description="Requesting the latest route metrics from the terrain service."
        />
      </div>
    );
  }

  if (error) {
    return (
      <div className="chart-empty-state">
        <EmptyState
          title="Elevation data unavailable"
          description={error}
        />
      </div>
    );
  }

  if (!chartData.length) {
    return (
      <div className="chart-empty-state">
        <EmptyState
          title="Elevation data unavailable"
          description="The route did not return any valid elevation samples."
        />
      </div>
    );
  }

  return (
    <div className="chart-surface" aria-label="Elevation profile chart" role="img">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={chartData} margin={{ top: 10, right: 18, bottom: 10, left: 8 }}>
          <defs>
            <linearGradient id="terrain-fill" x1="0" x2="0" y1="0" y2="1">
              <stop offset="0%" stopColor="#d88a2d" stopOpacity={0.32} />
              <stop offset="100%" stopColor="#d88a2d" stopOpacity={0.06} />
            </linearGradient>
          </defs>
          <CartesianGrid stroke="#d9d7cf" strokeDasharray="3 3" vertical={false} />
          <XAxis
            dataKey="distance"
            tickLine={{ stroke: '#aab4bf' }}
            tick={{ fill: '#435064', fontSize: 10 }}
            axisLine={{ stroke: '#aab4bf' }}
            height={28}
            minTickGap={28}
            domain={['dataMin', 'dataMax']}
            tickFormatter={(val: number) => (val >= 1000 ? `${(val / 1000).toFixed(1)} km` : `${Math.round(val)} m`)}
          />
          <YAxis
            dataKey="elevation"
            tickLine={{ stroke: '#aab4bf' }}
            tick={{ fill: '#435064', fontSize: 10 }}
            axisLine={{ stroke: '#aab4bf' }}
            width={62}
            domain={['auto', 'auto']}
            tickFormatter={(val: number) => `${Math.round(val)} m`}
          />
          <Tooltip
            formatter={(value) => {
              const numericValue = Number(value ?? 0);
              const safeValue = Number.isFinite(numericValue) ? numericValue : 0;
              return [`${safeValue.toFixed(1)} m`, 'Elevation (datum)'];
            }}
            labelFormatter={(label) => {
              const dist = Number(label ?? 0);
              return dist >= 1000
                ? `Distance: ${(dist / 1000).toFixed(2)} km`
                : `Distance: ${dist.toFixed(1)} m`;
            }}
          />
          <Area
            type="monotone"
            dataKey="elevation"
            stroke="#d88a2d"
            strokeWidth={2}
            fill="url(#terrain-fill)"
            isAnimationActive={false}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}

export default ElevationChart;
