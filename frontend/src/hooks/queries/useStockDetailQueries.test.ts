import { describe, it, expect } from 'vitest';
import { stockDetailKeys } from './useStockDetailQueries';

describe('stockDetailKeys', () => {
  it('chip includes symbol', () => {
    expect(stockDetailKeys.chip('600519')).toEqual(['stock-detail', 'chip', '600519']);
  });

  it('news includes symbol', () => {
    expect(stockDetailKeys.news('000001')).toEqual(['stock-detail', 'news', '000001']);
  });

  it('sentiment includes symbol', () => {
    expect(stockDetailKeys.sentiment('600519')).toEqual(['stock-detail', 'sentiment', '600519']);
  });

  it('garch includes symbol', () => {
    expect(stockDetailKeys.garch('000001')).toEqual(['stock-detail', 'garch', '000001']);
  });

  it('hmm includes symbol', () => {
    expect(stockDetailKeys.hmm('600519')).toEqual(['stock-detail', 'hmm', '600519']);
  });

  it('rollingRisk includes symbol', () => {
    expect(stockDetailKeys.rollingRisk('000001')).toEqual(['stock-detail', 'rolling-risk', '000001']);
  });

  it('seasonality includes symbol', () => {
    expect(stockDetailKeys.seasonality('600519')).toEqual(['stock-detail', 'seasonality', '600519']);
  });

  it('different symbols produce different keys', () => {
    expect(stockDetailKeys.chip('600519')).not.toEqual(stockDetailKeys.chip('000001'));
  });
});
