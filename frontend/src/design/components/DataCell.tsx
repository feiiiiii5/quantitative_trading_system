import { memo } from 'react';
import { AnimatedValue, StaticValue } from './AnimatedValue';

interface DataCellProps {
  label: string;
  value: number | string;
  format?: 'price' | 'percent' | 'ratio' | 'volume' | 'amount' | 'raw';
  compareValue?: number;
  unit?: string;
  size?: 'xs' | 'sm' | 'md' | 'lg' | 'xl';
  animated?: boolean;
  flash?: boolean;
  align?: 'left' | 'right' | 'center';
}

const labelStyle: Record<string, { fontSize: number; color: string; fontFamily: string }> = {
  xs: { fontSize: 9, color: 'var(--label-tertiary)', fontFamily: 'var(--font-mono)' },
  sm: { fontSize: 10, color: 'var(--label-tertiary)', fontFamily: 'var(--font-mono)' },
  md: { fontSize: 11, color: 'var(--label-tertiary)', fontFamily: 'var(--font-mono)' },
  lg: { fontSize: 12, color: 'var(--label-secondary)', fontFamily: 'var(--font-mono)' },
  xl: { fontSize: 13, color: 'var(--label-secondary)', fontFamily: 'var(--font-mono)' },
};

export const DataCell = memo(function DataCell(props: DataCellProps) {
  const { label, format = 'raw', size = 'md', animated, flash, align = 'left' } = props;
  const ValueComponent = (animated || flash) ? AnimatedValue : StaticValue;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 2, textAlign: align }}>
      <span style={labelStyle[size]}>{label}</span>
      <ValueComponent {...props} format={format} size={size} align={align} animated={animated ?? false} flash={flash ?? false} />
    </div>
  );
});
