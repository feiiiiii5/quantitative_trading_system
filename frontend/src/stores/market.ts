import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { api } from '@/api'
import type { MarketOverview, MarketStatus, AnomalyItem, NorthboundData, HeatmapItem } from '@/types'

export const useMarketStore = defineStore('market', () => {
  const overview = ref<MarketOverview | null>(null)
  const status = ref<Record<string, MarketStatus> | null>(null)
  const heatmap = ref<HeatmapItem[]>([])
  const anomalies = ref<AnomalyItem[]>([])
  const northbound = ref<NorthboundData | null>(null)
  const loading = ref(false)
  const error = ref('')

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
    try {
      overview.value = await api.market.overview()
    } catch (e: unknown) {
      error.value = (e as Error).message
    }
  }

  async function fetchStatus() {
    try {
      status.value = await api.market.status()
    } catch (e: unknown) {
      error.value = (e as Error).message
    }
  }

  async function fetchHeatmap() {
    try {
      const data = await api.market.heatmap()
      heatmap.value = data.items
    } catch (e: unknown) {
      error.value = (e as Error).message
    }
  }

  async function fetchAnomalies() {
    try {
      anomalies.value = await api.market.anomaly()
    } catch (e: unknown) {
      error.value = (e as Error).message
    }
  }

  async function fetchNorthbound() {
    try {
      northbound.value = await api.market.northbound()
    } catch (e: unknown) {
      error.value = (e as Error).message
    }
  }

  async function fetchDashboardData() {
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
      loading.value = false
    }
  }

  return {
    overview, status, heatmap, anomalies, northbound, loading, error,
    cnIndices, hkIndices, usIndices,
    fetchOverview, fetchStatus, fetchHeatmap, fetchAnomalies, fetchNorthbound,
    fetchDashboardData,
  }
})
