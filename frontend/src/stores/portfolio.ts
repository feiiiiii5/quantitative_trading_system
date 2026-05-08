import { defineStore } from 'pinia'
import { ref, shallowRef, triggerRef, watch, onScopeDispose } from 'vue'
import { api } from '@/api'
import { useWebSocketStore } from '@/stores/websocket'
import type { AccountInfo, PortfolioRisk, PortfolioEquity } from '@/types'

export const usePortfolioStore = defineStore('portfolio', () => {
  const account = shallowRef<AccountInfo | null>(null)
  const riskAnalysis = shallowRef<PortfolioRisk | null>(null)
  const equityCurve = shallowRef<PortfolioEquity | null>(null)
  const loading = ref(false)
  const error = ref('')
  let _fetchId = 0
  let _pollTimer: ReturnType<typeof setInterval> | null = null
  const POLL_INTERVAL_MS = 60_000

  function clearError() {
    error.value = ''
  }

  async function fetchAccount() {
    const thisFetch = ++_fetchId
    error.value = ''
    try {
      const result = await api.trading.account()
      if (thisFetch !== _fetchId) return
      account.value = result
      triggerRef(account)
    } catch (e: unknown) {
      if (thisFetch !== _fetchId) return
      error.value = e instanceof Error ? e.message : '获取账户信息失败'
    }
  }

  async function fetchRiskAnalysis(symbols: string[]) {
    const thisFetch = ++_fetchId
    error.value = ''
    try {
      const result = await api.portfolio.riskAnalysis(symbols)
      if (thisFetch !== _fetchId) return
      riskAnalysis.value = result
      triggerRef(riskAnalysis)
    } catch (e: unknown) {
      if (thisFetch !== _fetchId) return
      error.value = e instanceof Error ? e.message : '获取风险分析失败'
    }
  }

  async function fetchEquityCurve(symbols: string[]) {
    const thisFetch = ++_fetchId
    error.value = ''
    try {
      const result = await api.portfolio.equity(symbols)
      if (thisFetch !== _fetchId) return
      equityCurve.value = result
      triggerRef(equityCurve)
    } catch (e: unknown) {
      if (thisFetch !== _fetchId) return
      error.value = e instanceof Error ? e.message : '获取权益曲线失败'
    }
  }

  function startPolling() {
    stopPolling()
    _pollTimer = setInterval(fetchAccount, POLL_INTERVAL_MS)
  }

  function stopPolling() {
    if (_pollTimer) {
      clearInterval(_pollTimer)
      _pollTimer = null
    }
  }

  const wsStore = useWebSocketStore()

  function onPnlUpdate() {
    fetchAccount()
  }

  wsStore.on('pnl_update', onPnlUpdate)

  onScopeDispose(() => {
    wsStore.off('pnl_update', onPnlUpdate)
  })

  watch(() => wsStore.connected, (isConnected) => {
    if (isConnected) {
      stopPolling()
    } else {
      startPolling()
    }
  })

  return { account, riskAnalysis, equityCurve, loading, error, clearError, fetchAccount, fetchRiskAnalysis, fetchEquityCurve, startPolling, stopPolling }
})
