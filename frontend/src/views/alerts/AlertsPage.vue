<template>
  <div class="alerts-page">
    <div class="surface-panel">
      <div class="panel-header">
        <span class="panel-title">ACTIVE ALERTS</span>
        <button class="term-btn" @click="showCreateForm = !showCreateForm">
          {{ showCreateForm ? 'CANCEL' : '+ NEW ALERT' }}
        </button>
      </div>

      <div v-if="showCreateForm" class="create-form">
        <div class="form-row">
          <label class="form-label">SYMBOL</label>
          <input v-model="newAlert.symbol" class="form-input" placeholder="600519" />
        </div>
        <div class="form-row">
          <label class="form-label">DIRECTION</label>
          <select v-model="newAlert.direction" class="form-select">
            <option value="above">ABOVE</option>
            <option value="below">BELOW</option>
          </select>
        </div>
        <div class="form-row">
          <label class="form-label">PRICE</label>
          <input v-model="newAlert.target_price" class="form-input" placeholder="0" type="number" />
        </div>
        <button class="term-btn" @click="createAlert" :disabled="!canCreate">CREATE ALERT</button>
      </div>

      <div v-if="loading" class="panel-empty">LOADING<span class="blink-cursor">_</span></div>
      <div v-else-if="alerts.length" class="alert-list">
        <div v-for="a in alerts" :key="a.id" class="alert-row">
          <div class="ar-left">
            <span class="code-text">{{ a.symbol }}</span>
            <span class="ar-type">{{ alertTypeLabel(a.alert_type) }}</span>
            <span class="ar-value mono">{{ a.value }}</span>
          </div>
          <div class="ar-right">
            <button
              class="toggle-btn"
              :class="a.enabled ? 'toggle-on' : 'toggle-off'"
              @click="toggleAlert(a)"
            >
              {{ a.enabled ? 'ON' : 'OFF' }}
            </button>
            <button class="del-btn" @click="deleteAlert(Number(a.id))">DEL</button>
          </div>
        </div>
      </div>
      <div v-else class="panel-empty">NO ALERTS</div>
    </div>

    <div class="surface-panel">
      <div class="panel-header"><span class="panel-title">ALERT HISTORY</span></div>
      <DataTable
        v-if="history.length"
        :columns="historyColumns"
        :rows="history as unknown as Record<string, unknown>[]"
        row-key="id"
      >
        <template #cell-symbol="{ value }">
          <span class="code-text">{{ value }}</span>
        </template>
        <template #cell-triggered_at="{ value }">
          <span class="mono">{{ formatTime(value as string) }}</span>
        </template>
      </DataTable>
      <div v-else class="panel-empty">NO HISTORY</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useQuery } from '@/composables/useQuery'
import { useMutation } from '@/composables/useMutation'
import { useApiError } from '@/composables/useApiError'
import { api } from '@/api'
import DataTable from '@/components/ui/DataTable.vue'
import type { ColumnDef } from '@/components/ui/DataTable.vue'
import type { PriceAlert } from '@/types'

const { handleApiError } = useApiError()

const {
  data: alertsData,
  isLoading: alertsLoading,
} = useQuery<PriceAlert[]>({
  key: 'alerts/list',
  fetcher: () => api.alerts.list(),
})

const {
  data: historyData,
} = useQuery<PriceAlert[]>({
  key: 'alerts/history',
  fetcher: async () => {
    try {
      return await api.alerts.history()
    } catch (err) {
      handleApiError(err, '获取历史提醒失败')
      return []
    }
  },
})

const createAlertMutation = useMutation<{ id: number }, { symbol: string; target_price: number; direction: string }>({
  mutationFn: (vars) => api.alerts.create(vars),
  invalidateKeys: ['alerts/list'],
  onError: (err) => handleApiError(err, '创建提醒失败'),
})

const deleteAlertMutation = useMutation<{ id: number }, number>({
  mutationFn: (id) => api.alerts.delete(id),
  invalidateKeys: ['alerts/list'],
  onError: (err) => handleApiError(err, '删除提醒失败'),
})

const alerts = computed(() => alertsData.value ?? [])
const history = computed(() => historyData.value ?? [])
const loading = alertsLoading

const showCreateForm = ref(false)

const newAlert = ref({
  symbol: '',
  direction: 'above' as 'above' | 'below',
  target_price: '',
})

const canCreate = computed(() => newAlert.value.symbol.trim() && newAlert.value.target_price)

const historyColumns: ColumnDef[] = [
  { key: 'symbol', label: 'CODE', width: '90px', code: true },
  { key: 'alert_type', label: 'TYPE', width: '120px' },
  { key: 'value', label: 'VALUE', align: 'right', width: '80px' },
  { key: 'trigger_time', label: 'TRIGGERED', width: '160px' },
]

function alertTypeLabel(type: string): string {
  const map: Record<string, string> = {
    price_above: 'PRICE >',
    price_below: 'PRICE <',
    change_pct_above: 'CHG% >',
    change_pct_below: 'CHG% <',
    volume_above: 'VOL >',
  }
  return map[type] || type.toUpperCase()
}

function formatTime(t: string): string {
  if (!t) return '-'
  return String(t).slice(0, 16).replace('T', ' ')
}

async function createAlert() {
  if (!canCreate.value) return
  const result = await createAlertMutation.mutate({
    symbol: newAlert.value.symbol.trim(),
    target_price: parseFloat(newAlert.value.target_price),
    direction: newAlert.value.direction,
  })
  if (result !== null) {
    newAlert.value = { symbol: '', direction: 'above', target_price: '' }
    showCreateForm.value = false
  }
}

async function toggleAlert(a: PriceAlert) {
  try {
    await api.alerts.update(Number(a.id), { enabled: !a.enabled })
    a.enabled = !a.enabled
  } catch (err) {
    handleApiError(err, '切换提醒状态失败')
  }
}

async function deleteAlert(id: string | number) {
  await deleteAlertMutation.mutate(Number(id))
}
</script>

<style scoped>
.alerts-page {
  max-width: 960px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: var(--u4);
}

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

.term-btn {
  padding: 3px 10px;
  background: var(--accent);
  color: #fff;
  border: none;
  border-radius: var(--r-md);
  font-size: var(--fs-xs);
  font-family: var(--font-mono);
  font-weight: 600;
  cursor: pointer;
  letter-spacing: 0.04em;
  transition: opacity var(--dur-fast) var(--ease-mechanical);
}

.term-btn:hover { opacity: 0.85; }
.term-btn:disabled { opacity: 0.4; cursor: not-allowed; }

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
  color: var(--accent);
  font-size: var(--fs-xs);
}

.create-form {
  padding: var(--u4);
  background: var(--bg-plate);
  margin: var(--u4);
  border-radius: var(--r-md);
  display: flex;
  flex-direction: column;
  gap: var(--u3);
}

.form-row {
  display: flex;
  align-items: center;
  gap: var(--u3);
}

.form-label {
  width: 80px;
  font-size: var(--fs-3xs);
  color: var(--text-tertiary);
  font-family: var(--font-mono);
  text-transform: uppercase;
  letter-spacing: 0.06em;
  flex-shrink: 0;
}

.form-input {
  flex: 1;
  padding: 4px 8px;
  background: var(--bg-surface);
  border: 1px solid var(--border-dim);
  border-radius: var(--r-md);
  color: var(--text-primary);
  font-size: var(--fs-sm);
  font-family: var(--font-mono);
  outline: none;
  transition: border-color var(--dur-fast) var(--ease-mechanical);
}

.form-input:focus { border-color: var(--accent); }

.form-select {
  flex: 1;
  padding: 4px 8px;
  background: var(--bg-surface);
  border: 1px solid var(--border-dim);
  border-radius: var(--r-md);
  color: var(--text-primary);
  font-size: var(--fs-sm);
  font-family: var(--font-mono);
  outline: none;
  cursor: pointer;
  transition: border-color var(--dur-fast) var(--ease-mechanical);
}

.form-select:focus { border-color: var(--accent); }

.alert-list { display: flex; flex-direction: column; }

.alert-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--u2) var(--u4);
  border-bottom: 1px solid var(--border-hair);
}

.alert-row:last-child { border-bottom: none; }

.ar-left {
  display: flex;
  align-items: center;
  gap: var(--u3);
}

.ar-type {
  font-size: var(--fs-xs);
  color: var(--text-tertiary);
  font-family: var(--font-mono);
}

.ar-value {
  font-size: var(--fs-sm);
  color: var(--text-primary);
}

.ar-right {
  display: flex;
  align-items: center;
  gap: var(--u2);
}

.toggle-btn {
  font-size: var(--fs-3xs);
  font-weight: 700;
  padding: 1px 8px;
  border-radius: var(--r-md);
  border: none;
  font-family: var(--font-mono);
  letter-spacing: 0.04em;
  cursor: pointer;
  transition: all var(--dur-fast) var(--ease-mechanical);
}

.toggle-on { background: var(--fall-bg); color: var(--fall); }
.toggle-off { background: var(--bg-plate); color: var(--text-muted); }

.del-btn {
  font-size: var(--fs-3xs);
  font-weight: 600;
  padding: 1px 6px;
  border-radius: var(--r-md);
  border: 1px solid var(--border-dim);
  background: transparent;
  color: var(--text-tertiary);
  cursor: pointer;
  font-family: var(--font-mono);
  letter-spacing: 0.04em;
  transition: all var(--dur-fast) var(--ease-mechanical);
}

.del-btn:hover { border-color: var(--rise); color: var(--rise); }
</style>
