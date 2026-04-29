<template>
  <div class="watchlist-page">
    <div class="page-header">
      <h1 class="page-title">自选股</h1>
      <div class="header-actions">
        <div class="add-row">
          <input v-model="addSymbol" placeholder="输入股票代码" class="add-input" @keyup.enter="addStock" />
          <button class="add-btn" @click="addStock">添加</button>
        </div>
      </div>
    </div>

    <div class="main-layout">
      <div class="stocks-section">
        <div class="list-toolbar">
          <span class="list-count">共 {{ stocks.length }} 只</span>
          <button class="refresh-btn" @click="refreshPrices" :class="{ spinning: refreshing }">刷新行情</button>
        </div>
        <div v-if="stocks.length" class="stock-list">
          <div
            v-for="(stock, idx) in stocks"
            :key="stock.symbol"
            class="stock-row"
            :class="{ up: stock.change_pct >= 0, down: stock.change_pct < 0 }"
            draggable="true"
            @dragstart="dragStart(idx)"
            @dragover.prevent="dragOver(idx)"
            @drop="drop(idx)"
            @click="$router.push(`/stock/${stock.symbol}`)"
          >
            <span class="drag-handle">⠿</span>
            <span class="stock-code">{{ stock.symbol }}</span>
            <span class="stock-name">{{ stock.name }}</span>
            <span class="stock-price">{{ (stock.price || 0).toFixed(2) }}</span>
            <span class="stock-pct">{{ stock.change_pct >= 0 ? '+' : '' }}{{ (stock.change_pct || 0).toFixed(2) }}%</span>
            <button class="remove-btn" @click.stop="removeStock(stock.symbol)">✕</button>
          </div>
        </div>
        <div v-else class="empty-state">暂无自选股，请添加</div>
      </div>

      <div class="alerts-section">
        <div class="alerts-header">
          <h2 class="section-title">价格预警</h2>
          <button class="add-alert-btn" @click="showAlertForm = !showAlertForm">+ 新增</button>
        </div>

        <div v-if="showAlertForm" class="alert-form">
          <div class="form-row">
            <input v-model="alertForm.symbol" placeholder="股票代码" class="form-input" />
          </div>
          <div class="form-row">
            <select v-model="alertForm.type" class="form-input">
              <option value="price_above">价格高于</option>
              <option value="price_below">价格低于</option>
              <option value="pct_change_above">涨幅超过(%)</option>
            </select>
          </div>
          <div class="form-row">
            <input v-model.number="alertForm.value" type="number" placeholder="目标值" class="form-input" />
          </div>
          <div class="form-btns">
            <button class="btn-save" @click="addAlert">保存</button>
            <button class="btn-cancel" @click="showAlertForm = false">取消</button>
          </div>
        </div>

        <div v-if="alerts.length" class="alert-list">
          <div v-for="alert in alerts" :key="alert.id" class="alert-row" :class="{ triggered: alert.triggered }">
            <div class="alert-info">
              <span class="alert-symbol">{{ alert.symbol }}</span>
              <span class="alert-type">{{ alertLabel(alert.alert_type) }}</span>
              <span class="alert-value">{{ alert.value }}</span>
            </div>
            <div class="alert-actions">
              <span v-if="alert.triggered" class="alert-triggered">已触发</span>
              <button class="alert-del" @click="removeAlert(alert.id)">✕</button>
            </div>
          </div>
        </div>
        <div v-else class="empty-state-small">暂无预警</div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue'
import { api } from '../api'
import { useWebSocketStore } from '../stores/websocket.store'

const addSymbol = ref('')
const stocks = ref<any[]>([])
const alerts = ref<any[]>([])
const refreshing = ref(false)
const showAlertForm = ref(false)
const alertForm = ref({ symbol: '', type: 'price_above', value: 0 })
let dragIdx = -1
let updateTimer: any = null

const wsStore = useWebSocketStore()

watch(() => wsStore.lastMessage, (msg: any) => {
  if (!msg) return
  if (msg.type === 'quote_update') {
    const data = msg.data || {}
    if (data.quotes) {
      const updates = data.quotes
      stocks.value = stocks.value.map(s => {
        const u = updates[s.symbol]
        if (u) return { ...s, price: u.price ?? s.price, change_pct: u.change_pct ?? s.change_pct }
        return s
      })
    }
  } else if (msg.type === 'alert') {
    const a = msg.data || msg
    const idx = alerts.value.findIndex(x => x.symbol === a.symbol && x.alert_type === a.alert_type)
    if (idx >= 0) alerts.value[idx] = { ...alerts.value[idx], triggered: true }
  }
})

function alertLabel(type: string): string {
  if (type === 'price_above') return '价格高于'
  if (type === 'price_below') return '价格低于'
  if (type === 'pct_change_above') return '涨幅超%'
  return type
}

async function loadData() {
  try {
    const data = await api.getWatchlist()
    if (data) {
      const syms = data.symbols || []
      const quotes = data.quotes || {}
      stocks.value = syms.map((s: string) => {
        const q = quotes[s] || {}
        return { symbol: s, name: q.name || s, price: q.price, change_pct: q.change_pct, ...q }
      })
    }
  } catch (e) {}
}

async function loadAlerts() {
  try {
    const data = await api.getAlerts()
    if (data) alerts.value = data.alerts || data || []
  } catch (e) {}
}

async function addStock() {
  const sym = addSymbol.value.trim()
  if (!sym) return
  try {
    await api.addToWatchlist(sym)
    addSymbol.value = ''
    await loadData()
  } catch (e) {}
}

async function removeStock(symbol: string) {
  try {
    await api.removeFromWatchlist(symbol)
    await loadData()
  } catch (e) {}
}

async function refreshPrices() {
  refreshing.value = true
  try {
    await loadData()
  } finally {
    refreshing.value = false
  }
}

async function addAlert() {
  try {
    await api.addAlert(alertForm.value.symbol, alertForm.value.type, alertForm.value.value)
    showAlertForm.value = false
    alertForm.value = { symbol: '', type: 'price_above', value: 0 }
    await loadAlerts()
  } catch (e) {}
}

async function removeAlert(id: string) {
  try {
    await api.removeAlert(id)
    await loadAlerts()
  } catch (e) {}
}

function dragStart(idx: number) { dragIdx = idx }
function dragOver(idx: number) {}
function drop(idx: number) {
  if (dragIdx === idx || dragIdx < 0) return
  const item = stocks.value.splice(dragIdx, 1)[0]
  stocks.value.splice(idx, 0, item)
  dragIdx = -1
  api.reorderWatchlist(stocks.value.map(s => s.symbol))
}

onMounted(() => {
  loadData().then(() => {
    const syms = stocks.value.map((s: any) => s.symbol).filter(Boolean)
    if (syms.length) wsStore.subscribe(syms)
  })
  loadAlerts()
  updateTimer = setInterval(loadData, 30000)
  wsStore.connect()
})

onUnmounted(() => {
  if (updateTimer) clearInterval(updateTimer)
  wsStore.disconnect()
})
</script>

<style scoped>
.watchlist-page { padding: 20px; max-width: 1200px; margin: 0 auto; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.page-title { font-size: 20px; font-weight: 700; color: var(--text-primary); }
.add-row { display: flex; gap: 6px; }
.add-input { padding: 7px 12px; background: var(--bg-secondary); border: 1px solid var(--border-color); border-radius: var(--radius-sm); color: var(--text-primary); font-size: 12px; font-family: var(--font-mono); width: 140px; }
.add-input:focus { outline: none; border-color: var(--accent-cyan); }
.add-btn { padding: 7px 14px; background: linear-gradient(135deg, #4d9fff, #a78bfa); color: white; border: none; border-radius: var(--radius-sm); font-size: 12px; font-weight: 600; cursor: pointer; }

.main-layout { display: grid; grid-template-columns: 1fr 320px; gap: 16px; }

.stocks-section { background: var(--bg-secondary); border: 1px solid var(--border-color); border-radius: var(--radius-lg); padding: 14px; }
.list-toolbar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }
.list-count { font-size: 11px; color: var(--text-tertiary); }
.refresh-btn { padding: 4px 10px; background: transparent; border: 1px solid var(--border-color); border-radius: 3px; color: var(--text-secondary); font-size: 11px; cursor: pointer; }
.refresh-btn:hover { color: var(--text-primary); }
.refresh-btn.spinning { opacity: 0.5; }

.stock-list { display: flex; flex-direction: column; gap: 2px; }
.stock-row { display: flex; align-items: center; gap: 8px; padding: 8px 10px; border-radius: var(--radius-sm); cursor: pointer; transition: background 0.1s; }
.stock-row:hover { background: rgba(255,255,255,0.04); }
.drag-handle { color: var(--text-tertiary); cursor: grab; font-size: 14px; }
.stock-code { font-family: var(--font-mono); font-size: 12px; color: var(--accent-cyan); width: 60px; }
.stock-name { font-size: 12px; color: var(--text-primary); flex: 1; }
.stock-price { font-family: var(--font-mono); font-size: 12px; font-weight: 600; color: var(--text-primary); }
.stock-pct { font-family: var(--font-mono); font-size: 12px; font-weight: 600; }
.stock-row.up .stock-price, .stock-row.up .stock-pct { color: var(--accent-red); }
.stock-row.down .stock-price, .stock-row.down .stock-pct { color: var(--accent-green); }
.remove-btn { background: none; border: none; color: var(--text-tertiary); font-size: 12px; cursor: pointer; padding: 2px 6px; border-radius: 3px; }
.remove-btn:hover { color: var(--accent-red); background: rgba(244,63,94,0.1); }

.alerts-section { background: var(--bg-secondary); border: 1px solid var(--border-color); border-radius: var(--radius-lg); padding: 14px; }
.alerts-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }
.section-title { font-size: 12px; font-weight: 600; color: var(--text-secondary); margin-bottom: 0; }
.add-alert-btn { padding: 3px 10px; background: transparent; border: 1px solid var(--border-color); border-radius: 3px; color: var(--text-secondary); font-size: 11px; cursor: pointer; }
.add-alert-btn:hover { color: var(--accent-cyan); border-color: rgba(77,159,255,0.3); }

.alert-form { padding: 10px; background: rgba(255,255,255,0.02); border-radius: var(--radius-sm); margin-bottom: 10px; }
.form-row { margin-bottom: 8px; }
.form-input { width: 100%; padding: 6px 10px; background: var(--bg-primary); border: 1px solid var(--border-color); border-radius: var(--radius-sm); color: var(--text-primary); font-size: 12px; }
.form-input:focus { outline: none; border-color: var(--accent-cyan); }
.form-btns { display: flex; gap: 8px; }
.btn-save { flex: 1; padding: 6px; background: linear-gradient(135deg, #4d9fff, #a78bfa); color: white; border: none; border-radius: var(--radius-sm); font-size: 12px; cursor: pointer; }
.btn-cancel { flex: 1; padding: 6px; background: transparent; border: 1px solid var(--border-color); border-radius: var(--radius-sm); color: var(--text-secondary); font-size: 12px; cursor: pointer; }

.alert-list { display: flex; flex-direction: column; gap: 4px; }
.alert-row { display: flex; justify-content: space-between; align-items: center; padding: 8px 10px; background: rgba(255,255,255,0.02); border-radius: var(--radius-sm); border-left: 3px solid var(--accent-orange); }
.alert-row.triggered { border-left-color: var(--accent-green); opacity: 0.7; }
.alert-info { display: flex; gap: 8px; align-items: center; }
.alert-symbol { font-family: var(--font-mono); font-size: 11px; color: var(--accent-cyan); }
.alert-type { font-size: 11px; color: var(--text-secondary); }
.alert-value { font-family: var(--font-mono); font-size: 11px; color: var(--text-primary); font-weight: 600; }
.alert-actions { display: flex; gap: 6px; align-items: center; }
.alert-triggered { font-size: 10px; color: var(--accent-green); }
.alert-del { background: none; border: none; color: var(--text-tertiary); font-size: 11px; cursor: pointer; }
.alert-del:hover { color: var(--accent-red); }

.empty-state { text-align: center; padding: 60px 20px; color: var(--text-tertiary); font-size: 13px; }
.empty-state-small { text-align: center; padding: 20px; color: var(--text-tertiary); font-size: 12px; }

@media (max-width: 768px) {
  .watchlist-page { padding: 10px; }
  .main-layout { grid-template-columns: 1fr; }
}
</style>
