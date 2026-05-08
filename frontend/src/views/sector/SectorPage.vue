<template>
  <div class="sector-page">
    <div class="tab-bar">
      <button class="tab-btn" :class="{ active: activeTab === 'strength' }" @click="switchTab('strength')">STRENGTH RANKING</button>
      <button class="tab-btn" :class="{ active: activeTab === 'rotation' }" @click="switchTab('rotation')">ROTATION SIGNALS</button>
      <button class="tab-btn" :class="{ active: activeTab === 'snapshot' }" @click="switchTab('snapshot')">SNAPSHOT</button>
    </div>

    <div v-show="activeTab === 'strength'">
      <div class="surface-panel">
        <div class="panel-header">
          <span class="panel-title">SECTOR STRENGTH</span>
          <span class="count-tag mono" v-if="sectors.length">{{ sectors.length }} SECTORS</span>
        </div>
        <div v-if="loading" class="panel-empty">LOADING<span class="blink-cursor">_</span></div>
        <div v-else-if="sectors.length" class="strength-list">
          <div
            v-for="(s, idx) in sectors"
            :key="s.name"
            class="strength-row"
            @click="openDetail(s.name)"
          >
            <div class="sr-rank">
              <span class="rank-num mono" :class="idx < 3 ? 'rank-top' : ''">{{ idx + 1 }}</span>
            </div>
            <div class="sr-info">
              <span class="sr-name">{{ s.name }}</span>
              <span class="sr-change mono" :class="s.change_pct >= 0 ? 'val-rise' : 'val-fall'">
                {{ s.change_pct >= 0 ? '+' : '' }}{{ safeToFixed(s.change_pct, 2) }}%
              </span>
              <span class="sr-flow mono" :class="s.main_net_inflow >= 0 ? 'val-rise' : 'val-fall'">
                {{ formatFlow(s.main_net_inflow) }}
              </span>
            </div>
            <div class="sr-momentum">
              <div class="momentum-track">
                <div class="momentum-zero" />
                <div
                  class="momentum-fill"
                  :class="s.momentum_score >= 0 ? 'mom-rise' : 'mom-fall'"
                  :style="momentumStyle(s.momentum_score)"
                />
              </div>
            </div>
            <div class="sr-leader">
              <span class="leader-text" @click.stop="goToStock(s.leading_stock)">{{ s.leading_stock }}</span>
            </div>
          </div>
        </div>
        <div v-else class="panel-empty">NO DATA</div>
      </div>
    </div>

    <div v-show="activeTab === 'rotation'">
      <div class="surface-panel">
        <div class="panel-header"><span class="panel-title">ROTATION SIGNALS</span></div>
        <div v-if="loading" class="panel-empty">LOADING...</div>
        <div v-else-if="rotationSignals.length" class="rotation-list">
          <div v-for="r in rotationSignals" :key="r.sector + r.type" class="rotation-row">
            <div class="rr-sector">{{ r.sector }}</div>
            <div class="rr-signal" :class="r.signal === 'entering' || r.signal === 'bullish' ? 'sig-rise' : r.signal === 'exiting' || r.signal === 'bearish' ? 'sig-fall' : 'sig-neutral'">
              {{ r.signal.toUpperCase() }}
            </div>
            <div class="rr-type">{{ r.type.toUpperCase() }}</div>
          </div>
        </div>
        <div v-else class="panel-empty">NO ROTATION SIGNALS</div>
      </div>
    </div>

    <div v-show="activeTab === 'snapshot'">
      <div class="snapshot-grid">
        <div class="surface-panel">
          <div class="panel-header"><span class="panel-title">TOP GAINERS</span></div>
          <DataTable
            v-if="topGainers.length"
            :columns="snapshotColumns"
            :rows="topGainers as unknown as Record<string, unknown>[]"
            row-key="symbol"
            @row-click="(row: Record<string, unknown>) => goToStock(row.symbol as string)"
          >
            <template #cell-symbol="{ value }">
              <span class="code-text">{{ value }}</span>
            </template>
            <template #cell-change_pct="{ value }">
              <span class="mono val-rise">{{ formatPct((value as number) ?? 0) }}</span>
            </template>
          </DataTable>
          <div v-else class="panel-empty">NO DATA</div>
        </div>
        <div class="surface-panel">
          <div class="panel-header"><span class="panel-title">TOP LOSERS</span></div>
          <DataTable
            v-if="topLosers.length"
            :columns="snapshotColumns"
            :rows="topLosers as unknown as Record<string, unknown>[]"
            row-key="symbol"
            @row-click="(row: Record<string, unknown>) => goToStock(row.symbol as string)"
          >
            <template #cell-symbol="{ value }">
              <span class="code-text">{{ value }}</span>
            </template>
            <template #cell-change_pct="{ value }">
              <span class="mono val-fall">{{ formatPct((value as number) ?? 0) }}</span>
            </template>
          </DataTable>
          <div v-else class="panel-empty">NO DATA</div>
        </div>
      </div>
    </div>

    <teleport to="body">
      <div v-if="detailVisible" class="modal-overlay" @click.self="detailVisible = false">
        <div class="modal-content surface-panel">
          <div class="modal-header">
            <span class="modal-title">{{ detailSector }} — CONSTITUENTS</span>
            <button class="modal-close" @click="detailVisible = false">ESC</button>
          </div>
          <DataTable
            v-if="detailStocks.length"
            :columns="detailColumns"
            :rows="detailStocks as unknown as Record<string, unknown>[]"
            row-key="symbol"
            @row-click="(row: Record<string, unknown>) => goToStock(row.symbol as string)"
          >
            <template #cell-symbol="{ value }">
              <span class="code-text">{{ value }}</span>
            </template>
            <template #cell-change_pct="{ value }">
              <span class="mono" :class="((value as number) ?? 0) >= 0 ? 'val-rise' : 'val-fall'">
                {{ formatPct((value as number) ?? 0) }}
              </span>
            </template>
          </DataTable>
          <div v-else class="panel-empty">LOADING...</div>
        </div>
      </div>
    </teleport>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useQuery, invalidateQuery } from '@/composables/useQuery'
import { useApiError } from '@/composables/useApiError'
import { api } from '@/api'
import { formatPct, safeToFixed } from '@/utils/format'
import DataTable from '@/components/ui/DataTable.vue'
import type { ColumnDef } from '@/components/ui/DataTable.vue'
import type { SectorStrengthItem, SectorRotationData, SectorDetail } from '@/types'

const { handleApiError } = useApiError()

interface RotationSignalItem {
  type: string
  sector: string
  signal: string
  change_pct?: number
}

const router = useRouter()
const activeTab = ref('strength')

const {
  data: strengthData,
  isLoading: strengthLoading,
} = useQuery<SectorStrengthItem[]>({
  key: 'sector/strength',
  fetcher: () => api.sector.strength() as Promise<SectorStrengthItem[]>,
})

const rotationEnabled = computed(() => activeTab.value === 'rotation')
const {
  data: rotationResult,
} = useQuery<SectorRotationData>({
  key: 'sector/rotation',
  fetcher: () => api.sector.rotation() as Promise<SectorRotationData>,
  enabled: rotationEnabled,
})

const sectors = computed(() => strengthData.value ?? [])
const rotationData = computed(() => rotationResult.value ?? null)
const rotationSignals = computed<RotationSignalItem[]>(() => {
  const rd = rotationData.value
  if (!rd) return []
  return ('signals' in rd ? (rd as unknown as { signals: RotationSignalItem[] }).signals : []) ?? []
})
const loading = strengthLoading

const topGainers = ref<{ symbol: string; name: string; change_pct: number }[]>([])
const topLosers = ref<{ symbol: string; name: string; change_pct: number }[]>([])

const detailVisible = ref(false)
const detailSector = ref('')
const detailStocks = ref<SectorDetail['stocks']>([])

const snapshotColumns: ColumnDef[] = [
  { key: 'symbol', label: 'CODE', width: '90px', code: true },
  { key: 'name', label: 'NAME', width: '100px' },
  { key: 'change_pct', label: 'CHG%', align: 'right', width: '80px' },
]

const detailColumns: ColumnDef[] = [
  { key: 'symbol', label: 'CODE', width: '90px', code: true },
  { key: 'name', label: 'NAME', width: '100px' },
  { key: 'change_pct', label: 'CHG%', align: 'right', width: '80px' },
]

function momentumStyle(momentum: number): Record<string, string> {
  const maxMom = 100
  const pct = Math.min(Math.abs(momentum) / maxMom * 50, 50)
  if (momentum >= 0) {
    return { left: '50%', width: pct + '%' }
  }
  return { right: '50%', width: pct + '%' }
}

function formatFlow(v: number): string {
  if (v == null || isNaN(v)) return '-'
  const abs = Math.abs(v)
  const sign = v >= 0 ? '+' : '-'
  if (abs >= 1e8) return sign + safeToFixed(abs / 1e8, 2) + 'B'
  if (abs >= 1e4) return sign + safeToFixed(abs / 1e4, 1) + 'W'
  return sign + safeToFixed(abs, 0)
}

function switchTab(tab: string) {
  activeTab.value = tab
  if (tab === 'snapshot' && !topGainers.value.length) computeSnapshot()
}

function computeSnapshot() {
  const allSectors = sectors.value
  const sorted = [...allSectors].sort((a, b) => b.change_pct - a.change_pct)
  topGainers.value = sorted.slice(0, 5).map(s => ({
    symbol: s.leading_stock,
    name: s.name,
    change_pct: s.change_pct,
  }))
  topLosers.value = sorted.slice(-5).reverse().map(s => ({
    symbol: s.leading_stock,
    name: s.name,
    change_pct: s.change_pct,
  }))
}

async function openDetail(sectorName: string) {
  detailSector.value = sectorName
  detailVisible.value = true
  detailStocks.value = []
  try {
    const data = await api.sector.detail(sectorName)
    detailStocks.value = data?.stocks ?? []
  } catch (err) {
    handleApiError(err, '获取板块详情失败')
    detailStocks.value = []
  }
}

function goToStock(symbol: string) {
  router.push(`/stock/${symbol}`)
}
</script>

<style scoped>
.sector-page {
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

.strength-list { display: grid; }

.strength-row {
  display: flex;
  align-items: center;
  height: 56px;
  padding: 0 var(--u4);
  cursor: pointer;
  border-bottom: 1px solid var(--border-hair);
  transition: background var(--dur-fast) var(--ease-mechanical);
}

.strength-row:last-child { border-bottom: none; }
.strength-row:hover { background: var(--bg-overlay); }

.sr-rank { width: 44px; flex-shrink: 0; }

.rank-num {
  font-size: 16px;
  font-weight: 700;
  color: var(--text-tertiary);
  font-family: var(--font-mono);
  font-variant-numeric: tabular-nums;
}

.rank-top { color: var(--warn); }

.sr-info {
  flex: 1;
  display: grid;
  gap: 2px;
  min-width: 0;
}

.sr-name {
  font-size: var(--fs-base);
  font-weight: 600;
  color: var(--text-primary);
}

.sr-change {
  font-size: var(--fs-xs);
  font-family: var(--font-mono);
  font-variant-numeric: tabular-nums;
}

.sr-flow {
  font-size: var(--fs-xs);
  color: var(--text-tertiary);
  font-family: var(--font-mono);
  font-variant-numeric: tabular-nums;
}

.sr-momentum { width: 180px; flex-shrink: 0; padding: 0 var(--u3); }

.momentum-track {
  position: relative;
  height: 4px;
  background: var(--bg-plate);
  border-radius: 2px;
}

.momentum-zero {
  position: absolute;
  left: 50%;
  top: 0;
  width: 1px;
  height: 100%;
  background: var(--text-muted);
  transform: translateX(-50%);
}

.momentum-fill {
  position: absolute;
  top: 0;
  height: 100%;
  border-radius: 2px;
  transition: all var(--dur-normal) var(--ease-mechanical);
}

.mom-rise { background: var(--accent); opacity: 0.7; }
.mom-fall { background: var(--accent); opacity: 0.35; }

.sr-leader { width: 80px; flex-shrink: 0; text-align: right; }

.leader-text {
  font-size: var(--fs-sm);
  font-family: var(--font-mono);
  font-variant-numeric: tabular-nums;
  color: var(--accent);
  cursor: pointer;
  transition: opacity var(--dur-fast) var(--ease-mechanical);
}

.leader-text:hover { opacity: 0.7; }

.rotation-list { display: grid; }

.rotation-row {
  display: flex;
  align-items: center;
  gap: var(--u4);
  padding: var(--u3) var(--u4);
  border-bottom: 1px solid var(--border-hair);
}

.rotation-row:last-child { border-bottom: none; }

.rr-sector {
  font-size: var(--fs-base);
  font-weight: 600;
  color: var(--text-primary);
  min-width: 100px;
}

.rr-signal {
  font-size: var(--fs-3xs);
  font-weight: 700;
  padding: 1px 8px;
  border-radius: var(--r-md);
  font-family: var(--font-mono);
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.sig-rise { background: var(--rise-bg); color: var(--rise); }
.sig-fall { background: var(--fall-bg); color: var(--fall); }
.sig-neutral { background: var(--accent-muted); color: var(--accent); }

.rr-type {
  font-size: var(--fs-xs);
  color: var(--text-tertiary);
  font-family: var(--font-mono);
  text-transform: uppercase;
  letter-spacing: 0.08em;
  flex: 1;
}

.snapshot-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--u4);
}

.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  width: 600px;
  max-height: 80vh;
  overflow: auto;
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--u3) var(--u4);
  border-bottom: 1px solid var(--border-hair);
}

.modal-title {
  font-size: var(--fs-xs);
  font-weight: 600;
  color: var(--text-primary);
  font-family: var(--font-mono);
  text-transform: uppercase;
  letter-spacing: 0.1em;
}

.modal-close {
  padding: 2px 8px;
  background: transparent;
  border: 1px solid var(--border-dim);
  border-radius: var(--r-md);
  color: var(--text-tertiary);
  font-size: var(--fs-xs);
  font-family: var(--font-mono);
  text-transform: uppercase;
  letter-spacing: 0.08em;
  cursor: pointer;
  transition: border-color var(--dur-fast) var(--ease-mechanical),
              color var(--dur-fast) var(--ease-mechanical);
}

.modal-close:hover { border-color: var(--accent); color: var(--accent); }

@media (max-width: 768px) {
  .snapshot-grid { grid-template-columns: 1fr; }
  .strength-row { height: auto; padding: var(--u2) var(--u3); flex-wrap: wrap; gap: var(--u2); }
  .sr-momentum { width: 100%; }
}
</style>
