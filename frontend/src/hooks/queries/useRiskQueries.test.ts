import { describe, it, expect } from 'vitest';
import { riskKeys } from './useRiskQueries';

describe('riskKeys', () => {
  it('portfolio returns stable key', () => {
    expect(riskKeys.portfolio()).toEqual(['risk', 'portfolio']);
  });

  it('exposure returns stable key', () => {
    expect(riskKeys.exposure()).toEqual(['risk', 'exposure']);
  });

  it('drawdown includes symbol', () => {
    expect(riskKeys.drawdown('000001')).toEqual(['risk', 'drawdown', '000001']);
  });

  it('efficientFrontier returns stable key', () => {
    expect(riskKeys.efficientFrontier()).toEqual(['risk', 'efficient-frontier']);
  });

  it('monteCarloVaR returns stable key', () => {
    expect(riskKeys.monteCarloVaR()).toEqual(['risk', 'monte-carlo-var']);
  });

  it('correlation returns stable key', () => {
    expect(riskKeys.correlation()).toEqual(['risk', 'correlation']);
  });

  it('blackLitterman returns stable key', () => {
    expect(riskKeys.blackLitterman()).toEqual(['risk', 'black-litterman']);
  });

  it('kelly includes params string', () => {
    expect(riskKeys.kelly('0.6-2-1')).toEqual(['risk', 'kelly', '0.6-2-1']);
  });

  it('drawdown with different symbols produce different keys', () => {
    expect(riskKeys.drawdown('000001')).not.toEqual(riskKeys.drawdown('600519'));
  });
});
