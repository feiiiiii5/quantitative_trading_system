import { describe, it, expect } from 'vitest';
import { marketKeys } from './useMarketQueries';

describe('marketKeys', () => {
  it('generates stable query keys', () => {
    expect(marketKeys.overview()).toEqual(['market', 'overview']);
    expect(marketKeys.stocks('A')).toEqual(['market', 'stocks', 'A']);
    expect(marketKeys.breadth('sh600519,sh000001')).toEqual(['market', 'breadth', 'sh600519,sh000001']);
  });
});
