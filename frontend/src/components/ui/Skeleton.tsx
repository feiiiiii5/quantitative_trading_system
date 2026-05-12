import type { CSSProperties } from 'react';

interface SkeletonProps {
  width?: string | number;
  height?: string | number;
  borderRadius?: string | number;
  style?: CSSProperties;
}

export function Skeleton({ width = '100%', height = '1rem', borderRadius = '4px', style }: SkeletonProps) {
  return (
    <div
      style={{
        width,
        height,
        borderRadius,
        background: 'linear-gradient(90deg, rgba(255,255,255,0.05) 0%, rgba(255,255,255,0.1) 50%, rgba(255,255,255,0.05) 100%)',
        backgroundSize: '200% 100%',
        animation: 'skeleton-pulse 1.5s ease-in-out infinite',
        ...style,
      }}
    />
  );
}

export function SkeletonCard({ rows = 3 }: { rows?: number }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', padding: '1rem' }}>
      <Skeleton width="60%" height="1.25rem" />
      {Array.from({ length: rows }, (_, i) => (
        <Skeleton key={i} width={`${80 + (i % 3) * 10}%`} height="0.875rem" />
      ))}
    </div>
  );
}

export function SkeletonTable({ columns = 4, rows = 5 }: { columns?: number; rows?: number }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', padding: '1rem' }}>
      <div style={{ display: 'flex', gap: '1rem', marginBottom: '0.5rem' }}>
        {Array.from({ length: columns }, (_, i) => (
          <Skeleton key={i} width={`${100 / columns}%`} height="1rem" />
        ))}
      </div>
      {Array.from({ length: rows }, (_, r) => (
        <div key={r} style={{ display: 'flex', gap: '1rem' }}>
          {Array.from({ length: columns }, (_, c) => (
            <Skeleton key={c} width={`${100 / columns}%`} height="0.875rem" />
          ))}
        </div>
      ))}
    </div>
  );
}
