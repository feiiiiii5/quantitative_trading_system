<template>
  <div class="screener-page">
    <div class="page-hero">
      <h1 class="page-title">智能选股</h1>
      <p class="page-subtitle">多维度条件筛选，发现投资机会</p>
    </div>

    <div class="screener-body">
      <div class="preset-panel">
        <div class="preset-header">
          <h3 class="preset-title">选股策略</h3>
        </div>
        <div class="preset-list">
          <div v-for="p in presets" :key="p.id" class="preset-card apple-card apple-card-interactive" :class="{ active: selectedPreset === p.id }" @click="selectPreset(p.id)">
            <div class="preset-name">{{ p.name }}</div>
            <div class="preset-desc">{{ p.description }}</div>
            <div class="preset-tags">
              <span class="apple-badge" :class="categoryBadge(p.category)">{{ categoryLabel(p.category) }}</span>
            </div>
          </div>
        </div>
      </div>

      <div class="result-panel">
        <div class="result-header">
          <div class="result-info">
            <span v-if="results" class="result-count">共筛选出 <strong>{{ results.total }}</strong> 只股票</span>
          </div>
          <button class="apple-btn apple-btn-primary" @click="runScreener" :disabled="!selectedPreset || running">
            {{ running ? '筛选中...' : '开始选股' }}
          </button>
        </div>

        <div v-if="running" class="loading-state">
          <div class="loading-spinner" />
          <span>筛选中，请稍候...</span>
        </div>
        <div v-else-if="results && results.stocks.length" class="stock-table-wrap">
          <table class="apple-table">
            <thead>
              <tr>
                <th>代码</th><th>名称</th><th>最新价</th><th>涨跌幅</th><th>成交额</th><th>换手率</th><th>PE</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="s in results.stocks" :key="s.symbol" @click="goToStock(s.symbol)">
                <td class="mono">{{ s.symbol }}</td>
                <td>{{ s.name }}</td>
                <td class="mono">{{ (s.price || 0).toFixed(2) }}</td>
                <td class="mono" :class="(s.change_pct || 0) >= 0 ? 'text-rise' : 'text-fall'">
                  {{ (s.change_pct || 0) >= 0 ? '+' : '' }}{{ (s.change_pct || 0).toFixed(2) }}%
                </td>
                <td class="mono">{{ formatAmount(s.amount) }}</td>
                <td class="mono">{{ (s.turnover_rate || 0).toFixed(2) }}%</td>
                <td class="mono">{{ s.pe ? s.pe.toFixed(1) : '-' }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <div v-else-if="results && !results.stocks.length" class="empty-state">
          <div class="empty-icon">🔍</div>
          <p>未筛选到符合条件的股票</p>
        </div>
        <div v-else class="empty-state">
          <div class="empty-icon">📊</div>
          <p>请选择选股策略后点击"开始选股"</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '@/api'
import type { ScreenerPreset, ScreenerResult } from '@/types'

const router = useRouter()
const presets = ref<ScreenerPreset[]>([])
const selectedPreset = ref('')
const results = ref<ScreenerResult | null>(null)
const running = ref(false)

function categoryLabel(cat: string) {
  const map: Record<string, string> = { technical: '技术面', fundamental: '基本面', market_activity: '市场活跃' }
  return map[cat] || cat
}

function categoryBadge(cat: string) {
  const map: Record<string, string> = { technical: 'apple-badge-accent', fundamental: 'apple-badge-fall', market_activity: 'apple-badge-warn' }
  return map[cat] || 'apple-badge-accent'
}

function selectPreset(id: string) {
  selectedPreset.value = selectedPreset.value === id ? '' : id
}

async function fetchPresets() {
  try { presets.value = await api.screener.presets() } catch { presets.value = [] }
}

async function runScreener() {
  if (!selectedPreset.value) return
  running.value = true
  try {
    results.value = await api.screener.run(selectedPreset.value)
  } catch { results.value = null }
  finally { running.value = false }
}

function goToStock(symbol: string) { router.push(`/stock/${symbol}`) }

function formatAmount(v: number | undefined) {
  if (!v) return '-'
  if (v >= 1e8) return (v / 1e8).toFixed(1) + '亿'
  if (v >= 1e4) return (v / 1e4).toFixed(1) + '万'
  return v.toFixed(0)
}

onMounted(fetchPresets)
</script>

<style scoped>
.screener-page { height: 100%; display: flex; flex-direction: column; }
.page-hero { margin-bottom: var(--space-6); }
.page-title { font-size: var(--text-3xl); font-weight: 700; letter-spacing: -0.03em; color: var(--text-primary); line-height: var(--leading-tight); }
.page-subtitle { font-size: var(--text-md); color: var(--text-secondary); margin-top: var(--space-2); }
.screener-body { display: flex; gap: var(--space-6); flex: 1; min-height: 0; }
.preset-panel { width: 300px; flex-shrink: 0; overflow-y: auto; }
.preset-header { margin-bottom: var(--space-4); }
.preset-title { font-size: var(--text-sm); color: var(--text-secondary); font-weight: 600; text-transform: uppercase; letter-spacing: 0.04em; }
.preset-list { display: flex; flex-direction: column; gap: var(--space-2); }
.preset-card { padding: var(--space-4); }
.preset-card.active { border-color: var(--accent); background: var(--accent-soft); }
.preset-name { font-size: var(--text-md); font-weight: 600; color: var(--text-primary); margin-bottom: var(--space-1); }
.preset-desc { font-size: var(--text-xs); color: var(--text-tertiary); margin-bottom: var(--space-2); line-height: 1.4; }
.preset-tags { display: flex; gap: var(--space-1); }
.result-panel { flex: 1; min-width: 0; display: flex; flex-direction: column; }
.result-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: var(--space-4); }
.result-info { }
.result-count { font-size: var(--text-sm); color: var(--text-secondary); }
.result-count strong { color: var(--accent); font-weight: 600; }
.stock-table-wrap { flex: 1; overflow-y: auto; border-radius: var(--radius-lg); border: 1px solid var(--border); }
.stock-table-wrap .apple-table th { background: var(--bg-surface); }
.loading-state { display: flex; flex-direction: column; align-items: center; gap: var(--space-3); padding: var(--space-16); color: var(--text-tertiary); }
.loading-spinner { width: 24px; height: 24px; border: 2px solid var(--border); border-top-color: var(--accent); border-radius: 50%; animation: spin 0.8s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
.empty-state { text-align: center; padding: var(--space-16); color: var(--text-tertiary); }
.empty-icon { font-size: 40px; margin-bottom: var(--space-3); }
</style>
