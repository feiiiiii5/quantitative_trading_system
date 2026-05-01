import { defineStore } from 'pinia'
import { api } from '../api'

export const useBacktestStore = defineStore('backtest', {
  state: () => ({
    results: null as any,
    history: [] as any[],
    running: false,
    progress: 0,
    compareResult: null as any,
  }),
  actions: {
    async runBacktest(params: {
      symbol: string
      strategyName?: string
      startDate?: string
      endDate?: string
      initialCapital?: number
      monteCarlo?: boolean
      nSimulations?: number
    }) {
      this.running = true
      this.progress = 0
      this.results = null
      try {
        const progressSim = window.setInterval(() => {
          if (this.progress < 90) this.progress += Math.random() * 15
        }, 500)

        const data = await api.runBacktest(
          params.symbol,
          params.strategyName || 'adaptive',
          params.startDate || '2022-01-01',
          params.endDate || '2024-12-31',
          params.initialCapital || 1000000,
          {
            monte_carlo: params.monteCarlo || false,
            n_simulations: params.nSimulations || 500,
          }
        )

        clearInterval(progressSim)
        this.progress = 100
        this.results = data

        await this.loadHistory()
      } catch (e) {
        console.error('Run backtest error:', e)
      } finally {
        this.running = false
      }
    },

    cancelBacktest() {
      this.running = false
      this.progress = 0
    },

    async loadHistory(symbol?: string) {
      try {
        const data = await api.getBacktestHistory(symbol, 20)
        if (data) this.history = Array.isArray(data) ? data : []
      } catch (e) {
        console.error('Load backtest history error:', e)
      }
    },

    compare(id1: number, id2: number) {
      const r1 = this.history[id1]
      const r2 = this.history[id2]
      if (!r1 || !r2) {
        this.compareResult = null
        return
      }
      const d1 = r1.data || r1
      const d2 = r2.data || r2
      this.compareResult = {
        left: { symbol: r1.symbol || d1.symbol || '', strategy: r1.strategy || d1.strategy_name || '', data: d1 },
        right: { symbol: r2.symbol || d2.symbol || '', strategy: r2.strategy || d2.strategy_name || '', data: d2 },
      }
    },

    clearCompare() {
      this.compareResult = null
    },
  },
})
