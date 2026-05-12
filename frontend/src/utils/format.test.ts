import { describe, it, expect } from 'vitest';
import { formatPrice, formatPercent, formatRatio, formatVolume, formatAmount, priceColor, priceClass } from '@/utils/format';

function seededRandom(seed: number): () => number {
  let s = seed;
  return () => {
    s = (s * 16807 + 0) % 2147483647;
    return (s - 1) / 2147483646;
  };
}

describe('formatPrice', () => {
  it('formats normal price', () => {
    expect(formatPrice(123.456)).toBe('123.46');
  });

  it('formats zero', () => {
    expect(formatPrice(0)).toBe('0.00');
  });

  it('formats negative price', () => {
    expect(formatPrice(-5.5)).toBe('-5.50');
  });

  it('returns — for NaN', () => {
    expect(formatPrice(NaN)).toBe('—');
  });

  it('returns — for Infinity', () => {
    expect(formatPrice(Infinity)).toBe('—');
    expect(formatPrice(-Infinity)).toBe('—');
  });

  it('formats very small numbers', () => {
    expect(formatPrice(0.001)).toBe('0.00');
  });

  it('formats very large numbers', () => {
    const result = formatPrice(1e15);
    expect(result).toContain('1,000,000,000,000,000');
  });
});

describe('formatPercent', () => {
  it('formats positive percent', () => {
    expect(formatPercent(5.23)).toBe('+5.23%');
  });

  it('formats negative percent', () => {
    expect(formatPercent(-3.12)).toBe('-3.12%');
  });

  it('formats zero percent', () => {
    expect(formatPercent(0)).toBe('+0.00%');
  });

  it('returns — for NaN', () => {
    expect(formatPercent(NaN)).toBe('—');
  });

  it('returns — for Infinity', () => {
    expect(formatPercent(Infinity)).toBe('—');
  });
});

describe('formatRatio', () => {
  it('converts ratio to percent', () => {
    expect(formatRatio(0.0523)).toBe('+5.23%');
  });

  it('handles negative ratio', () => {
    expect(formatRatio(-0.08)).toBe('-8.00%');
  });

  it('handles zero', () => {
    expect(formatRatio(0)).toBe('+0.00%');
  });

  it('returns — for NaN', () => {
    expect(formatRatio(NaN)).toBe('—');
  });
});

describe('formatVolume', () => {
  it('formats small volume', () => {
    expect(formatVolume(500)).toBe('500');
  });

  it('formats wan volume', () => {
    expect(formatVolume(12_500)).toBe('1.25万');
  });

  it('formats yi volume', () => {
    expect(formatVolume(150_000_000)).toBe('1.50亿');
  });

  it('formats negative volume', () => {
    expect(formatVolume(-25_000)).toBe('-2.50万');
  });

  it('returns — for NaN', () => {
    expect(formatVolume(NaN)).toBe('—');
  });
});

describe('formatAmount', () => {
  it('formats small amount', () => {
    expect(formatAmount(800)).toBe('800');
  });

  it('formats wan amount', () => {
    expect(formatAmount(25_000)).toBe('2.50万');
  });

  it('formats yi amount', () => {
    expect(formatAmount(3_500_000_000)).toBe('35.00亿');
  });

  it('formats wan yi amount', () => {
    expect(formatAmount(1.5e12)).toBe('1.50万亿');
  });

  it('returns — for NaN', () => {
    expect(formatAmount(NaN)).toBe('—');
  });
});

describe('priceColor', () => {
  it('returns rise var for positive', () => {
    expect(priceColor(0.01)).toBe('var(--signal-rise)');
  });

  it('returns fall var for negative', () => {
    expect(priceColor(-0.01)).toBe('var(--signal-fall)');
  });

  it('returns neutral var for zero', () => {
    expect(priceColor(0)).toBe('var(--label-secondary)');
  });
});

describe('priceClass', () => {
  it('returns rise class for positive', () => {
    expect(priceClass(0.01)).toBe('price-rise');
  });

  it('returns fall class for negative', () => {
    expect(priceClass(-0.01)).toBe('price-fall');
  });

  it('returns flat class for zero', () => {
    expect(priceClass(0)).toBe('price-flat');
  });
});

describe('Fuzz: format functions never throw', () => {
  const r = seededRandom(999);

  it('formatPrice handles all finite numbers', () => {
    for (let i = 0; i < 1000; i++) {
      const n = (r() - 0.5) * 1e15;
      expect(() => formatPrice(n)).not.toThrow();
    }
  });

  it('formatPercent handles all finite numbers', () => {
    for (let i = 0; i < 1000; i++) {
      const n = (r() - 0.5) * 1e6;
      expect(() => formatPercent(n)).not.toThrow();
    }
  });

  it('formatRatio handles all finite numbers', () => {
    for (let i = 0; i < 1000; i++) {
      const n = (r() - 0.5) * 100;
      expect(() => formatRatio(n)).not.toThrow();
    }
  });

  it('formatVolume handles all finite numbers', () => {
    for (let i = 0; i < 1000; i++) {
      const n = (r() - 0.5) * 1e18;
      expect(() => formatVolume(n)).not.toThrow();
    }
  });

  it('formatAmount handles all finite numbers', () => {
    for (let i = 0; i < 1000; i++) {
      const n = (r() - 0.5) * 1e20;
      expect(() => formatAmount(n)).not.toThrow();
    }
  });

  it('all functions handle edge values', () => {
    const edges = [0, -0, NaN, Infinity, -Infinity, Number.MAX_VALUE, Number.MIN_VALUE, Number.EPSILON, -Number.MAX_VALUE];
    for (const n of edges) {
      expect(() => formatPrice(n)).not.toThrow();
      expect(() => formatPercent(n)).not.toThrow();
      expect(() => formatRatio(n)).not.toThrow();
      expect(() => formatVolume(n)).not.toThrow();
      expect(() => formatAmount(n)).not.toThrow();
    }
  });
});

describe('Fuzz: formatPercent + priceColor consistency', () => {
  const r = seededRandom(777);

  it('positive change always has + sign and rise color', () => {
    for (let i = 0; i < 500; i++) {
      const change = r() * 100;
      const formatted = formatPercent(change);
      const color = priceColor(change);
      expect(formatted.startsWith('+')).toBe(true);
      expect(color).toBe('var(--signal-rise)');
    }
  });

  it('negative change always has - sign and fall color', () => {
    for (let i = 0; i < 500; i++) {
      const change = -r() * 100;
      const formatted = formatPercent(change);
      const color = priceColor(change);
      expect(formatted.startsWith('-')).toBe(true);
      expect(color).toBe('var(--signal-fall)');
    }
  });

  it('zero change has + sign and neutral color', () => {
    expect(formatPercent(0)).toBe('+0.00%');
    expect(priceColor(0)).toBe('var(--label-secondary)');
  });
});

describe('Fuzz: formatVolume boundary transitions', () => {
  it('correctly transitions at 10000 boundary', () => {
    expect(formatVolume(9999)).not.toContain('万');
    expect(formatVolume(10000)).toContain('万');
  });

  it('correctly transitions at 100000000 boundary', () => {
    expect(formatVolume(99_999_999)).toContain('万');
    expect(formatVolume(100_000_000)).toContain('亿');
  });
});

describe('Fuzz: formatAmount boundary transitions', () => {
  it('correctly transitions at all boundaries', () => {
    expect(formatAmount(9999)).not.toContain('万');
    expect(formatAmount(10000)).toContain('万');
    expect(formatAmount(99_999_999)).toContain('万');
    expect(formatAmount(100_000_000)).toContain('亿');
    expect(formatAmount(999_999_999_999)).toContain('亿');
    expect(formatAmount(1e12)).toContain('万亿');
  });
});
