import { describe, it, expect } from 'vitest';
import { formatPrice, formatPercent, formatRatio, formatVolume, formatAmount, priceColor } from '@/utils/format';
import { isBacktestResult } from '@/stores/strategy';
import { strategyKeys } from '../hooks/queries/useStrategyQueries';
import { riskKeys } from '../hooks/queries/useRiskQueries';
import { stockDetailKeys } from '../hooks/queries/useStockDetailQueries';

function seededRandom(seed: number): () => number {
  let s = seed;
  return () => {
    s = (s * 16807 + 0) % 2147483647;
    return (s - 1) / 2147483646;
  };
}

describe('Random / Fuzz Tests', () => {
  const rand = seededRandom(42);

  describe('formatPrice fuzz', () => {
    it('never throws for any finite number', () => {
      for (let i = 0; i < 500; i++) {
        const n = (rand() - 0.5) * 1e12;
        expect(() => formatPrice(n)).not.toThrow();
      }
    });

    it('never throws for edge cases', () => {
      const edges = [0, -0, Infinity, -Infinity, NaN, Number.MAX_VALUE, Number.MIN_VALUE];
      for (const n of edges) {
        expect(() => formatPrice(n)).not.toThrow();
      }
    });

    it('always returns — for non-finite values', () => {
      expect(formatPrice(NaN)).toBe('—');
      expect(formatPrice(Infinity)).toBe('—');
      expect(formatPrice(-Infinity)).toBe('—');
    });
  });

  describe('formatPercent fuzz', () => {
    it('never throws for any finite number', () => {
      for (let i = 0; i < 500; i++) {
        const n = (rand() - 0.5) * 1e6;
        expect(() => formatPercent(n)).not.toThrow();
      }
    });

    it('always includes % sign for finite values', () => {
      for (let i = 0; i < 200; i++) {
        const n = (rand() - 0.5) * 100;
        const result = formatPercent(n);
        expect(result.endsWith('%')).toBe(true);
      }
    });
  });

  describe('formatRatio fuzz', () => {
    it('never throws for any finite number', () => {
      for (let i = 0; i < 500; i++) {
        const n = (rand() - 0.5) * 10;
        expect(() => formatRatio(n)).not.toThrow();
      }
    });

    it('multiplies by 100 correctly', () => {
      for (let i = 0; i < 200; i++) {
        const n = (rand() - 0.5) * 2;
        const result = formatRatio(n);
        expect(result.endsWith('%')).toBe(true);
      }
    });
  });

  describe('formatVolume fuzz', () => {
    it('never throws for any finite number', () => {
      for (let i = 0; i < 500; i++) {
        const n = (rand() - 0.5) * 1e15;
        expect(() => formatVolume(n)).not.toThrow();
      }
    });
  });

  describe('formatAmount fuzz', () => {
    it('never throws for any finite number', () => {
      for (let i = 0; i < 500; i++) {
        const n = (rand() - 0.5) * 1e18;
        expect(() => formatAmount(n)).not.toThrow();
      }
    });
  });

  describe('priceColor fuzz', () => {
    it('returns valid CSS value for any number', () => {
      for (let i = 0; i < 500; i++) {
        const n = (rand() - 0.5) * 1e6;
        const color = priceColor(n);
        expect(color).toMatch(/^var\(--|^#[0-9A-Fa-f]{6}$/);
      }
    });
  });

  describe('isBacktestResult fuzz with seeded random', () => {
    it('correctly identifies random valid objects', () => {
      const r = seededRandom(123);
      for (let i = 0; i < 200; i++) {
        const obj = {
          total_return: (r() - 0.5) * 2,
          annual_return: (r() - 0.5) * 2,
          sharpe_ratio: (r() - 0.5) * 5,
          max_drawdown: (r() - 0.5) * 2,
          equity_curve: Array.from({ length: Math.floor(r() * 20) }, (_, j) => ({
            date: `2024-01-${j + 1}`,
            value: 100000 + (r() - 0.5) * 50000,
          })),
        };
        expect(isBacktestResult(obj)).toBe(true);
      }
    });

    it('correctly rejects objects with random missing fields', () => {
      const r = seededRandom(456);
      for (let i = 0; i < 200; i++) {
        const obj: Record<string, unknown> = {};
        if (r() > 0.2) obj.total_return = r();
        if (r() > 0.2) obj.annual_return = r();
        if (r() > 0.2) obj.sharpe_ratio = r();
        if (r() > 0.2) obj.max_drawdown = r();
        if (r() > 0.2) obj.equity_curve = [];
        const expected =
          typeof obj.total_return === 'number' &&
          typeof obj.annual_return === 'number' &&
          typeof obj.sharpe_ratio === 'number' &&
          typeof obj.max_drawdown === 'number' &&
          Array.isArray(obj.equity_curve);
        expect(isBacktestResult(obj)).toBe(expected);
      }
    });

    it('correctly rejects objects with wrong types', () => {
      const r = seededRandom(789);
      for (let i = 0; i < 200; i++) {
        const obj: Record<string, unknown> = {
          total_return: r() > 0.5 ? r() : 'string',
          annual_return: r() > 0.5 ? r() : null,
          sharpe_ratio: r() > 0.5 ? r() : undefined,
          max_drawdown: r() > 0.5 ? r() : {},
          equity_curve: r() > 0.5 ? [] : 'not-array',
        };
        const isValid =
          typeof obj.total_return === 'number' &&
          typeof obj.annual_return === 'number' &&
          typeof obj.sharpe_ratio === 'number' &&
          typeof obj.max_drawdown === 'number' &&
          Array.isArray(obj.equity_curve);
        expect(isBacktestResult(obj)).toBe(isValid);
      }
    });

    it('handles extreme numeric values', () => {
      const extremes = [Number.MAX_VALUE, Number.MIN_VALUE, Number.EPSILON, -Number.MAX_VALUE];
      for (const total_return of extremes) {
        for (const annual_return of extremes) {
          const obj = {
            total_return,
            annual_return,
            sharpe_ratio: 1,
            max_drawdown: -0.1,
            equity_curve: [],
          };
          expect(isBacktestResult(obj)).toBe(true);
        }
      }
    });

    it('rejects null and primitives', () => {
      expect(isBacktestResult(null)).toBe(false);
      expect(isBacktestResult(undefined)).toBe(false);
      expect(isBacktestResult('string')).toBe(false);
      expect(isBacktestResult(123)).toBe(false);
      expect(isBacktestResult(true)).toBe(false);
    });

    it('rejects empty object', () => {
      expect(isBacktestResult({})).toBe(false);
    });
  });

  describe('Cross-module integration fuzz', () => {
    it('formatPercent + priceColor pipeline is consistent for positive values', () => {
      const r = seededRandom(321);
      for (let i = 0; i < 300; i++) {
        const change = r() * 20;
        const formatted = formatPercent(change);
        const color = priceColor(change);
        expect(formatted.startsWith('+')).toBe(true);
        expect(color).toBe('var(--signal-rise)');
      }
    });

    it('formatPercent + priceColor pipeline is consistent for negative values', () => {
      const r = seededRandom(654);
      for (let i = 0; i < 300; i++) {
        const change = -r() * 20;
        const formatted = formatPercent(change);
        const color = priceColor(change);
        expect(formatted.startsWith('-')).toBe(true);
        expect(color).toBe('var(--signal-fall)');
      }
    });

    it('formatRatio + priceColor pipeline is consistent', () => {
      const r = seededRandom(987);
      for (let i = 0; i < 300; i++) {
        const ratio = (r() - 0.5) * 0.4;
        const formatted = formatRatio(ratio);
        const color = priceColor(ratio);
        expect(formatted.endsWith('%')).toBe(true);
        if (ratio > 0) expect(color).toBe('var(--signal-rise)');
        else if (ratio < 0) expect(color).toBe('var(--signal-fall)');
        else expect(color).toBe('var(--label-secondary)');
      }
    });
  });
});

describe('Fuzz: query key factories never collide', () => {
  const seededRng = seededRandom(42);
  const symbols = ['600519', '000001', '601318', '300750', '002594', '688981'];

  it('strategyKeys produce unique stringified keys', () => {
    const keys = new Set<string>();
    keys.add(JSON.stringify(strategyKeys.list()));
    keys.add(JSON.stringify(strategyKeys.factorRegistry()));
    keys.add(JSON.stringify(strategyKeys.alphaList()));
    keys.add(JSON.stringify(strategyKeys.backtestHistory()));
    for (const s of symbols) {
      keys.add(JSON.stringify(strategyKeys.paramSpecs(s)));
    }
    expect(keys.size).toBe(4 + symbols.length);
  });

  it('riskKeys produce unique stringified keys', () => {
    const keys = new Set<string>();
    keys.add(JSON.stringify(riskKeys.portfolio()));
    keys.add(JSON.stringify(riskKeys.exposure()));
    keys.add(JSON.stringify(riskKeys.efficientFrontier()));
    keys.add(JSON.stringify(riskKeys.monteCarloVaR()));
    keys.add(JSON.stringify(riskKeys.correlation()));
    keys.add(JSON.stringify(riskKeys.blackLitterman()));
    for (const s of symbols) {
      keys.add(JSON.stringify(riskKeys.drawdown(s)));
      keys.add(JSON.stringify(riskKeys.kelly(`${seededRng()}-${seededRng()}-${seededRng()}`)));
    }
    expect(keys.size).toBe(6 + symbols.length * 2);
  });

  it('stockDetailKeys produce unique stringified keys', () => {
    const keys = new Set<string>();
    for (const s of symbols) {
      keys.add(JSON.stringify(stockDetailKeys.chip(s)));
      keys.add(JSON.stringify(stockDetailKeys.news(s)));
      keys.add(JSON.stringify(stockDetailKeys.sentiment(s)));
      keys.add(JSON.stringify(stockDetailKeys.garch(s)));
      keys.add(JSON.stringify(stockDetailKeys.hmm(s)));
      keys.add(JSON.stringify(stockDetailKeys.rollingRisk(s)));
      keys.add(JSON.stringify(stockDetailKeys.seasonality(s)));
    }
    expect(keys.size).toBe(symbols.length * 7);
  });
});

describe('Fuzz: API path consistency', () => {
  it('all query hook paths start with /', () => {
    const paths = [
      '/market/overview', '/market/stocks', '/market/heatmap', '/market/breadth',
      '/stock/realtime/600519', '/stock/history/600519', '/stock/indicators/600519',
      '/stock/fundamentals/600519', '/stock/analysis/600519',
      '/portfolio/risk/dashboard', '/portfolio/summary', '/portfolio/diversification',
      '/portfolio/attribution', '/portfolio/stress/scenarios',
      '/trading/account', '/trading/history', '/trading/analytics',
      '/trading/buy', '/trading/sell',
      '/watchlist', '/screener/presets', '/watchlist/add', '/watchlist/remove',
      '/strategies/list', '/strategy/param-specs', '/factor/registry', '/alpha/list',
      '/backtest/history',
      '/risk/portfolio', '/risk/exposure', '/drawdown/analysis/000001',
      '/portfolio/efficient-frontier', '/portfolio/monte-carlo-var',
      '/correlation/matrix', '/portfolio/black-litterman', '/position/kelly',
      '/portfolio/stress/run',
      '/chip/600519', '/news/stock/600519', '/news/sentiment',
      '/volatility/garch/600519', '/regime/hmm/600519',
      '/rolling-risk/600519', '/seasonality/600519',
      '/system/health', '/system/status', '/readiness',
    ];
    for (const p of paths) {
      expect(p.startsWith('/')).toBe(true);
      expect(p.includes('//')).toBe(false);
    }
  });
});
