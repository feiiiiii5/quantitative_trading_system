<template>
  <div class="market-page">
    <div class="market-header">
      <div class="header-left">
        <div class="region-selector">
          <button
            v-for="region in marketRegions"
            :key="region.value"
            class="region-btn"
            :class="{ active: marketRegion === region.value }"
            @click="switchRegion(region.value)"
          >
            {{ region.label }}
          </button>
        </div>
        <div class="tab-divider" />
        <div v-if="marketRegion === 'A'" class="sub-tabs">
          <button
            v-for="tab in aShareTabs"
            :key="tab.value"
            class="sub-tab"
            :class="{ active: activeTab === tab.value }"
            @click="switchTab(tab.value)"
          >
            {{ tab.label }}
          </button>
        </div>
        <div v-else class="region-label mono">{{ marketRegion === 'HK' ? 'HK MARKET' : 'US MARKET' }}</div>
      </div>
      <div class="header-right">
        <button
          v-for="tab in viewTabs"
          :key="tab.value"
          class="view-tab"
          :class="{ active: activeTab === tab.value }"
          @click="switchTab(tab.value)"
        >
          {{ tab.label }}
        </button>
      </div>
    </div>

    <div v-show="activeView === 'table'" class="table-view surface-panel">
      <DataTable
        :columns="stockColumns"
        :rows="filteredStocks"
        row-key="symbol"
        :toolbar="true"
        :page-size="50"
        exportable
        export-filename="market-stocks"
        @row-click="goToStock"
      >
        <template #toolbar>
          <div class="toolbar-wrap">
            <input
              v-model="searchQuery"
              class="qc-input search-input"
              placeholder="Search symbol / name..."
              type="text"
            />
            <span class="stock-count mono">{{ filteredStocks.length }} items</span>
          </div>
        </template>

        <template #cell-_pricebar="{ row }">
          <div class="price-bar" :title="`Price: ${formatPrice(asStock(row).price)}`">
            <div
              class="price-bar-marker"
              :class="asStock(row).change_pct >= 0 ? 'rise' : 'fall'"
              :style="{ bottom: priceBarPosition(asStock(row)) + '%' }"
            />
          </div>
        </template>

        <template #cell-change_pct="{ value }">
          <span class="mono" :class="(value as number) >= 0 ? 'text-rise' : 'text-fall'">
            {{ formatPct(value as number) }}
          </span>
        </template>

        <template #cell-change="{ value }">
          <span class="mono" :class="(value as number) >= 0 ? 'text-rise' : 'text-fall'">
            {{ ((value as number) >= 0 ? '+' : '') + safeToFixed(value, 2) }}
          </span>
        </template>

        <template #cell-_flowbar="{ row }">
          <div class="flow-bar-track">
            <div
              class="flow-bar-fill"
              :class="flowDirection(asStock(row))"
              :style="{ width: flowBarWidth(asStock(row)) + 'px' }"
            />
          </div>
        </template>

        <template #actions="{ row }">
          <button
            class="wl-toggle"
            :class="{ added: isInWatchlist(asStock(row).symbol) }"
            @click.stop="toggleWatchlist(asStock(row).symbol)"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" :fill="isInWatchlist(asStock(row).symbol) ? 'currentColor' : 'none'" stroke="currentColor" stroke-width="2">
              <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" />
            </svg>
          </button>
        </template>
      </DataTable>
    </div>

    <div v-show="activeView === 'sector'" class="sector-view">
      <DataPanel title="SECTOR HEATMAP">
        <div v-if="sectors.length" class="heatmap-container">
          <BaseChart :option="heatmapOption" height="500px" />
        </div>
        <div v-else class="empty-state">No sector data</div>
      </DataPanel>
    </div>

    <div v-show="activeView === 'anomaly'" class="anomaly-view">
      <DataPanel title="ANOMALY DETECTION">
        <div v-if="anomalies.length" class="anomaly-list">
          <div
            v-for="item in anomalies"
            :key="item.symbol"
            class="anomaly-row"
            :class="{ 'high-ratio': item.volume_ratio > 3 }"
            @click="goToStock(item.symbol)"
          >
            <div class="anom-indicator" :class="item.change_pct >= 0 ? 'rise' : 'fall'" />
            <div class="anom-left">
              <span class="anom-name">{{ item.name }}</span>
              <span class="anom-code mono">{{ item.symbol }}</span>
            </div>
            <div class="anom-mid">
              <span class="anom-pct mono" :class="item.change_pct >= 0 ? 'text-rise' : 'text-fall'">
                {{ formatPct(item.change_pct) }}
              </span>
              <span class="anom-price mono">{{ formatPrice(item.price) }}</span>
            </div>
            <div class="anom-right">
              <div class="anom-vol-ratio">
                <span class="anom-vol-label">VOL RATIO</span>
                <span class="anom-vol-val mono" :class="item.volume_ratio > 3 ? 'text-warn' : 'text-secondary'">
                  {{ safeToFixed(item.volume_ratio, 1) }}x
                </span>
              </div>
              <span class="anom-reason">{{ item.reason }}</span>
            </div>
          </div>
        </div>
        <div v-else class="empty-state">No unusual activity</div>
      </DataPanel>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted, defineAsyncComponent } from 'vue'
import { useRouter } from 'vue-router'
import { createLogger } from '@/composables/useLogger'
import { useRequestCancel } from '@/composables/useRequestCancel'
import { useApiError } from '@/composables/useApiError'
import { api } from '@/api'
import { useMarketStore } from '@/stores/market'
import { useWatchlistStore } from '@/stores/watchlist'
import { formatPrice, formatPct, formatVolume, formatNumber, safeToFixed } from '@/utils/format'
import DataTable from '@/components/ui/DataTable.vue'
import DataPanel from '@/components/ui/DataPanel.vue'
import type { ColumnDef } from '@/components/ui/DataTable.vue'
import type { MarketStock, HeatmapItem, AnomalyItem } from '@/types'

const log = createLogger('Market')
const { handleApiError } = useApiError()

const BaseChart = defineAsyncComponent(() => import('@/components/chart/BaseChart.vue'))

const marketRegions = [
  { label: 'A', value: 'A' },
  { label: 'HK', value: 'HK' },
  { label: 'US', value: 'US' },
]

const aShareTabs = [
  { label: '全市', value: 'A' },
  { label: '沪市', value: 'sh' },
  { label: '深市', value: 'sz' },
  { label: '创业板', value: 'cy' },
  { label: '科创板', value: 'kc' },
]

const viewTabs = [
  { label: '板块行业', value: 'sector' },
  { label: '量价异动', value: 'anomaly' },
]

const tabs = [
  { label: '全市', value: 'A' },
  { label: '沪市', value: 'sh' },
  { label: '深市', value: 'sz' },
  { label: '创业板', value: 'cy' },
  { label: '科创板', value: 'kc' },
  { label: '板块行业', value: 'sector' },
  { label: '量价异动', value: 'anomaly' },
]

const router = useRouter()
const marketStore = useMarketStore()
const watchlistStore = useWatchlistStore()

const POLL_INTERVAL_MS = 30_000

const activeTab = ref('A')
const marketRegion = ref('A')
const stocks = ref<MarketStock[]>([])
const sectors = ref<HeatmapItem[]>([])
const anomalies = ref<AnomalyItem[]>([])
const searchQuery = ref('')
const loading = ref(false)
const expandedSector = ref<string | null>(null)
let pollTimer: ReturnType<typeof setInterval> | null = null
const { cancelAll } = useRequestCancel()

const activeView = computed(() => {
  if (activeTab.value === 'sector') return 'sector'
  if (activeTab.value === 'anomaly') return 'anomaly'
  return 'table'
})

const maxSectorChange = computed(() => {
  if (!sectors.value.length) return 5
  const maxAbs = Math.max(...sectors.value.map(s => Math.abs(s.change_pct)))
  return Math.max(maxAbs, 1)
})

const maxFlow = computed(() => {
  if (!stocks.value.length) return 1
  return Math.max(
    ...stocks.value.map(s => Math.abs((s as Record<string, unknown>).main_net_inflow as number || 0)),
    1,
  )
})

const stockColumns: ColumnDef[] = [
  { key: 'symbol', label: '代码', width: '80px', code: true, sortable: true },
  { key: 'name', label: '名称', width: '80px', sortable: true },
  { key: '_pricebar', label: '', width: '16px', sortable: false },
  { key: 'price', label: '最新价', width: '80px', align: 'right', sortable: true, format: (v: unknown) => formatPrice(v as number) },
  { key: 'change_pct', label: '涨跌幅', width: '80px', align: 'right', sortable: true },
  { key: 'change', label: '涨跌额', width: '72px', align: 'right', sortable: true },
  { key: 'volume', label: '成交量', width: '80px', align: 'right', sortable: true, format: (v: unknown) => formatVolume(v as number) },
  { key: 'amount', label: '成交额', width: '80px', align: 'right', sortable: true, format: (v: unknown) => formatNumber(v as number) },
  { key: 'turnover_rate', label: '换手率', width: '72px', align: 'right', sortable: true, format: (v: unknown) => safeToFixed(v, 2) + '%' },
  { key: '_flowbar', label: '资金流向', width: '130px', align: 'right', sortable: false },
]

const filteredStocks = computed(() => {
  const q = searchQuery.value.trim().toLowerCase()
  if (!q) return stocks.value
  return stocks.value.filter(
    (s) =>
      s.symbol.toLowerCase().includes(q) ||
      s.name.toLowerCase().includes(q),
  )
})

const heatmapOption = computed(() => {
  if (!sectors.value.length) return {}

  const maxAbs = Math.max(...sectors.value.map(s => Math.abs(s.change_pct)), 1)

  return {
    tooltip: {
      formatter: (params: Record<string, unknown>) => {
        const d = params.data as { name?: string; change_pct?: number; leader?: string } | undefined
        if (!d?.name) return ''
        const pctColor = (d.change_pct ?? 0) >= 0 ? '#ff3b3b' : '#00e676'
        const sign = (d.change_pct ?? 0) >= 0 ? '+' : ''
        return [
          '<div style="font-family:JetBrains Mono;font-size:11px;line-height:1.6">',
          `<div style="font-weight:600;margin-bottom:2px">${d.name}</div>`,
          `<div>涨跌幅: <span style="color:${pctColor};font-weight:600">${sign}${(d.change_pct ?? 0).toFixed(2)}%</span></div>`,
          d.leader ? `<div>领涨: <span style="color:#2979ff">${d.leader}</span></div>` : '',
          '</div>',
        ].join('')
      },
    },
    series: [{
      type: 'treemap',
      data: sectors.value.map(s => ({
        name: s.name,
        value: Math.max(Math.abs(s.amount || s.value || 1), 1),
        change_pct: s.change_pct,
        leader: s.leader,
        itemStyle: {
          color: s.change_pct >= 0
            ? `rgba(255, 59, 59, ${0.25 + (Math.abs(s.change_pct) / maxAbs) * 0.65})`
            : `rgba(0, 230, 118, ${0.25 + (Math.abs(s.change_pct) / maxAbs) * 0.65})`,
        },
      })),
      width: '100%',
      height: '100%',
      top: 5,
      left: 5,
      right: 5,
      bottom: 5,
      roam: false,
      nodeClick: false,
      breadcrumb: { show: false },
      label: {
        show: true,
        formatter: (params: Record<string, unknown>) => {
          const d = params.data as { name?: string; change_pct?: number } | undefined
          if (!d?.name) return ''
          const sign = (d.change_pct ?? 0) >= 0 ? '+' : ''
          return `${d.name}\n${sign}${(d.change_pct ?? 0).toFixed(2)}%`
        },
        fontSize: 11,
        fontFamily: 'JetBrains Mono',
        color: '#e8e8f0',
      },
      upperLabel: { show: false },
      itemStyle: {
        borderColor: 'rgba(255,255,255,0.08)',
        borderWidth: 1,
        gapWidth: 2,
      },
      levels: [{
        itemStyle: {
          borderColor: 'rgba(255,255,255,0.08)',
          borderWidth: 1,
          gapWidth: 2,
        },
      }],
    }],
  }
})

function asStock(row: Record<string, unknown>): MarketStock {
  return row as unknown as MarketStock
}

function priceBarPosition(stock: MarketStock): number {
  const pct = stock.change_pct ?? 0
  const normalized = 50 + pct * 8
  return Math.max(5, Math.min(95, normalized))
}

function sectorBarWidth(changePct: number): number {
  const normalized = (Math.abs(changePct) / maxSectorChange.value) * 100
  return Math.max(2, Math.min(98, normalized))
}

function flowDirection(stock: MarketStock): string {
  const flow = (stock as unknown as Record<string, unknown>).main_net_inflow as number || 0
  return flow >= 0 ? 'inflow' : 'outflow'
}

function flowBarWidth(stock: MarketStock): number {
  const flow = (stock as unknown as Record<string, unknown>).main_net_inflow as number || 0
  if (!flow) return 0
  return Math.min(120, (Math.abs(flow) / maxFlow.value) * 120)
}

function toggleSectorExpand(name: string): void {
  expandedSector.value = expandedSector.value === name ? null : name
}

function isInWatchlist(symbol: string): boolean {
  return watchlistStore.symbols.includes(symbol)
}

async function toggleWatchlist(symbol: string): Promise<void> {
  if (isInWatchlist(symbol)) {
    await watchlistStore.removeSymbol(symbol)
  } else {
    await watchlistStore.addSymbol(symbol)
  }
}

function goToStock(rowOrSymbol: Record<string, unknown> | string): void {
  const sym = typeof rowOrSymbol === 'string'
    ? rowOrSymbol
    : (rowOrSymbol as { symbol: string }).symbol
  if (sym) router.push(`/stock/${sym}`)
}

function switchTab(value: string): void {
  activeTab.value = value
  if (['sh', 'sz', 'cy', 'kc', 'A'].includes(value)) {
    marketRegion.value = 'A'
  }
  expandedSector.value = null
}

function switchRegion(region: string): void {
  marketRegion.value = region
  if (activeTab.value !== 'sector' && activeTab.value !== 'anomaly') {
    activeTab.value = region === 'A' ? 'A' : region
  }
  expandedSector.value = null
}

async function fetchStocks(): Promise<void> {
  if (activeTab.value === 'sector' || activeTab.value === 'anomaly') return
  loading.value = true
  try {
    stocks.value = await api.market.stocks(activeTab.value, 5000)
  } catch (err) {
    handleApiError(err, '获取股票列表失败')
    stocks.value = []
  } finally {
    loading.value = false
  }
}

async function fetchSectors(): Promise<void> {
  try {
    const data = await api.market.heatmap()
    sectors.value = data?.items || []
  } catch (err) {
    handleApiError(err, '获取板块数据失败')
    sectors.value = []
  }
}

async function fetchAnomalies(): Promise<void> {
  try {
    anomalies.value = await api.market.anomaly()
  } catch (err) {
    handleApiError(err, '获取异动数据失败')
    anomalies.value = []
  }
}

watch(activeTab, (val) => {
  if (val === 'sector') {
    fetchSectors()
  } else if (val === 'anomaly') {
    fetchAnomalies()
  } else {
    fetchStocks()
  }
})

onMounted(async () => {
  await Promise.allSettled([
    fetchStocks(),
    watchlistStore.fetchWatchlist(),
  ])

  pollTimer = setInterval(() => {
    if (activeView.value === 'table') {
      fetchStocks()
    }
  }, POLL_INTERVAL_MS)
})

onUnmounted(() => {
  cancelAll()
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
})
</script>

<style scoped>
.market-page {
  max-width: 1600px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  height: calc(100vh - var(--topbar-height) - var(--u8));
  background: var(--bg-base);
}

.market-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 var(--u4);
  border-bottom: 1px solid var(--border-hair);
  background: var(--bg-surface);
  height: 40px;
  flex-shrink: 0;
}

.header-left {
  display: flex;
  align-items: center;
  gap: var(--u3);
  height: 100%;
}

.region-selector {
  display: flex;
  height: 26px;
}

.region-btn {
  padding: 0 var(--u3);
  font-family: var(--font-mono);
  font-size: var(--fs-xs);
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--text-tertiary);
  background: transparent;
  border: 1px solid var(--border-hair);
  cursor: pointer;
  transition: all var(--dur-fast) var(--ease-mechanical);
  line-height: 24px;
}

.region-btn:first-child {
  border-radius: var(--r-md) 0 0 var(--r-md);
}

.region-btn:last-child {
  border-radius: 0 var(--r-md) var(--r-md) 0;
}

.region-btn:not(:first-child) {
  border-left: none;
}

.region-btn:hover {
  color: var(--text-secondary);
  background: var(--bg-plate);
}

.region-btn.active {
  color: var(--accent);
  background: var(--accent-muted);
  border-color: var(--accent);
}

.region-btn.active + .region-btn {
  border-left-color: var(--accent);
}

.tab-divider {
  width: 1px;
  height: 20px;
  background: var(--border-mid);
  flex-shrink: 0;
}

.sub-tabs {
  display: flex;
  height: 100%;
  align-items: center;
}

.sub-tab {
  padding: 0 var(--u3);
  height: 100%;
  font-family: var(--font-mono);
  font-size: var(--fs-xs);
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--text-tertiary);
  border-bottom: 2px solid transparent;
  transition: all var(--dur-fast) var(--ease-mechanical);
  cursor: pointer;
  line-height: 40px;
}

.sub-tab:hover {
  color: var(--text-secondary);
}

.sub-tab.active {
  color: var(--accent);
  border-bottom-color: var(--accent);
}

.region-label {
  font-size: var(--fs-xs);
  font-weight: 500;
  color: var(--text-tertiary);
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.header-right {
  display: flex;
  height: 100%;
  align-items: center;
}

.view-tab {
  padding: 0 var(--u4);
  height: 100%;
  font-family: var(--font-mono);
  font-size: var(--fs-xs);
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--text-tertiary);
  border-bottom: 2px solid transparent;
  transition: all var(--dur-fast) var(--ease-mechanical);
  cursor: pointer;
  line-height: 40px;
}

.view-tab:hover {
  color: var(--text-secondary);
}

.view-tab.active {
  color: var(--accent);
  border-bottom-color: var(--accent);
}

.table-view {
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

.table-view :deep(.dt td:first-child),
.table-view :deep(.dt th:first-child) {
  position: sticky;
  left: 0;
  z-index: 1;
  background: var(--bg-void);
}

.table-view :deep(.dt th:first-child) {
  z-index: 3;
}

.table-view :deep(.dt th.sorted) {
  color: var(--accent);
}

.table-view :deep(.dt td) {
  height: 36px;
}

.table-view :deep(.num-col) {
  font-family: var(--font-mono);
  font-variant-numeric: tabular-nums;
  font-weight: 500;
}

.toolbar-wrap {
  display: flex;
  align-items: center;
  gap: var(--u4);
  width: 100%;
}

.search-input {
  width: 220px;
  font-size: var(--fs-sm);
  font-family: var(--font-mono);
}

.stock-count {
  font-size: var(--fs-xs);
  color: var(--text-muted);
  margin-left: auto;
  font-family: var(--font-mono);
  font-variant-numeric: tabular-nums;
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.price-bar {
  width: 12px;
  height: 24px;
  background: var(--bg-plate);
  border-radius: var(--r-xs);
  position: relative;
  overflow: hidden;
}

.price-bar-marker {
  position: absolute;
  left: 2px;
  right: 2px;
  height: 4px;
  border-radius: 1px;
  transition: bottom var(--dur-normal) var(--ease-mechanical);
}

.price-bar-marker.rise {
  background: var(--rise);
}

.price-bar-marker.fall {
  background: var(--fall);
}

.flow-bar-track {
  width: 120px;
  height: 6px;
  background: var(--bg-plate);
  border-radius: 3px;
  overflow: hidden;
  display: inline-flex;
  vertical-align: middle;
}

.flow-bar-fill {
  height: 100%;
  border-radius: 3px;
  transition: width var(--dur-normal) var(--ease-mechanical);
}

.flow-bar-fill.inflow {
  background: var(--rise);
}

.flow-bar-fill.outflow {
  background: var(--fall);
}

.wl-toggle {
  background: none;
  border: none;
  cursor: pointer;
  color: var(--text-muted);
  padding: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--r-xs);
  transition: color var(--dur-fast) var(--ease-mechanical);
}

.wl-toggle:hover {
  color: var(--warn);
}

.wl-toggle.added {
  color: var(--warn);
}

.sector-view {
  flex: 1;
  overflow-y: auto;
}

.heatmap-container {
  width: 100%;
  min-height: 500px;
}

.anomaly-view {
  flex: 1;
  overflow-y: auto;
}

.anomaly-list {
  display: grid;
  gap: 2px;
}

.anomaly-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--u3) var(--u4);
  background: var(--bg-surface);
  border-radius: var(--r-sm);
  cursor: pointer;
  transition: background var(--dur-fast) var(--ease-mechanical);
  position: relative;
}

.anomaly-row:hover {
  background: var(--bg-raised);
}

.anomaly-row.high-ratio {
  border-left: 3px solid var(--warn);
}

.anom-indicator {
  width: 2px;
  height: 24px;
  border-radius: 1px;
  flex-shrink: 0;
  margin-right: var(--u3);
}

.anom-indicator.rise {
  background: var(--rise);
}

.anom-indicator.fall {
  background: var(--fall);
}

.anom-left {
  display: flex;
  align-items: center;
  gap: var(--u2);
  min-width: 0;
  flex-shrink: 0;
}

.anom-name {
  font-size: var(--fs-sm);
  font-weight: 500;
  color: var(--text-primary);
  white-space: nowrap;
}

.anom-code {
  font-size: var(--fs-xs);
  color: var(--text-tertiary);
  font-family: var(--font-mono);
  font-variant-numeric: tabular-nums;
}

.anom-mid {
  display: flex;
  align-items: center;
  gap: var(--u4);
  flex-shrink: 0;
}

.anom-pct {
  font-size: var(--fs-sm);
  font-weight: 600;
  font-family: var(--font-mono);
  font-variant-numeric: tabular-nums;
  min-width: 64px;
  text-align: right;
}

.anom-price {
  font-size: var(--fs-sm);
  color: var(--text-secondary);
  font-family: var(--font-mono);
  font-variant-numeric: tabular-nums;
  min-width: 64px;
  text-align: right;
}

.anom-right {
  display: flex;
  align-items: center;
  gap: var(--u4);
  flex-shrink: 0;
}

.anom-vol-ratio {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 1px;
}

.anom-vol-label {
  font-size: var(--fs-xs);
  color: var(--text-muted);
  font-family: var(--font-mono);
  text-transform: uppercase;
  letter-spacing: 0.1em;
}

.anom-vol-val {
  font-size: var(--fs-sm);
  font-weight: 600;
  font-family: var(--font-mono);
  font-variant-numeric: tabular-nums;
}

.text-warn {
  color: var(--warn);
}

.text-secondary {
  color: var(--text-secondary);
}

.anom-reason {
  font-size: var(--fs-xs);
  color: var(--text-tertiary);
  padding: 1px 5px;
  background: var(--bg-raised);
  border-radius: var(--r-xs);
  white-space: nowrap;
  font-family: var(--font-mono);
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.empty-state {
  padding: var(--u16) var(--u4);
  text-align: center;
  color: var(--text-muted);
  font-size: var(--fs-xs);
  font-family: var(--font-mono);
  text-transform: uppercase;
  letter-spacing: 0.1em;
}

.text-rise {
  color: var(--rise);
}

.text-fall {
  color: var(--fall);
}

@media (max-width: 768px) {
  .search-input {
    width: 140px;
  }

  .anom-right {
    display: none;
  }

  .sub-tabs {
    display: none;
  }

  .flow-bar-track {
    width: 60px;
  }
}
</style>
