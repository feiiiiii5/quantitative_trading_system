<template>
  <div class="alert-manager">
    <div class="alert-header">
      <h3 class="alert-title">价格预警</h3>
      <button class="add-btn" @click="showAddForm = !showAddForm">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 5v14M5 12h14"/></svg>
        添加
      </button>
    </div>

    <div v-if="showAddForm" class="add-form">
      <div class="form-row">
        <label>股票代码</label>
        <input v-model="newAlert.symbol" class="form-input" placeholder="如 600519" />
      </div>
      <div class="form-row">
        <label>预警类型</label>
        <select v-model="newAlert.alert_type" class="form-input">
          <option value="price_above">价格高于</option>
          <option value="price_below">价格低于</option>
          <option value="pct_change_above">涨跌幅超</option>
        </select>
      </div>
      <div class="form-row">
        <label>目标值</label>
        <input v-model.number="newAlert.value" type="number" class="form-input" placeholder="输入价格或百分比" />
      </div>
      <div class="form-actions">
        <button class="btn-confirm" @click="addAlert">确认</button>
        <button class="btn-cancel" @click="showAddForm = false">取消</button>
      </div>
    </div>

    <div v-if="alerts.length === 0 && !showAddForm" class="empty-state">
      <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="var(--text-tertiary)" stroke-width="1.5"><path d="M18 8A6 6 0 006 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 01-3.46 0"/></svg>
      <span>暂无预警</span>
      <span class="empty-hint">设置价格预警，及时获取提醒</span>
    </div>

    <div v-else class="alert-list">
      <div v-for="alert in alerts" :key="alert.id" class="alert-item" :class="{ triggered: alert.triggered }">
        <div class="alert-info">
          <span class="alert-symbol">{{ alert.symbol }}</span>
          <span class="alert-type">{{ typeLabel(alert.alert_type) }}</span>
          <span class="alert-value" :class="alert.alert_type === 'pct_change_above' ? 'pct' : 'price'">
            {{ alert.alert_type === 'pct_change_above' ? `${alert.value}%` : `¥${alert.value}` }}
          </span>
        </div>
        <div class="alert-actions">
          <span v-if="alert.triggered" class="triggered-tag">已触发</span>
          <button class="remove-btn" @click="removeAlert(alert.id)">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 6L6 18M6 6l12 12"/></svg>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { api } from '../api'

interface Alert {
  id: string
  symbol: string
  alert_type: string
  value: number
  triggered: boolean
  created_at: string
}

const alerts = ref<Alert[]>([])
const showAddForm = ref(false)
const newAlert = ref({ symbol: '', alert_type: 'price_above', value: 0 })

let checkTimer: any = null

onMounted(() => {
  loadAlerts()
  checkTimer = setInterval(checkAlerts, 30000)
})

onUnmounted(() => {
  if (checkTimer) clearInterval(checkTimer)
})

async function loadAlerts() {
  try {
    const data = await api.getAlerts()
    alerts.value = Array.isArray(data) ? data : []
  } catch (e) { /* ignore */ }
}

async function addAlert() {
  if (!newAlert.value.symbol || newAlert.value.value == null) return
  try {
    const data = await api.addAlert(newAlert.value.symbol, newAlert.value.alert_type, newAlert.value.value)
    if (data) {
      alerts.value.push(data)
      showAddForm.value = false
      newAlert.value = { symbol: '', alert_type: 'price_above', value: 0 }
    }
  } catch (e) { /* ignore */ }
}

async function removeAlert(id: string) {
  try {
    await api.removeAlert(id)
    alerts.value = alerts.value.filter(a => a.id !== id)
  } catch (e) { /* ignore */ }
}

async function checkAlerts() {
  for (const alert of alerts.value) {
    if (alert.triggered) continue
    try {
      const rt = await api.getRealtime(alert.symbol)
      if (!rt) continue
      const price = rt.price || 0
      const pct = rt.change_pct || 0
      let triggered = false
      if (alert.alert_type === 'price_above' && price >= alert.value) triggered = true
      if (alert.alert_type === 'price_below' && price <= alert.value) triggered = true
      if (alert.alert_type === 'pct_change_above' && Math.abs(pct) >= alert.value) triggered = true
      if (triggered) {
        alert.triggered = true
        notifyUser(alert, price)
      }
    } catch (e) { /* ignore */ }
  }
}

function notifyUser(alert: Alert, currentPrice: number) {
  const msg = `${alert.symbol} ${typeLabel(alert.alert_type)} ${alert.alert_type === 'pct_change_above' ? `${alert.value}%` : `¥${alert.value}`}，当前 ¥${currentPrice.toFixed(2)}`
  if ('Notification' in window && Notification.permission === 'granted') {
    new Notification('QuantCore 价格预警', { body: msg })
  }
}

function typeLabel(type: string): string {
  const map: Record<string, string> = { price_above: '价格高于', price_below: '价格低于', pct_change_above: '涨跌幅超' }
  return map[type] || type
}
</script>

<style scoped>
.alert-manager {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md, 12px);
  padding: 16px;
}

.alert-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.alert-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0;
}

.add-btn {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  border: 1px solid var(--border-color);
  border-radius: 6px;
  background: transparent;
  color: var(--accent-blue);
  font-size: 12px;
  cursor: pointer;
}

.add-btn:hover {
  background: var(--bg-hover);
}

.add-form {
  padding: 12px;
  background: var(--bg-elevated);
  border-radius: 8px;
  margin-bottom: 12px;
}

.form-row {
  margin-bottom: 8px;
}

.form-row label {
  display: block;
  font-size: 12px;
  color: var(--text-secondary);
  margin-bottom: 4px;
}

.form-input {
  width: 100%;
  padding: 6px 10px;
  border: 1px solid var(--border-color);
  border-radius: 6px;
  background: var(--bg-secondary);
  color: var(--text-primary);
  font-size: 13px;
  box-sizing: border-box;
}

.form-actions {
  display: flex;
  gap: 8px;
  margin-top: 12px;
}

.btn-confirm {
  padding: 6px 16px;
  border: none;
  border-radius: 6px;
  background: var(--accent-blue);
  color: #fff;
  font-size: 12px;
  cursor: pointer;
}

.btn-cancel {
  padding: 6px 16px;
  border: 1px solid var(--border-color);
  border-radius: 6px;
  background: transparent;
  color: var(--text-secondary);
  font-size: 12px;
  cursor: pointer;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  padding: 24px;
  color: var(--text-tertiary);
  font-size: 13px;
}

.empty-hint {
  font-size: 11px;
}

.alert-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.alert-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 10px;
  border-radius: 6px;
  background: var(--bg-elevated);
}

.alert-item.triggered {
  border-left: 3px solid var(--accent-orange);
}

.alert-info {
  display: flex;
  align-items: center;
  gap: 8px;
}

.alert-symbol {
  font-weight: 600;
  color: var(--text-primary);
  font-size: 13px;
}

.alert-type {
  color: var(--text-secondary);
  font-size: 12px;
}

.alert-value {
  font-weight: 500;
  font-size: 13px;
}

.alert-value.price {
  color: var(--accent-blue);
}

.alert-value.pct {
  color: var(--accent-orange);
}

.alert-actions {
  display: flex;
  align-items: center;
  gap: 6px;
}

.triggered-tag {
  font-size: 11px;
  padding: 2px 6px;
  border-radius: 4px;
  background: rgba(251, 146, 60, 0.15);
  color: var(--accent-orange);
}

.remove-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border: none;
  border-radius: 4px;
  background: transparent;
  color: var(--text-tertiary);
  cursor: pointer;
}

.remove-btn:hover {
  background: var(--bg-hover);
  color: var(--accent-red);
}
</style>
