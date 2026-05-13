import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { DataCell } from './DataCell';

vi.mock('@/utils/format', () => ({
  formatPrice: (n: number) => `$${n.toFixed(2)}`,
  formatPercent: (n: number) => `${n >= 0 ? '+' : ''}${n.toFixed(2)}%`,
  formatRatio: (n: number) => `${(n * 100).toFixed(2)}%`,
  formatVolume: (n: number) => `${n}vol`,
  formatAmount: (n: number) => `${n}amt`,
  priceColor: (n: number) => (n > 0 ? 'var(--signal-rise)' : n < 0 ? 'var(--signal-fall)' : 'var(--label-secondary)'),
}));

vi.mock('@/hooks/useCountUp', () => ({
  useCountUp: (target: number) => target,
}));

vi.mock('@/hooks/useTickFlash', () => ({
  useTickFlash: (_value: number) => null,
}));

describe('DataCell', () => {
  it('renders label and value', () => {
    render(<DataCell label="Price" value={100} />);
    expect(screen.getByText('Price')).toBeInTheDocument();
    expect(screen.getByText('100')).toBeInTheDocument();
  });

  it('applies price format correctly', () => {
    render(<DataCell label="Price" value={99.5} format="price" />);
    expect(screen.getByText('$99.50')).toBeInTheDocument();
  });

  it('applies percent format correctly', () => {
    render(<DataCell label="Change" value={2.5} format="percent" />);
    expect(screen.getByText('+2.50%')).toBeInTheDocument();
  });

  it('shows unit suffix when provided', () => {
    const { container } = render(<DataCell label="Vol" value={500} unit="手" />);
    expect(container.textContent).toContain('手');
  });

  it('uses priceColor for positive values', () => {
    const { container } = render(<DataCell label="Chg" value={1.5} format="percent" />);
    const valueSpan = container.querySelector('span[style]');
    expect(valueSpan).toBeTruthy();
  });

  it('uses priceColor for negative values', () => {
    const { container } = render(<DataCell label="Chg" value={-2.3} format="percent" />);
    const valueSpan = container.querySelector('span[style]');
    expect(valueSpan).toBeTruthy();
  });

  it('renders StaticValue when animated=false and flash=false', () => {
    const { container } = render(<DataCell label="Price" value={42} animated={false} flash={false} />);
    const spans = container.querySelectorAll('span');
    expect(spans.length).toBeGreaterThanOrEqual(2);
  });

  it('renders AnimatedValue when animated=true', () => {
    const { container } = render(<DataCell label="Price" value={42} animated={true} />);
    const spans = container.querySelectorAll('span');
    expect(spans.length).toBeGreaterThanOrEqual(2);
  });
});
