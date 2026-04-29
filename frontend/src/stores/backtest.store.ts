import { defineStore } from 'pinia'
import { api } from '../api'

export const useBacktestStore = defineStore('backtest', {
  state: () => ({
    results: null as any,
    history: [] as any[],
    running: false,
    progress: 0,
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
          params.monteCarlo || false,
          params.nSimulations || 500,
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

    async compare(id1: string, id2: string) {
      // TODO: 实现回测结果对比
    },
  },
})
