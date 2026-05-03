<template>
  <div class="sector-page">
    <div class="page-hero">
      <h1 class="page-title">板块轮动</h1>
      <p class="page-subtitle">追踪板块资金轮动，把握市场节奏</p>
    </div>

    <div class="tab-bar">
      <button class="apple-tab" :class="{ active: activeTab === 'strength' }" @click="activeTab = 'strength'; fetchStrength()">板块强度</button>
      <button class="apple-tab" :class="{ active: activeTab === 'rotation' }" @click="activeTab = 'rotation'; fetchRotation()">轮动信号</button>
    </div>

    <div v-show="activeTab === 'strength'" class="strength-panel">
      <div v-if="loading" class="loading-state">
        <div class="loading-spinner" /><span>加载中...</span>
      </div>
      <div v-else-if="sectorList.length" class="sector-grid">
        <div v-for="s in sectorList" :key="s.code" class="sector-card apple-card apple-card-interactive" @click="showSectorDetail(s.code)">
          <div class="sector-rank" :class="s.rank <= 3 ? 'top' : ''">{{ s.rank }}</div>
          <div class="sector-info">
            <div class="sector-name">{{ s.name }}</div>
            <div class="sector-meta">
              <span class="mono" :class="s.change_pct >= 0 ? 'text-rise' : 'text-fall'">
                {{ s.change_pct >= 0 ? '+' : '' }}{{ s.change_pct.toFixed(2) }}%
              </span>
              <span class="sector-flow mono" :class="s.main_net_inflow >= 0 ? 'text-rise' : 'text-fall'">
                {{ formatFlow(s.main_net_inflow) }}
              </span>
            </div>
          </div>
          <div class="momentum-bar">
            <div class="m-bar-track">
              <div class="m-bar-fill" :style="{ width: Math.min(Math.max(s.momentum_score / maxMomentum * 100, 2), 100) + '%' }" :class="s.momentum_score > 0 ? 'positive' : 'negative'" />
            </div>
          </div>
          <div class="momentum-score mono">{{ s.momentum_score.toFixed(1) }}</div>
        </div>
      </div>
      <div v-else class="empty-state"><div class="empty-icon">🌐</div><p>暂无数据</p></div>
    </div>

    <div v-show="activeTab === 'rotation'" class="rotation-panel">
      <div v-if="loadingRotation" class="loading-state">
        <div class="loading-spinner" /><span>加载中...</span>
      </div>
      <template v-else-if="rotationData">
        <div v-if="rotationData.signals?.length" class="signals-section">
          <h3 class="section-title">轮动信号</h3>
          <div class="signal-grid">
            <div v-for="(sig, idx) in rotationData.signals" :key="idx" class="signal-card apple-card" :class="sig.type">
              <div class="signal-type">
                <span class="apple-badge" :class="sig.type === 'sector_entering_top' ? 'apple-badge-rise' : 'apple-badge-fall'">
                  {{ sig.type === 'sector_entering_top' ? '↑ 进入前列' : '↓ 退出前列' }}
                </span>
              </div>
              <div class="signal-sector">{{ sig.sector }}</div>
              <div class="signal-text">{{ sig.signal }}</div>
            </div>
          </div>
        </div>
        <div v-else class="empty-state"><div class="empty-icon">📡</div><p>暂无轮动信号</p></div>

        <div class="snapshot-section" v-if="rotationData.snapshot">
          <h3 class="section-title">当前快照</h3>
          <div class="snapshot-grid">
            <div class="snapshot-col apple-card">
              <div class="col-title text-rise">领涨板块</div>
              <div v-for="s in rotationData.snapshot.top_sectors" :key="s.name" class="snapshot-item">
                <span>{{ s.name }}</span>
                <span class="mono" :class="s.change_pct >= 0 ? 'text-rise' : 'text-fall'">{{ s.change_pct >= 0 ? '+' : '' }}{{ s.change_pct.toFixed(2) }}%</span>
              </div>
            </div>
            <div class="snapshot-col apple-card">
              <div class="col-title text-fall">领跌板块</div>
              <div v-for="s in rotationData.snapshot.bottom_sectors" :key="s.name" class="snapshot-item">
                <span>{{ s.name }}</span>
                <span class="mono" :class="s.change_pct >= 0 ? 'text-rise' : 'text-fall'">{{ s.change_pct >= 0 ? '+' : '' }}{{ s.change_pct.toFixed(2) }}%</span>
              </div>
            </div>
          </div>
        </div>
      </template>
    </div>

    <teleport to="body">
      <transition name="fade">
        <div v-if="detailVisible" class="detail-overlay" @click.self="detailVisible = false">
          <div class="detail-modal">
            <div class="detail-header">
              <h3>{{ detailData?.sector?.name || '板块详情' }}</h3>
              <button class="close-btn" @click="detailVisible = false">✕</button>
            </div>
            <div v-if="detailData?.stocks?.length" class="detail-stocks">
              <table class="apple-table">
                <thead><tr><th>代码</th><th>名称</th><th>最新价</th><th>涨跌幅</th><th>换手率</th></tr></thead>
                <tbody>
                  <tr v-for="s in detailData.stocks" :key="s.symbol" @click="goToStock(s.symbol)">
                    <td class="mono">{{ s.symbol }}</td>
                    <td>{{ s.name }}</td>
                    <td class="mono">{{ s.price.toFixed(2) }}</td>
                    <td class="mono" :class="s.change_pct >= 0 ? 'text-rise' : 'text-fall'">{{ s.change_pct >= 0 ? '+' : '' }}{{ s.change_pct.toFixed(2) }}%</td>
                    <td class="mono">{{ (s.turnover_rate || 0).toFixed(2) }}%</td>
                  </tr>
                </tbody>
              </table>
            </div>
            <div v-else class="empty-state">加载中...</div>
          </div>
        </div>
      </transition>
    </teleport>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '@/api'
import type { SectorStrengthItem, SectorRotationData, SectorDetail } from '@/types'

const router = useRouter()
const activeTab = ref('strength')
const sectorList = ref<SectorStrengthItem[]>([])
const rotationData = ref<SectorRotationData | null>(null)
const detailData = ref<SectorDetail | null>(null)
const detailVisible = ref(false)
const loading = ref(false)
const loadingRotation = ref(false)

const maxMomentum = computed(() => {
  if (!sectorList.value.length) return 1
  return Math.max(...sectorList.value.map(s => Math.abs(s.momentum_score)), 1)
})

async function fetchStrength() {
  loading.value = true
  try { sectorList.value = await api.sector.strength(30) } catch { sectorList.value = [] }
  finally { loading.value = false }
}

async function fetchRotation() {
  loadingRotation.value = true
  try { rotationData.value = await api.sector.rotation() } catch { rotationData.value = null }
  finally { loadingRotation.value = false }
}

async function showSectorDetail(code: string) {
  detailVisible.value = true
  try { detailData.value = await api.sector.detail(code) } catch { detailData.value = null }
}

function goToStock(symbol: string) {
  detailVisible.value = false
  router.push(`/stock/${symbol}`)
}

function formatFlow(v: number) {
  if (!v) return '-'
  const abs = Math.abs(v)
  const sign = v >= 0 ? '+' : '-'
  if (abs >= 1e8) return sign + (abs / 1e8).toFixed(1) + '亿'
  if (abs >= 1e4) return sign + (abs / 1e4).toFixed(0) + '万'
  return sign + abs.toFixed(0)
}

onMounted(fetchStrength)
</script>

<style scoped>
.sector-page { max-width: 1100px; margin: 0 auto; }
.page-hero { margin-bottom: var(--space-6); }
.page-title { font-size: var(--text-3xl); font-weight: 700; letter-spacing: -0.03em; color: var(--text-primary); line-height: var(--leading-tight); }
.page-subtitle { font-size: var(--text-md); color: var(--text-secondary); margin-top: var(--space-2); }
.tab-bar { display: inline-flex; gap: 2px; padding: 3px; background: var(--bg-elevated); border-radius: var(--radius-sm); border: 1px solid var(--border-subtle); margin-bottom: var(--space-6); }
.sector-grid { display: flex; flex-direction: column; gap: var(--space-2); }
.sector-card { display: flex; align-items: center; gap: var(--space-4); padding: var(--space-3) var(--space-5); }
.sector-rank { width: 32px; height: 32px; border-radius: 50%; background: var(--bg-elevated); display: flex; align-items: center; justify-content: center; font-size: var(--text-sm); font-weight: 700; color: var(--text-secondary); flex-shrink: 0; }
.sector-rank.top { background: var(--bg-gradient-accent); color: white; box-shadow: var(--glow-accent); }
.sector-info { flex: 1; min-width: 0; }
.sector-name { font-size: var(--text-md); font-weight: 600; color: var(--text-primary); }
.sector-meta { display: flex; gap: var(--space-3); font-size: var(--text-xs); margin-top: 2px; }
.momentum-bar { width: 140px; flex-shrink: 0; }
.m-bar-track { height: 6px; background: var(--bg-elevated); border-radius: 3px; overflow: hidden; }
.m-bar-fill { height: 100%; border-radius: 3px; transition: width var(--duration-slow) var(--ease-out); }
.m-bar-fill.positive { background: linear-gradient(90deg, var(--accent), var(--rise)); }
.m-bar-fill.negative { background: linear-gradient(90deg, var(--fall), var(--accent)); }
.momentum-score { width: 50px; font-size: var(--text-sm); font-weight: 600; text-align: right; flex-shrink: 0; }
.signals-section { margin-bottom: var(--space-6); }
.section-title { font-size: var(--text-sm); color: var(--text-secondary); margin-bottom: var(--space-4); font-weight: 600; text-transform: uppercase; letter-spacing: 0.04em; }
.signal-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: var(--space-3); }
.signal-card { padding: var(--space-4); }
.signal-card.sector_entering_top { border-left: 3px solid var(--rise); }
.signal-card.sector_leaving_top { border-left: 3px solid var(--fall); }
.signal-type { margin-bottom: var(--space-2); }
.signal-sector { font-size: var(--text-md); font-weight: 600; color: var(--text-primary); margin-bottom: var(--space-1); }
.signal-text { font-size: var(--text-xs); color: var(--text-secondary); line-height: 1.5; }
.snapshot-section { }
.snapshot-grid { display: grid; grid-template-columns: 1fr 1fr; gap: var(--space-4); }
.snapshot-col { padding: var(--space-4); }
.col-title { font-size: var(--text-sm); font-weight: 600; margin-bottom: var(--space-3); }
.snapshot-item { display: flex; justify-content: space-between; padding: var(--space-2) 0; font-size: var(--text-sm); border-bottom: 1px solid var(--border-subtle); }
.detail-overlay { position: fixed; inset: 0; background: rgba(0, 0, 0, 0.5); z-index: 1000; display: flex; align-items: center; justify-content: center; backdrop-filter: blur(8px); }
.detail-modal { width: 620px; max-height: 80vh; background: var(--bg-surface); border: 1px solid var(--border); border-radius: var(--radius-xl); box-shadow: var(--shadow-float); overflow-y: auto; }
.detail-header { display: flex; align-items: center; justify-content: space-between; padding: var(--space-5); border-bottom: 1px solid var(--border-subtle); }
.detail-header h3 { font-size: var(--text-lg); font-weight: 600; color: var(--text-primary); }
.close-btn { background: none; border: none; color: var(--text-tertiary); cursor: pointer; font-size: var(--text-lg); padding: var(--space-1); border-radius: var(--radius-xs); transition: all var(--transition-fast); }
.close-btn:hover { color: var(--text-primary); background: var(--bg-hover); }
.detail-stocks { }
.loading-state { display: flex; flex-direction: column; align-items: center; gap: var(--space-3); padding: var(--space-16); color: var(--text-tertiary); }
.loading-spinner { width: 24px; height: 24px; border: 2px solid var(--border); border-top-color: var(--accent); border-radius: 50%; animation: spin 0.8s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
.empty-state { text-align: center; padding: var(--space-16); color: var(--text-tertiary); }
.empty-icon { font-size: 40px; margin-bottom: var(--space-3); }
</style>
