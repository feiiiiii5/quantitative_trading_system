import { defineStore } from 'pinia'
import { ref, shallowRef, triggerRef, watch, onScopeDispose } from 'vue'
import { api } from '@/api'
import { useWebSocketStore } from '@/stores/websocket'
import type { WatchlistData, StockQuote, PriceAlert } from '@/types'

export const useWatchlistStore = defineStore('watchlist', () => {
  const symbols = ref<string[]>([])
  const quotes = shallowRef<Record<string, StockQuote>>({})
  const alerts = shallowRef<PriceAlert[]>([])
  const loading = ref(false)
  const error = ref('')
  let _fetchId = 0
  let _pollTimer: ReturnType<typeof setInterval> | null = null
  const POLL_INTERVAL_MS = 30_000

  function clearError() {
    error.value = ''
  }

  async function fetchWatchlist() {
    const thisFetch = ++_fetchId
    loading.value = true
    error.value = ''
    try {
      const data: WatchlistData = await api.watchlist.get()
      if (thisFetch !== _fetchId) return
      symbols.value = data.symbols
      quotes.value = data.quotes
      triggerRef(quotes)
    } catch (e: unknown) {
      if (thisFetch !== _fetchId) return
      error.value = e instanceof Error ? e.message : '获取自选股失败'
    } finally {
      if (thisFetch === _fetchId) loading.value = false
    }
  }

  async function addSymbol(symbol: string) {
    error.value = ''
    try {
      await api.watchlist.add(symbol)
      await fetchWatchlist()
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : '添加自选股失败'
    }
  }

  async function removeSymbol(symbol: string) {
    error.value = ''
    try {
      await api.watchlist.remove(symbol)
      await fetchWatchlist()
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : '移除自选股失败'
    }
  }

  async function fetchAlerts(): Promise<PriceAlert[]> {
    const thisFetch = ++_fetchId
    error.value = ''
    try {
      const result = await api.watchlist.alerts()
      if (thisFetch !== _fetchId) return []
      alerts.value = result
      triggerRef(alerts)
      return result
    } catch (e: unknown) {
      if (thisFetch !== _fetchId) return []
      error.value = e instanceof Error ? e.message : '获取提醒失败'
      return []
    }
  }

  function startPolling() {
    stopPolling()
    _pollTimer = setInterval(fetchWatchlist, POLL_INTERVAL_MS)
  }

  function stopPolling() {
    if (_pollTimer) {
      clearInterval(_pollTimer)
      _pollTimer = null
    }
  }

  const wsStore = useWebSocketStore()

  function onQuote(data: Record<string, unknown>) {
    const symbol = String(data.symbol ?? '')
    if (!symbol) return
    const current = { ...quotes.value }
    current[symbol] = {
      ...current[symbol],
      ...data,
    } as StockQuote
    quotes.value = current
    triggerRef(quotes)
  }

  wsStore.on('quote', onQuote)

  onScopeDispose(() => {
    wsStore.off('quote', onQuote)
  })

  watch(() => wsStore.connected, (isConnected) => {
    if (isConnected) {
      stopPolling()
      if (symbols.value.length > 0) {
        wsStore.subscribe(symbols.value)
      }
    } else {
      startPolling()
    }
  })

  return { symbols, quotes, alerts, loading, error, clearError, fetchWatchlist, addSymbol, removeSymbol, fetchAlerts, startPolling, stopPolling }
})
