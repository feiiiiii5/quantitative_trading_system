import { describe, it, expect } from 'vitest';
import { stockKeys } from './useStockQueries';
import { portfolioKeys } from './usePortfolioQueries';
import { watchlistKeys } from './useWatchlistQueries';
import { tradingKeys } from './useTradingQueries';
import { systemKeys } from './useSystemQueries';

describe('Query key stability', () => {
  it('stockKeys generate stable keys', () => {
    expect(stockKeys.detail('sh600519')).toEqual(['stock', 'detail', 'sh600519']);
    expect(stockKeys.history('sh600519', '1y')).toEqual(['stock', 'history', 'sh600519', '1y']);
    expect(stockKeys.indicators('sh600519')).toEqual(['stock', 'indicators', 'sh600519']);
  });

  it('portfolioKeys generate stable keys', () => {
    expect(portfolioKeys.riskDashboard()).toEqual(['portfolio', 'risk', 'dashboard']);
    expect(portfolioKeys.summary()).toEqual(['portfolio', 'summary']);
    expect(portfolioKeys.holdings()).toEqual(['portfolio', 'holdings']);
  });

  it('watchlistKeys generate stable keys', () => {
    expect(watchlistKeys.list()).toEqual(['watchlist', 'list']);
    expect(watchlistKeys.screener()).toEqual(['watchlist', 'screener']);
  });

  it('tradingKeys generate stable keys', () => {
    expect(tradingKeys.account()).toEqual(['trading', 'account']);
    expect(tradingKeys.history()).toEqual(['trading', 'history']);
  });

  it('systemKeys generate stable keys', () => {
    expect(systemKeys.health()).toEqual(['system', 'health']);
    expect(systemKeys.status()).toEqual(['system', 'status']);
  });

  it('keys are unique across domains', () => {
    const allKeys = [
      stockKeys.detail('sh600519'),
      portfolioKeys.riskDashboard(),
      watchlistKeys.list(),
      tradingKeys.account(),
      systemKeys.health(),
    ];
    const serialized = allKeys.map(k => JSON.stringify(k));
    expect(new Set(serialized).size).toBe(allKeys.length);
  });
});

describe('Query key fuzz', () => {
  const symbols = ['sh600519', 'sz000001', 'sh000001', 'sz399001', 'sh688001'];

  it('stockKeys produce unique keys for different symbols', () => {
    const keys = symbols.map(s => JSON.stringify(stockKeys.detail(s)));
    expect(new Set(keys).size).toBe(symbols.length);
  });

  it('stockKeys produce unique keys for different periods', () => {
    const periods = ['1m', '3m', '6m', '1y', '3y'];
    const keys = periods.map(p => JSON.stringify(stockKeys.history('sh600519', p)));
    expect(new Set(keys).size).toBe(periods.length);
  });
});
