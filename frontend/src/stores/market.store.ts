import { defineStore } from 'pinia'
import { api } from '../api'

export const useMarketStore = defineStore('market', {
  state: () => ({
    overview: null as any,
    status: {} as Record<string, any>,
    lastUpdate: 0,
    isLoading: false,
  }),
  getters: {
    cnIndices: (state) => state.overview?.cn_indices ?? {},
    temperature: (state) => state.overview?.temperature ?? 50,
    isMarketOpen: (state) => Object.values(state.status).some((s: any) => s.is_open),
  },
  actions: {
    async fetchOverview() {
      this.isLoading = true
      try {
        const data = await api.getMarketOverview()
        if (data) {
          this.overview = data
          this.lastUpdate = Date.now()
        }
      } catch (e) {
        console.error('Fetch market overview error:', e)
      } finally {
        this.isLoading = false
      }
    },
    async fetchStatus() {
      try {
        const data = await api.getMarketStatus()
        if (data) this.status = data
      } catch (e) {
        console.error('Fetch market status error:', e)
      }
    },
    startAutoRefresh(intervalMs = 5000) {
      this.fetchOverview()
      this.fetchStatus()
      this._timer = window.setInterval(() => {
        this.fetchOverview()
        this.fetchStatus()
      }, intervalMs)
    },
    stopAutoRefresh() {
      if (this._timer) {
        clearInterval(this._timer)
        this._timer = null
      }
    },
    _timer: null as any,
  },
})
