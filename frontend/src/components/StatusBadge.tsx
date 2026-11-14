import type { ReactNode } from 'react';

type StatusBadgeVariant = 'success' | 'warning' | 'error' | 'neutral';

interface StatusBadgeProps {
  children: ReactNode;
  variant?: StatusBadgeVariant;
  className?: string;
}

export function StatusBadge({
  children,
  variant = 'neutral',
  className = '',
}: StatusBadgeProps) {
  const classes = ['status-badge', `status-badge--${variant}`, className]
    .filter(Boolean)
    .join(' ');

  return <span className={classes}>{children}</span>;
}
