<template>
  <div class="watchlist-page">
    <div class="page-header">
      <h1 class="page-title">自选股</h1>
      <div class="header-actions">
        <div class="add-row">
          <input v-model="addSymbol" placeholder="输入代码或名称" class="add-input" @keyup.enter="addStock" />
          <button class="add-btn" @click="addStock">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M12 5v14M5 12h14"/></svg>
            添加
          </button>
        </div>
      </div>
    </div>

    <div class="main-layout">
      <div class="stocks-section card">
        <div class="list-toolbar">
          <span class="list-count mono">{{ stocks.length }} 只</span>
          <button class="refresh-btn" @click="refreshPrices" :class="{ spinning: refreshing }">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 2v6h-6M3 12a9 9 0 0115.36-6.36L21 8M3 22v-6h6M21 12a9 9 0 01-15.36 6.36L3 16"/></svg>
            刷新
          </button>
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
            <span class="stock-code mono">{{ stock.symbol }}</span>
            <span class="stock-name">{{ stock.name }}</span>
            <span class="stock-price mono">{{ (stock.price || 0).toFixed(2) }}</span>
            <span class="stock-pct mono">{{ stock.change_pct >= 0 ? '+' : '' }}{{ (stock.change_pct || 0).toFixed(2) }}%</span>
            <button class="remove-btn" @click.stop="removeStock(stock.symbol)">
              <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 6L6 18M6 6l12 12"/></svg>
            </button>
          </div>
        </div>
        <div v-else class="empty-state">
          <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="var(--text-tertiary)" stroke-width="1.5"><path d="M19 21l-7-5-7 5V5a2 2 0 012-2h10a2 2 0 012 2z"/></svg>
          <span>暂无自选股</span>
          <button class="btn-primary" @click="$router.push('/market')">去市场添加</button>
        </div>
      </div>

      <div class="alerts-section card">
        <div class="alerts-header">
          <h2 class="section-title">价格预警</h2>
          <button class="add-alert-btn" @click="showAlertForm = !showAlertForm">
            <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M12 5v14M5 12h14"/></svg>
            新增
          </button>
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
              <span class="alert-symbol mono">{{ alert.symbol }}</span>
              <span class="alert-type">{{ alertLabel(alert.alert_type) }}</span>
              <span class="alert-value mono">{{ alert.value }}</span>
            </div>
            <div class="alert-actions">
              <span v-if="alert.triggered" class="badge badge-warn">已触发</span>
              <button class="alert-del" @click="removeAlert(alert.id)">
                <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 6L6 18M6 6l12 12"/></svg>
              </button>
            </div>
          </div>
        </div>
        <div v-else class="empty-hint">暂无预警</div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue'
import { api } from '../api'
import { useToast } from '../composables/useToast'
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
const toast = useToast()

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
  } catch (e) {
    toast.warning(e instanceof Error ? e.message : '自选股加载失败')
  }
}

async function loadAlerts() {
  try {
    const data = await api.getAlerts()
    alerts.value = Array.isArray(data) ? data : []
  } catch (e) {
    toast.warning(e instanceof Error ? e.message : '预警加载失败')
  }
}

async function addStock() {
  const sym = addSymbol.value.trim()
  if (!sym) return
  try {
    await api.addToWatchlist(sym)
    addSymbol.value = ''
    await loadData()
  } catch (e) {
    toast.error(e instanceof Error ? e.message : '添加自选股失败')
  }
}

async function removeStock(symbol: string) {
  try {
    await api.removeFromWatchlist(symbol)
    await loadData()
  } catch (e) {
    toast.error(e instanceof Error ? e.message : '删除自选股失败')
  }
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
  } catch (e) {
    toast.error(e instanceof Error ? e.message : '添加预警失败')
  }
}

async function removeAlert(id: string) {
  try {
    await api.removeAlert(id)
    await loadAlerts()
  } catch (e) {
    toast.error(e instanceof Error ? e.message : '删除预警失败')
  }
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
.watchlist-page { padding: 14px 16px; max-width: 1200px; margin: 0 auto; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
.page-title { font-size: 18px; font-weight: 700; color: var(--text-primary); }

.add-row { display: flex; gap: 4px; }
.add-input {
  padding: 5px 10px; background: var(--bg-secondary); border: 1px solid var(--border-color);
  border-radius: var(--radius-sm); color: var(--text-primary); font-size: 12px;
  font-family: var(--font-mono); width: 150px;
}
.add-input:focus { outline: none; border-color: var(--accent-cyan); box-shadow: 0 0 0 2px var(--accent-cyan-dim); }
.add-btn {
  display: flex; align-items: center; gap: 4px;
  padding: 5px 12px; background: linear-gradient(135deg, var(--accent-blue), var(--accent-violet));
  color: white; border: none; border-radius: var(--radius-sm);
  font-size: 11px; font-weight: 600; cursor: pointer;
}

.main-layout { display: grid; grid-template-columns: 1fr 300px; gap: 10px; }

.stocks-section { padding: 12px; }
.list-toolbar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.list-count { font-size: 10px; color: var(--text-tertiary); }
.refresh-btn {
  display: flex; align-items: center; gap: 4px;
  padding: 3px 8px; background: transparent; border: 1px solid var(--border-color);
  border-radius: var(--radius-xs); color: var(--text-secondary); font-size: 10px; cursor: pointer;
}
.refresh-btn:hover { color: var(--text-primary); }
.refresh-btn.spinning svg { animation: spin 0.6s linear infinite; }
@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }

.stock-list { display: flex; flex-direction: column; gap: 1px; }
.stock-row {
  display: flex; align-items: center; gap: 8px; padding: 7px 8px;
  border-radius: var(--radius-sm); cursor: pointer; transition: background var(--transition-fast);
}
.stock-row:hover { background: var(--bg-hover); }
.drag-handle { color: var(--text-tertiary); cursor: grab; font-size: 12px; opacity: 0.5; }
.stock-code { font-size: 11px; color: var(--accent-cyan); width: 55px; }
.stock-name { font-size: 11px; color: var(--text-primary); flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.stock-price { font-size: 11px; font-weight: 600; color: var(--text-primary); width: 60px; text-align: right; }
.stock-pct { font-size: 11px; font-weight: 600; width: 60px; text-align: right; }
.stock-row.up .stock-price, .stock-row.up .stock-pct { color: var(--accent-red); }
.stock-row.down .stock-price, .stock-row.down .stock-pct { color: var(--accent-green); }
.remove-btn {
  display: flex; align-items: center; justify-content: center;
  width: 20px; height: 20px; border-radius: 3px;
  background: none; border: none; color: var(--text-tertiary);
  cursor: pointer; opacity: 0; transition: all var(--transition-fast);
}
.stock-row:hover .remove-btn { opacity: 1; }
.remove-btn:hover { color: var(--accent-red); background: var(--accent-red-dim); }

.alerts-section { padding: 12px; }
.alerts-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.section-title { margin-bottom: 0; }
.add-alert-btn {
  display: flex; align-items: center; gap: 3px;
  padding: 3px 8px; background: transparent; border: 1px solid var(--border-color);
  border-radius: var(--radius-xs); color: var(--text-secondary); font-size: 10px; cursor: pointer;
}
.add-alert-btn:hover { color: var(--accent-cyan); border-color: rgba(56,189,248,0.3); }

.alert-form {
  padding: 8px; background: var(--bg-hover); border-radius: var(--radius-sm);
  margin-bottom: 8px; border: 1px solid var(--border-subtle);
}
.form-row { margin-bottom: 6px; }
.form-input {
  width: 100%; padding: 5px 8px; background: var(--bg-elevated);
  border: 1px solid var(--border-subtle); border-radius: var(--radius-sm);
  color: var(--text-primary); font-size: 11px;
}
.form-input:focus { outline: none; border-color: var(--accent-cyan); }
.form-btns { display: flex; gap: 6px; }
.btn-save {
  flex: 1; padding: 5px; background: linear-gradient(135deg, var(--accent-blue), var(--accent-violet));
  color: white; border: none; border-radius: var(--radius-sm); font-size: 11px; cursor: pointer;
}
.btn-cancel {
  flex: 1; padding: 5px; background: transparent; border: 1px solid var(--border-color);
  border-radius: var(--radius-sm); color: var(--text-secondary); font-size: 11px; cursor: pointer;
}

.alert-list { display: flex; flex-direction: column; gap: 3px; }
.alert-row {
  display: flex; justify-content: space-between; align-items: center;
  padding: 6px 8px; background: var(--bg-hover); border-radius: var(--radius-sm);
  border-left: 2px solid var(--accent-amber);
}
.alert-row.triggered { border-left-color: var(--accent-green); opacity: 0.7; }
.alert-info { display: flex; gap: 6px; align-items: center; }
.alert-symbol { font-size: 10px; color: var(--accent-cyan); }
.alert-type { font-size: 10px; color: var(--text-secondary); }
.alert-value { font-size: 10px; color: var(--text-primary); font-weight: 600; }
.alert-actions { display: flex; gap: 4px; align-items: center; }
.alert-del {
  display: flex; align-items: center; justify-content: center;
  width: 18px; height: 18px; border-radius: 3px;
  background: none; border: none; color: var(--text-tertiary); cursor: pointer;
}
.alert-del:hover { color: var(--accent-red); background: var(--accent-red-dim); }

.empty-state {
  display: flex; flex-direction: column; align-items: center; gap: 8px;
  padding: 40px 20px; color: var(--text-tertiary); font-size: 12px;
}
.empty-hint { text-align: center; padding: 20px; color: var(--text-tertiary); font-size: 11px; }

@media (max-width: 768px) {
  .watchlist-page { padding: 10px; }
  .main-layout { grid-template-columns: 1fr; }
}
</style>
