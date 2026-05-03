import { defineStore } from 'pinia'
import { ref } from 'vue'
import { api } from '@/api'
import type { WatchlistData, StockQuote, PriceAlert } from '@/types'

export const useWatchlistStore = defineStore('watchlist', () => {
  const symbols = ref<string[]>([])
  const quotes = ref<Record<string, StockQuote>>({})
  const alerts = ref<PriceAlert[]>([])
  const loading = ref(false)

  async function fetchWatchlist() {
    loading.value = true
    try {
      const data: WatchlistData = await api.watchlist.get()
      symbols.value = data.symbols
      quotes.value = data.quotes
    } finally {
      loading.value = false
    }
  }

  async function addSymbol(symbol: string) {
    try {
      await api.watchlist.add(symbol)
      await fetchWatchlist()
    } catch (e) {
      console.error('Add watchlist error:', e)
    }
  }

  async function removeSymbol(symbol: string) {
    try {
      await api.watchlist.remove(symbol)
      await fetchWatchlist()
    } catch (e) {
      console.error('Remove watchlist error:', e)
    }
  }

  async function fetchAlerts(): Promise<PriceAlert[]> {
    try {
      alerts.value = await api.watchlist.alerts()
      return alerts.value
    } catch (e) {
      console.error('Fetch alerts error:', e)
      return []
    }
  }

  return { symbols, quotes, alerts, loading, fetchWatchlist, addSymbol, removeSymbol, fetchAlerts }
})
