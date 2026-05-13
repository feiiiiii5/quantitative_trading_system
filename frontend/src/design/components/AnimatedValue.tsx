import { memo, useMemo } from 'react';
import { useCountUp } from '@/hooks/useCountUp';
import { useTickFlash } from '@/hooks/useTickFlash';
import { colors } from '@/design/tokens/colors';
import { formatPrice, formatPercent, formatRatio, formatVolume, formatAmount, priceColor } from '@/utils/format';

interface AnimatedValueProps {
  value: number | string;
  format: 'price' | 'percent' | 'ratio' | 'volume' | 'amount' | 'raw';
  compareValue?: number;
  size: 'xs' | 'sm' | 'md' | 'lg' | 'xl';
  animated: boolean;
  flash: boolean;
  unit?: string;
  align?: 'left' | 'right' | 'center';
}

const valueStyle: Record<string, { fontSize: number; fontWeight: number; fontFamily: string; fontVariantNumeric: string }> = {
  xs: { fontSize: 12, fontWeight: 500, fontFamily: 'var(--font-mono)', fontVariantNumeric: 'tabular-nums' },
  sm: { fontSize: 13, fontWeight: 500, fontFamily: 'var(--font-mono)', fontVariantNumeric: 'tabular-nums' },
  md: { fontSize: 15, fontWeight: 600, fontFamily: 'var(--font-mono)', fontVariantNumeric: 'tabular-nums' },
  lg: { fontSize: 18, fontWeight: 600, fontFamily: 'var(--font-mono)', fontVariantNumeric: 'tabular-nums' },
  xl: { fontSize: 24, fontWeight: 700, fontFamily: 'var(--font-mono)', fontVariantNumeric: 'tabular-nums' },
};

function formatValue(val: number, fmt: AnimatedValueProps['format']): string {
  switch (fmt) {
    case 'price': return formatPrice(val);
    case 'percent': return formatPercent(val);
    case 'ratio': return formatRatio(val);
    case 'volume': return formatVolume(val);
    case 'amount': return formatAmount(val);
    default: return String(val);
  }
}

export const AnimatedValue = memo(function AnimatedValue(props: AnimatedValueProps) {
  const { value, format: fmt, compareValue, size, animated, flash, unit, align } = props;
  const numVal = typeof value === 'number' ? value : parseFloat(value as string);
  const compare = compareValue ?? (fmt === 'percent' || fmt === 'ratio' ? numVal : 0);
  const color = isNaN(compare) ? 'var(--label-primary)' : priceColor(compare);

  const countUpValue = useCountUp(numVal);
  const tickFlash = useTickFlash(numVal);
  const displayed = animated && !isNaN(numVal) ? countUpValue : numVal;
  const flashState = flash && !isNaN(numVal) ? tickFlash : null;

  const formatted = useMemo(() => {
    if (isNaN(numVal)) return String(value);
    return formatValue(displayed, fmt);
  }, [fmt, displayed, value, numVal]);

  return (
    <span style={{
      ...valueStyle[size],
      color,
      background: flashState === 'up' ? colors.market.riseDim :
                  flashState === 'down' ? colors.market.fallDim : 'transparent',
      transition: 'background 600ms ease-out, color 200ms',
      padding: '0 2px',
      borderRadius: 2,
      textAlign: align,
    }}>
      {formatted}
      {unit && <span style={{ fontSize: '0.7em', opacity: 0.6, marginLeft: 2 }}>{unit}</span>}
    </span>
  );
});

export const StaticValue = memo(function StaticValue(props: AnimatedValueProps) {
  const { value, format: fmt, compareValue, size, unit, align } = props;
  const numVal = typeof value === 'number' ? value : parseFloat(value as string);
  const compare = compareValue ?? (fmt === 'percent' || fmt === 'ratio' ? numVal : 0);
  const color = isNaN(compare) ? 'var(--label-primary)' : priceColor(compare);

  const formatted = useMemo(() => {
    if (isNaN(numVal)) return String(value);
    return formatValue(numVal, fmt);
  }, [fmt, numVal, value]);

  return (
    <span style={{
      ...valueStyle[size],
      color,
      padding: '0 2px',
      borderRadius: 2,
      textAlign: align,
    }}>
      {formatted}
      {unit && <span style={{ fontSize: '0.7em', opacity: 0.6, marginLeft: 2 }}>{unit}</span>}
    </span>
  );
});
