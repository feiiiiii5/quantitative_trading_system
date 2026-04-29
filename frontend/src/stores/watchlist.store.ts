import { defineStore } from 'pinia'
import { api } from '../api'

export const useWatchlistStore = defineStore('watchlist', {
  state: () => ({
    symbols: [] as string[],
    quotes: {} as Record<string, any>,
    loading: false,
  }),
  actions: {
    async fetch() {
      this.loading = true
      try {
        const data = await api.getWatchlist()
        if (data) {
          this.symbols = Array.isArray(data) ? data : (data.symbols || [])
        }
      } catch (e) {
        console.error('Fetch watchlist error:', e)
      } finally {
        this.loading = false
      }
    },
    async add(symbol: string) {
      try {
        await api.addToWatchlist(symbol)
        if (!this.symbols.includes(symbol)) {
          this.symbols.push(symbol)
        }
      } catch (e) {
        console.error('Add watchlist error:', e)
      }
    },
    async remove(symbol: string) {
      try {
        await api.removeFromWatchlist(symbol)
        this.symbols = this.symbols.filter(s => s !== symbol)
        delete this.quotes[symbol]
      } catch (e) {
        console.error('Remove watchlist error:', e)
      }
    },
    async refreshQuotes() {
      if (this.symbols.length === 0) return
      try {
        const data = await api.getRealtimeBatch(this.symbols.slice(0, 30))
        if (data) this.quotes = { ...this.quotes, ...data }
      } catch (e) {
        console.error('Refresh quotes error:', e)
      }
    },
  },
})
