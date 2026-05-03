<template>
  <div class="moneyflow-page">
    <div class="page-hero">
      <h1 class="page-title">资金流向</h1>
      <p class="page-subtitle">追踪主力资金动向，洞察市场脉搏</p>
    </div>

    <div class="tab-bar">
      <button class="apple-tab" :class="{ active: activeTab === 'ranking' }" @click="activeTab = 'ranking'; fetchRanking()">资金排名</button>
      <button class="apple-tab" :class="{ active: activeTab === 'sector' }" @click="activeTab = 'sector'; fetchSectorFlow()">板块资金</button>
    </div>

    <div v-show="activeTab === 'ranking'" class="ranking-panel">
      <div v-if="loading" class="loading-state">
        <div class="loading-spinner" /><span>加载中...</span>
      </div>
      <div v-else-if="rankingList.length" class="table-wrap">
        <table class="apple-table">
          <thead>
            <tr><th>代码</th><th>名称</th><th>最新价</th><th>涨跌幅</th><th>主力净流入</th><th>超大单</th><th>大单</th><th>中单</th><th>小单</th></tr>
          </thead>
          <tbody>
            <tr v-for="s in rankingList" :key="s.symbol" @click="goToStock(s.symbol)">
              <td class="mono">{{ s.symbol }}</td>
              <td>{{ s.name }}</td>
              <td class="mono">{{ (s.price || 0).toFixed(2) }}</td>
              <td class="mono" :class="(s.change_pct || 0) >= 0 ? 'text-rise' : 'text-fall'">
                {{ (s.change_pct || 0) >= 0 ? '+' : '' }}{{ (s.change_pct || 0).toFixed(2) }}%
              </td>
              <td class="mono" :class="(s.main_net_inflow || 0) >= 0 ? 'text-rise' : 'text-fall'">
                {{ formatFlow(s.main_net_inflow) }}
              </td>
              <td class="mono" :class="(s.super_large_net || 0) >= 0 ? 'text-rise' : 'text-fall'">{{ formatFlow(s.super_large_net) }}</td>
              <td class="mono" :class="(s.large_net || 0) >= 0 ? 'text-rise' : 'text-fall'">{{ formatFlow(s.large_net) }}</td>
              <td class="mono" :class="(s.medium_net || 0) >= 0 ? 'text-rise' : 'text-fall'">{{ formatFlow(s.medium_net) }}</td>
              <td class="mono" :class="(s.small_net || 0) >= 0 ? 'text-rise' : 'text-fall'">{{ formatFlow(s.small_net) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <div v-else class="empty-state"><div class="empty-icon">💰</div><p>暂无数据</p></div>
    </div>

    <div v-show="activeTab === 'sector'" class="sector-panel">
      <div v-if="loadingSector" class="loading-state">
        <div class="loading-spinner" /><span>加载中...</span>
      </div>
      <div v-else-if="sectorFlow.length" class="sector-flow-list">
        <div v-for="s in sectorFlow" :key="s.code" class="sector-flow-card apple-card">
          <div class="sector-info">
            <div class="sector-name">{{ s.name }}</div>
            <div class="sector-change mono" :class="s.change_pct >= 0 ? 'text-rise' : 'text-fall'">
              {{ s.change_pct >= 0 ? '+' : '' }}{{ s.change_pct.toFixed(2) }}%
            </div>
          </div>
          <div class="sector-flow-bar" v-if="maxSectorFlow > 1">
            <div class="flow-bar-track">
              <div class="flow-bar-fill" :class="s.main_net_inflow >= 0 ? 'inflow' : 'outflow'" :style="{ width: Math.min(Math.abs(s.main_net_inflow) / maxSectorFlow * 100, 100) + '%' }" />
            </div>
          </div>
          <div class="sector-flow-val mono" :class="s.main_net_inflow ? (s.main_net_inflow >= 0 ? 'text-rise' : 'text-fall') : 'text-tertiary'">
            {{ s.main_net_inflow ? formatFlow(s.main_net_inflow) : '-' }}
          </div>
        </div>
      </div>
      <div v-else class="empty-state"><div class="empty-icon">💰</div><p>暂无数据</p></div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '@/api'
import type { CapitalFlowRealtime, SectorFlowItem } from '@/types'

const router = useRouter()
const activeTab = ref('ranking')
const rankingList = ref<CapitalFlowRealtime[]>([])
const sectorFlow = ref<SectorFlowItem[]>([])
const loading = ref(false)
const loadingSector = ref(false)

const maxSectorFlow = computed(() => {
  if (!sectorFlow.value.length) return 1
  return Math.max(...sectorFlow.value.map(s => Math.abs(s.main_net_inflow)), 1)
})

async function fetchRanking() {
  loading.value = true
  try { rankingList.value = await api.moneyFlow.ranking('main_net', 30) } catch { rankingList.value = [] }
  finally { loading.value = false }
}

async function fetchSectorFlow() {
  loadingSector.value = true
  try { sectorFlow.value = await api.moneyFlow.sector() } catch { sectorFlow.value = [] }
  finally { loadingSector.value = false }
}

function goToStock(symbol: string) { router.push(`/stock/${symbol}`) }

function formatFlow(v: number | undefined) {
  if (v === undefined || v === null) return '-'
  const abs = Math.abs(v)
  const sign = v >= 0 ? '+' : '-'
  if (abs >= 1e8) return sign + (abs / 1e8).toFixed(2) + '亿'
  if (abs >= 1e4) return sign + (abs / 1e4).toFixed(1) + '万'
  return sign + abs.toFixed(0)
}

onMounted(fetchRanking)
</script>

<style scoped>
.moneyflow-page { max-width: 1200px; margin: 0 auto; }
.page-hero { margin-bottom: var(--space-6); }
.page-title { font-size: var(--text-3xl); font-weight: 700; letter-spacing: -0.03em; color: var(--text-primary); line-height: var(--leading-tight); }
.page-subtitle { font-size: var(--text-md); color: var(--text-secondary); margin-top: var(--space-2); }
.tab-bar { display: inline-flex; gap: 2px; padding: 3px; background: var(--bg-elevated); border-radius: var(--radius-sm); border: 1px solid var(--border-subtle); margin-bottom: var(--space-6); }
.table-wrap { border-radius: var(--radius-lg); border: 1px solid var(--border); overflow: hidden; }
.table-wrap .apple-table th { background: var(--bg-surface); }
.sector-flow-list { display: flex; flex-direction: column; gap: var(--space-2); }
.sector-flow-card { display: flex; align-items: center; gap: var(--space-4); padding: var(--space-3) var(--space-5); }
.sector-info { width: 140px; flex-shrink: 0; }
.sector-name { font-size: var(--text-sm); font-weight: 600; color: var(--text-primary); }
.sector-change { font-size: var(--text-xs); margin-top: 2px; }
.sector-flow-bar { flex: 1; }
.flow-bar-track { height: 6px; background: var(--bg-elevated); border-radius: 3px; overflow: hidden; }
.flow-bar-fill { height: 100%; border-radius: 3px; transition: width var(--duration-slow) var(--ease-out); }
.flow-bar-fill.inflow { background: linear-gradient(90deg, var(--rise), rgba(255,59,48,0.6)); }
.flow-bar-fill.outflow { background: linear-gradient(90deg, var(--fall), rgba(52,199,89,0.6)); }
.sector-flow-val { width: 90px; font-size: var(--text-sm); text-align: right; flex-shrink: 0; font-weight: 500; }
.loading-state { display: flex; flex-direction: column; align-items: center; gap: var(--space-3); padding: var(--space-16); color: var(--text-tertiary); }
.loading-spinner { width: 24px; height: 24px; border: 2px solid var(--border); border-top-color: var(--accent); border-radius: 50%; animation: spin 0.8s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
.empty-state { text-align: center; padding: var(--space-16); color: var(--text-tertiary); }
.empty-icon { font-size: 40px; margin-bottom: var(--space-3); }
</style>
