import { describe, it, expect, vi, beforeEach } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useBacktestStore } from '@/stores/backtest'
import type { StrategyInfo, BacktestResult } from '@/types'

vi.mock('@/api', () => ({
  api: {
    backtest: {
      strategies: vi.fn(),
      run: vi.fn(),
      compare: vi.fn(),
    },
  },
}))

import { api } from '@/api'

const mockStrategy: Record<string, StrategyInfo> = {
  adaptive: { name: 'Adaptive', type: 'adaptive', param_space: { period: { min: 5, max: 30, step: 1 } }, difficulty: 'PRO' },
}

const mockResult: BacktestResult = {
  strategy_name: 'Adaptive',
  total_return: 0.15,
  annual_return: 0.12,
  sharpe_ratio: 1.2,
  max_drawdown: 0.08,
  win_rate: 0.6,
  profit_factor: 1.5,
  total_trades: 42,
}

describe('useBacktestStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('initializes with empty state', () => {
    const store = useBacktestStore()
    expect(store.loading).toBe(false)
    expect(store.error).toBe('')
    expect(store.currentResult).toBeNull()
    expect(store.compareResults).toHaveLength(0)
  })

  it('fetchStrategies populates strategies on success', async () => {
    vi.mocked(api.backtest.strategies).mockResolvedValue(mockStrategy)
    const store = useBacktestStore()
    await store.fetchStrategies()
    expect(store.strategies).toEqual(mockStrategy)
    expect(store.error).toBe('')
  })

  it('fetchStrategies sets error on failure', async () => {
    vi.mocked(api.backtest.strategies).mockRejectedValue(new Error('Network error'))
    const store = useBacktestStore()
    await store.fetchStrategies()
    expect(store.error).toBe('Network error')
  })

  it('runBacktest sets currentResult on success', async () => {
    vi.mocked(api.backtest.run).mockResolvedValue(mockResult)
    const store = useBacktestStore()
    await store.runBacktest({ symbol: '600519' })
    expect(store.currentResult).toEqual(mockResult)
    expect(store.loading).toBe(false)
  })

  it('runBacktest sets error on failure', async () => {
    vi.mocked(api.backtest.run).mockRejectedValue(new Error('Backtest failed'))
    const store = useBacktestStore()
    await expect(store.runBacktest({ symbol: '600519' })).rejects.toThrow('Backtest failed')
    expect(store.error).toBe('Backtest failed')
    expect(store.loading).toBe(false)
  })

  it('compareStrategies populates compareResults', async () => {
    vi.mocked(api.backtest.compare).mockResolvedValue([mockResult])
    const store = useBacktestStore()
    await store.compareStrategies('600519')
    expect(store.compareResults).toHaveLength(1)
  })

  it('clearError resets error', async () => {
    vi.mocked(api.backtest.strategies).mockRejectedValue(new Error('fail'))
    const store = useBacktestStore()
    await store.fetchStrategies()
    expect(store.error).toBe('fail')
    store.clearError()
    expect(store.error).toBe('')
  })
})
