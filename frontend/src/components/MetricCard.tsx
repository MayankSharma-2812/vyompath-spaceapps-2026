import type { ReactNode } from 'react';

interface MetricCardProps {
  title: string;
  value: ReactNode;
  description?: string;
}

export function MetricCard({ title, value, description }: MetricCardProps) {
  return (
    <article className="metric-card">
      <h3>{title}</h3>
      <p className="metric-card-value">{value}</p>
      {description && <p className="metric-card-description">{description}</p>}
    </article>
  );
}
