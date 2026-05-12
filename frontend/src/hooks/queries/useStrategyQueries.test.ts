import { describe, it, expect } from 'vitest';
import { strategyKeys } from './useStrategyQueries';

describe('strategyKeys', () => {
  it('list returns stable key', () => {
    expect(strategyKeys.list()).toEqual(['strategy', 'list']);
  });

  it('paramSpecs includes strategy name', () => {
    expect(strategyKeys.paramSpecs('dual_ma')).toEqual(['strategy', 'param-specs', 'dual_ma']);
  });

  it('factorRegistry returns stable key', () => {
    expect(strategyKeys.factorRegistry()).toEqual(['strategy', 'factor-registry']);
  });

  it('alphaList returns stable key', () => {
    expect(strategyKeys.alphaList()).toEqual(['strategy', 'alpha-list']);
  });

  it('backtestHistory returns stable key', () => {
    expect(strategyKeys.backtestHistory()).toEqual(['strategy', 'backtest-history']);
  });

  it('paramSpecs with different strategies produce different keys', () => {
    expect(strategyKeys.paramSpecs('dual_ma')).not.toEqual(strategyKeys.paramSpecs('macd'));
  });
});
