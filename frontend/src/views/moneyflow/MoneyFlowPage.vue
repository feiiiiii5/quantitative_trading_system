<template>
  <div class="moneyflow-page">
    <div class="tab-bar">
      <button class="tab-btn" :class="{ active: activeTab === 'ranking' }" @click="activeTab = 'ranking'; fetchRanking()">MONEY FLOW RANKING</button>
      <button class="tab-btn" :class="{ active: activeTab === 'sector' }" @click="activeTab = 'sector'; fetchSectorFlow()">SECTOR FLOW</button>
    </div>

    <div v-show="activeTab === 'ranking'">
      <div class="surface-panel">
        <div class="panel-header">
          <span class="panel-title">MONEY FLOW RANKING</span>
          <span class="count-tag mono" v-if="rankingList.length">{{ rankingList.length }} STOCKS</span>
        </div>
        <div v-if="loading" class="panel-empty">LOADING<span class="blink-cursor">_</span></div>
        <DataTable
          v-else-if="rankingList.length"
          :columns="rankingColumns"
          :rows="rankingList as unknown as Record<string, unknown>[]"
          row-key="symbol"
          @row-click="(row: Record<string, unknown>) => goToStock(row.symbol as string)"
        >
          <template #cell-symbol="{ value }">
            <span class="code-text">{{ value }}</span>
          </template>
          <template #cell-name="{ value }">
            <span class="name-text">{{ value }}</span>
          </template>
          <template #cell-price="{ value }">
            <span class="mono">{{ ((value as number) ?? 0).toFixed(2) }}</span>
          </template>
          <template #cell-change_pct="{ value }">
            <span class="mono" :class="((value as number) ?? 0) >= 0 ? 'val-rise' : 'val-fall'">
              {{ formatPct((value as number) ?? 0) }}
            </span>
          </template>
          <template #cell-main_net_inflow="{ value }">
            <div class="flow-cell">
              <div class="flow-track">
                <div
                  class="flow-fill"
                  :class="((value as number) ?? 0) >= 0 ? 'fill-in' : 'fill-out'"
                  :style="{ width: flowBarWidth(value as number) + 'px' }"
                />
              </div>
              <span class="mono flow-val" :class="((value as number) ?? 0) >= 0 ? 'val-rise' : 'val-fall'">
                {{ formatFlow(value as number) }}
              </span>
            </div>
          </template>
          <template #cell-super_large_net="{ value }">
            <span class="mono" :class="((value as number) ?? 0) >= 0 ? 'val-rise' : 'val-fall'">{{ formatFlow(value as number) }}</span>
          </template>
          <template #cell-large_net="{ value }">
            <span class="mono" :class="((value as number) ?? 0) >= 0 ? 'val-rise' : 'val-fall'">{{ formatFlow(value as number) }}</span>
          </template>
          <template #cell-medium_net="{ value }">
            <span class="mono" :class="((value as number) ?? 0) >= 0 ? 'val-rise' : 'val-fall'">{{ formatFlow(value as number) }}</span>
          </template>
          <template #cell-small_net="{ value }">
            <span class="mono" :class="((value as number) ?? 0) >= 0 ? 'val-rise' : 'val-fall'">{{ formatFlow(value as number) }}</span>
          </template>
        </DataTable>
        <div v-else class="panel-empty">NO DATA</div>
      </div>
    </div>

    <div v-show="activeTab === 'sector'">
      <div class="surface-panel">
        <div class="panel-header"><span class="panel-title">SECTOR MONEY FLOW</span></div>
        <div v-if="loadingSector" class="panel-empty">LOADING...</div>
        <BaseChart
          v-else-if="sectorFlow.length"
          :option="sectorChartOption"
          height="600px"
        />
        <div v-else class="panel-empty">NO DATA</div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, defineAsyncComponent } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '@/api'
import { useRequestCancel } from '@/composables/useRequestCancel'
import { formatPct } from '@/utils/format'
import DataTable from '@/components/ui/DataTable.vue'
const BaseChart = defineAsyncComponent(() => import('@/components/chart/BaseChart.vue'))
import type { ColumnDef } from '@/components/ui/DataTable.vue'
import type { CapitalFlowRealtime, SectorFlowItem } from '@/types'
import echarts from '@/lib/echarts'

const router = useRouter()
const { cancelAll } = useRequestCancel()
const activeTab = ref('ranking')
const rankingList = ref<CapitalFlowRealtime[]>([])
const sectorFlow = ref<SectorFlowItem[]>([])
const loading = ref(false)
const loadingSector = ref(false)

const maxMainNet = computed(() => {
  if (!rankingList.value.length) return 1
  return Math.max(...rankingList.value.map(s => Math.abs(s.main_net_inflow || 0)), 1)
})

function flowBarWidth(value: number | undefined): number {
  if (value === undefined || value === null) return 0
  return Math.min((Math.abs(value) / maxMainNet.value) * 120, 120)
}

function formatFlow(v: number | undefined): string {
  if (v === undefined || v === null) return '-'
  const abs = Math.abs(v)
  const sign = v >= 0 ? '+' : '-'
  if (abs >= 1e8) return sign + (abs / 1e8).toFixed(2) + 'B'
  if (abs >= 1e4) return sign + (abs / 1e4).toFixed(1) + 'W'
  return sign + abs.toFixed(0)
}

const rankingColumns: ColumnDef[] = [
  { key: 'symbol', label: 'CODE', width: '90px', code: true },
  { key: 'name', label: 'NAME', width: '80px' },
  { key: 'price', label: 'PRICE', align: 'right', width: '70px' },
  { key: 'change_pct', label: 'CHG%', align: 'right', width: '65px' },
  { key: 'main_net_inflow', label: 'MAIN NET', align: 'right', width: '180px' },
  { key: 'super_large_net', label: 'SUPER', align: 'right', width: '80px' },
  { key: 'large_net', label: 'LARGE', align: 'right', width: '80px' },
  { key: 'medium_net', label: 'MEDIUM', align: 'right', width: '80px' },
  { key: 'small_net', label: 'SMALL', align: 'right', width: '80px' },
]

const sectorChartOption = computed(() => {
  if (!sectorFlow.value.length) return {}
  const sorted = [...sectorFlow.value].sort((a, b) => b.main_net_inflow - a.main_net_inflow)
  const names = sorted.map(s => s.name)
  const values = sorted.map(s => s.main_net_inflow)
  return {
    tooltip: {
      trigger: 'axis' as const,
      axisPointer: { type: 'shadow' as const },
      formatter: (params: { name: string; value: number; data: { inflow: number; outflow: number } }[]) => {
        const p = params[0]
        if (!p) return ''
        const d = p.data as unknown as { inflow: number; outflow: number }
        return `${p.name}<br/>Net: ${formatFlow(p.value)}<br/>Inflow: ${formatFlow(d?.inflow)}<br/>Outflow: ${formatFlow(d?.outflow)}`
      },
    },
    grid: { left: 100, right: 40, top: 10, bottom: 20 },
    xAxis: {
      type: 'value' as const,
      show: false,
    },
    yAxis: {
      type: 'category' as const,
      data: names,
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: {
        color: '#9898b0',
        fontSize: 11,
        fontFamily: 'JetBrains Mono, monospace',
      },
    },
    series: [
      {
        type: 'bar',
        data: values.map((v, i) => ({
          value: v,
          inflow: sorted[i].main_inflow,
          outflow: sorted[i].main_outflow,
          itemStyle: {
            color: v >= 0
              ? new echarts.graphic.LinearGradient(0, 0, 1, 0, [
                  { offset: 0, color: 'rgba(0, 230, 118, 0.3)' },
                  { offset: 1, color: 'rgba(0, 230, 118, 0.8)' },
                ])
              : new echarts.graphic.LinearGradient(1, 0, 0, 0, [
                  { offset: 0, color: 'rgba(255, 59, 59, 0.3)' },
                  { offset: 1, color: 'rgba(255, 59, 59, 0.8)' },
                ]),
            borderRadius: v >= 0 ? [0, 2, 2, 0] as number[] : [2, 0, 0, 2] as number[],
          },
        })),
        barWidth: 14,
        label: {
          show: true,
          position: 'right' as const,
          formatter: (p: { value: number }) => formatFlow(p.value),
          color: '#9898b0',
          fontSize: 10,
          fontFamily: 'JetBrains Mono, monospace',
        },
      },
    ],
  }
})

async function fetchRanking() {
  loading.value = true
  try {
    rankingList.value = await api.moneyFlow.ranking('main_net', 30)
  } catch {
    rankingList.value = []
  } finally {
    loading.value = false
  }
}

async function fetchSectorFlow() {
  loadingSector.value = true
  try {
    sectorFlow.value = await api.moneyFlow.sector()
  } catch {
    sectorFlow.value = []
  } finally {
    loadingSector.value = false
  }
}

function goToStock(symbol: string) {
  router.push(`/stock/${symbol}`)
}

onMounted(fetchRanking)

onUnmounted(cancelAll)
</script>

<style scoped>
.moneyflow-page {
  max-width: 1440px;
  margin: 0 auto;
  display: grid;
  gap: var(--u4);
}

.tab-bar {
  display: flex;
  gap: 0;
  border-bottom: 1px solid var(--border-hair);
  overflow-x: auto;
  white-space: nowrap;
}

.tab-btn {
  padding: var(--u2) var(--u6);
  border: none;
  background: transparent;
  color: var(--text-tertiary);
  font-size: var(--fs-sm);
  font-weight: 500;
  font-family: var(--font-mono);
  cursor: pointer;
  position: relative;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  transition: color var(--dur-fast) var(--ease-mechanical);
}

.tab-btn::after {
  content: '';
  position: absolute;
  bottom: -1px;
  left: 0;
  right: 0;
  height: 2px;
  background: var(--accent);
  transform: scaleX(0);
  will-change: transform;
  transition: transform var(--dur-fast) var(--ease-mechanical);
}

.tab-btn:hover { color: var(--text-primary); }
.tab-btn.active { color: var(--accent); }
.tab-btn.active::after { transform: scaleX(1); }

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--u3) var(--u4);
  border-bottom: 1px solid var(--border-hair);
}

.panel-title {
  font-family: var(--font-mono);
  font-size: var(--fs-xs);
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: var(--text-tertiary);
}

.panel-empty {
  padding: var(--u8) var(--u4);
  text-align: center;
  color: var(--text-muted);
  font-size: var(--fs-xs);
  font-family: var(--font-mono);
  text-transform: uppercase;
  letter-spacing: 0.1em;
}

.blink-cursor { animation: blink 1s step-end infinite; }

.code-text {
  font-family: var(--font-mono);
  font-variant-numeric: tabular-nums;
  color: var(--accent);
  font-size: var(--fs-xs);
}

.name-text { color: var(--text-primary); }

.val-rise { color: var(--rise); }
.val-fall { color: var(--fall); }

.count-tag {
  font-size: var(--fs-xs);
  color: var(--text-tertiary);
  font-family: var(--font-mono);
  font-variant-numeric: tabular-nums;
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.flow-cell {
  display: flex;
  align-items: center;
  gap: var(--u2);
}

.flow-track {
  width: 120px;
  height: 3px;
  background: var(--bg-plate);
  border-radius: 2px;
  overflow: hidden;
  flex-shrink: 0;
}

.flow-fill {
  height: 100%;
  border-radius: 2px;
  transition: width var(--dur-normal) var(--ease-mechanical);
}

.fill-in { background: var(--fall); }
.fill-out { background: var(--rise); }

.flow-val {
  font-size: var(--fs-xs);
  min-width: 60px;
  text-align: right;
  font-family: var(--font-mono);
  font-variant-numeric: tabular-nums;
}

@media (max-width: 768px) {
  .flow-cell { flex-direction: column; align-items: flex-end; }
  .flow-track { width: 100%; }
}
</style>
