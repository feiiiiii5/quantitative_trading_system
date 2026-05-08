import { defineStore } from 'pinia'
import { ref, shallowRef, triggerRef } from 'vue'
import { api } from '@/api'
import type { StrategyInfo, BacktestResult } from '@/types'

export const useBacktestStore = defineStore('backtest', () => {
  const strategies = ref<Record<string, StrategyInfo>>({})
  const currentResult = shallowRef<BacktestResult | null>(null)
  const compareResults = shallowRef<BacktestResult[]>([])
  const loading = ref(false)
  const error = ref('')
  let _runId = 0

  function clearError() {
    error.value = ''
  }

  async function fetchStrategies() {
    error.value = ''
    try {
      strategies.value = await api.backtest.strategies()
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : '获取策略列表失败'
    }
  }

  async function runBacktest(params: { symbol: string; strategy_type?: string; start_date?: string; end_date?: string; initial_capital?: number }) {
    const thisRun = ++_runId
    loading.value = true
    error.value = ''
    try {
      const result = await api.backtest.run(params)
      if (thisRun !== _runId) return
      currentResult.value = result
      triggerRef(currentResult)
    } catch (e: unknown) {
      if (thisRun !== _runId) return
      error.value = e instanceof Error ? e.message : '回测运行失败'
      throw e
    } finally {
      if (thisRun === _runId) loading.value = false
    }
  }

  async function compareStrategies(symbol: string) {
    const thisRun = ++_runId
    loading.value = true
    error.value = ''
    try {
      const result = await api.backtest.compare(symbol)
      if (thisRun !== _runId) return
      compareResults.value = result
      triggerRef(compareResults)
    } catch (e: unknown) {
      if (thisRun !== _runId) return
      error.value = e instanceof Error ? e.message : '策略对比失败'
    } finally {
      if (thisRun === _runId) loading.value = false
    }
  }

  return { strategies, currentResult, compareResults, loading, error, clearError, fetchStrategies, runBacktest, compareStrategies }
})
