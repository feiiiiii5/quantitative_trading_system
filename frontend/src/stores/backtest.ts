import { defineStore } from 'pinia'
import { ref } from 'vue'
import { api } from '@/api'
import type { StrategyInfo, BacktestResult } from '@/types'

export const useBacktestStore = defineStore('backtest', () => {
  const strategies = ref<Record<string, StrategyInfo>>({})
  const currentResult = ref<BacktestResult | null>(null)
  const compareResults = ref<BacktestResult[]>([])
  const loading = ref(false)

  async function fetchStrategies() {
    try {
      strategies.value = await api.backtest.strategies()
    } catch (e) {
      console.error('Fetch strategies error:', e)
    }
  }

  async function runBacktest(params: { symbol: string; strategy_type?: string; start_date?: string; end_date?: string; initial_capital?: number }) {
    loading.value = true
    try {
      currentResult.value = await api.backtest.run(params)
    } catch (e) {
      console.error('Run backtest error:', e)
      throw e
    } finally {
      loading.value = false
    }
  }

  async function compareStrategies(symbol: string) {
    loading.value = true
    try {
      compareResults.value = await api.backtest.compare(symbol)
    } catch (e) {
      console.error('Compare strategies error:', e)
    } finally {
      loading.value = false
    }
  }

  return { strategies, currentResult, compareResults, loading, fetchStrategies, runBacktest, compareStrategies }
})
