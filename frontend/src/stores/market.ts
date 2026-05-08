import { defineStore } from 'pinia'
import { ref, computed, shallowRef, triggerRef, watch, onScopeDispose } from 'vue'
import { api } from '@/api'
import { useWebSocketStore } from '@/stores/websocket'
import type { MarketOverview, MarketStatus, AnomalyItem, NorthboundData, HeatmapItem } from '@/types'

export const useMarketStore = defineStore('market', () => {
  const overview = shallowRef<MarketOverview | null>(null)
  const status = shallowRef<Record<string, MarketStatus> | null>(null)
  const heatmap = shallowRef<HeatmapItem[]>([])
  const anomalies = shallowRef<AnomalyItem[]>([])
  const northbound = ref<NorthboundData | null>(null)
  const loading = ref(false)
  const error = ref('')
  let _fetchId = 0
  let _pollTimer: ReturnType<typeof setTimeout> | null = null
  let _pollStopped = true
  const POLL_INTERVAL_MS = 30_000

  const cnIndices = computed(() => {
    if (!overview.value) return []
    return Object.entries(overview.value.cn_indices).map(([code, data]) => ({ code, ...data }))
  })

  const hkIndices = computed(() => {
    if (!overview.value) return []
    return Object.entries(overview.value.hk_indices).map(([code, data]) => ({ code, ...data }))
  })

  const usIndices = computed(() => {
    if (!overview.value) return []
    return Object.entries(overview.value.us_indices).map(([code, data]) => ({ code, ...data }))
  })

  async function fetchOverview() {
    const thisFetch = ++_fetchId
    try {
      const result = await api.market.overview()
      if (thisFetch !== _fetchId) return
      overview.value = result
      triggerRef(overview)
    } catch (e: unknown) {
      if (thisFetch !== _fetchId) return
      error.value = e instanceof Error ? e.message : '获取市场概览失败'
    }
  }

  async function fetchStatus() {
    const thisFetch = ++_fetchId
    try {
      const result = await api.market.status()
      if (thisFetch !== _fetchId) return
      status.value = result
      triggerRef(status)
    } catch (e: unknown) {
      if (thisFetch !== _fetchId) return
      error.value = e instanceof Error ? e.message : '获取市场状态失败'
    }
  }

  async function fetchHeatmap() {
    const thisFetch = ++_fetchId
    try {
      const data = await api.market.heatmap()
      if (thisFetch !== _fetchId) return
      heatmap.value = data?.items ?? []
      triggerRef(heatmap)
    } catch (e: unknown) {
      if (thisFetch !== _fetchId) return
      error.value = e instanceof Error ? e.message : '获取热力图失败'
    }
  }

  async function fetchAnomalies() {
    const thisFetch = ++_fetchId
    try {
      const result = await api.market.anomaly()
      if (thisFetch !== _fetchId) return
      anomalies.value = result
      triggerRef(anomalies)
    } catch (e: unknown) {
      if (thisFetch !== _fetchId) return
      error.value = e instanceof Error ? e.message : '获取异动数据失败'
    }
  }

  async function fetchNorthbound() {
    const thisFetch = ++_fetchId
    try {
      const result = await api.market.northbound()
      if (thisFetch !== _fetchId) return
      northbound.value = result
    } catch (e: unknown) {
      if (thisFetch !== _fetchId) return
      error.value = e instanceof Error ? e.message : '获取北向资金失败'
    }
  }

  async function fetchDashboardData() {
    const thisFetch = ++_fetchId
    loading.value = true
    error.value = ''
    try {
      await Promise.allSettled([
        fetchOverview(),
        fetchStatus(),
        fetchHeatmap(),
        fetchAnomalies(),
        fetchNorthbound(),
      ])
    } finally {
      if (thisFetch === _fetchId) loading.value = false
    }
  }

  async function pollTick() {
    if (_pollStopped) return
    try {
      await fetchOverview()
    } finally {
      if (!_pollStopped) {
        _pollTimer = setTimeout(pollTick, POLL_INTERVAL_MS)
      }
    }
  }

  function startPolling() {
    stopPolling()
    _pollStopped = false
    _pollTimer = setTimeout(pollTick, POLL_INTERVAL_MS)
  }

  function stopPolling() {
    _pollStopped = true
    if (_pollTimer) {
      clearTimeout(_pollTimer)
      _pollTimer = null
    }
  }

  const wsStore = useWebSocketStore()

  function onIndexUpdate() {
    fetchOverview()
  }

  wsStore.on('index_update', onIndexUpdate)

  onScopeDispose(() => {
    wsStore.off('index_update', onIndexUpdate)
    stopPolling()
  })

  watch(() => wsStore.connected, (isConnected) => {
    if (isConnected) {
      stopPolling()
    } else {
      startPolling()
    }
  })

  return {
    overview, status, heatmap, anomalies, northbound, loading, error,
    cnIndices, hkIndices, usIndices,
    fetchOverview, fetchStatus, fetchHeatmap, fetchAnomalies, fetchNorthbound,
    fetchDashboardData,
    startPolling, stopPolling,
  }
})
