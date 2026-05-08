<template>
  <div class="data-table-wrap">
    <div v-if="toolbar" class="dt-toolbar">
      <slot name="toolbar" />
      <button v-if="exportable" class="qc-btn qc-btn-ghost qc-btn-sm dt-export-btn" @click="handleExport">
        ↓ CSV
      </button>
    </div>
    <div class="dt-scroll">
      <table class="dt">
        <thead>
          <tr>
            <th
              v-for="col in columns"
              :key="col.key"
              :class="{ sorted: sortKey === col.key }"
              :style="{ width: col.width, textAlign: col.align || 'left' }"
              @click="col.sortable && toggleSort(col.key)"
            >
              {{ col.label }}
              <span v-if="col.sortable" class="sort-indicator">
                <span v-if="sortKey === col.key" class="sort-arrow">{{ sortOrder === 1 ? '▲' : '▼' }}</span>
                <span v-else class="sort-dormant">▲</span>
              </span>
            </th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="(row, i) in pagedRows"
            :key="rowKey ? String(row[rowKey]) : i"
            class="dt-row"
            :class="rowDirection(row)"
            @click="$emit('rowClick', row)"
          >
            <td
              v-for="col in columns"
              :key="col.key"
              :class="{
                'num-col': col.align === 'right',
                'code-col': col.code,
              }"
              :style="{ textAlign: col.align || 'left' }"
            >
              <slot :name="`cell-${col.key}`" :row="row" :value="row[col.key]">
                {{ col.format ? col.format(row[col.key]) : row[col.key] }}
              </slot>
            </td>
          </tr>
          <tr v-if="!pagedRows.length">
            <td :colspan="columns.length" class="dt-empty">NO DATA</td>
          </tr>
        </tbody>
      </table>
    </div>
    <div v-if="totalPages > 1" class="dt-pagination">
      <span class="pg-info">{{ (page - 1) * pageSize + 1 }}–{{ Math.min(page * pageSize, sortedRows.length) }} / {{ sortedRows.length }}</span>
      <button class="pg-btn" :disabled="page <= 1" @click="page = 1">«</button>
      <button class="pg-btn" :disabled="page <= 1" @click="page--">‹</button>
      <button
        v-for="p in visiblePages"
        :key="p"
        class="pg-btn"
        :class="{ active: p === page }"
        @click="page = p"
      >{{ p }}</button>
      <button class="pg-btn" :disabled="page >= totalPages" @click="page++">›</button>
      <button class="pg-btn" :disabled="page >= totalPages" @click="page = totalPages">»</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { exportToCsv } from '@/composables/useExport'

export interface ColumnDef {
  key: string
  label: string
  width?: string
  align?: 'left' | 'right' | 'center'
  sortable?: boolean
  code?: boolean
  format?: (v: unknown) => string
}

const props = withDefaults(defineProps<{
  columns: ColumnDef[]
  rows: Record<string, unknown>[]
  rowKey?: string
  toolbar?: boolean
  pageSize?: number
  exportable?: boolean
  exportFilename?: string
}>(), {
  toolbar: false,
  pageSize: 50,
  exportable: false,
  exportFilename: 'export',
})

defineEmits<{
  rowClick: [row: Record<string, unknown>]
}>()

const sortKey = ref('')
const sortOrder = ref(1)
const page = ref(1)

watch(() => props.rows, () => { page.value = 1 })

function toggleSort(key: string) {
  if (sortKey.value === key) {
    sortOrder.value = sortOrder.value === 1 ? -1 : 1
  } else {
    sortKey.value = key
    sortOrder.value = 1
  }
  page.value = 1
}

const sortedRows = computed(() => {
  if (!sortKey.value) return props.rows
  const key = sortKey.value
  const order = sortOrder.value
  return [...props.rows].sort((a, b) => {
    const va = a[key]
    const vb = b[key]
    if (typeof va === 'number' && typeof vb === 'number') {
      return (va - vb) * order
    }
    return String(va ?? '').localeCompare(String(vb ?? '')) * order
  })
})

const totalPages = computed(() => Math.max(1, Math.ceil(sortedRows.value.length / props.pageSize)))

const pagedRows = computed(() => {
  const start = (page.value - 1) * props.pageSize
  return sortedRows.value.slice(start, start + props.pageSize)
})

const visiblePages = computed(() => {
  const total = totalPages.value
  const current = page.value
  const delta = 2
  const pages: number[] = []
  for (let i = Math.max(1, current - delta); i <= Math.min(total, current + delta); i++) {
    pages.push(i)
  }
  return pages
})

function rowDirection(row: Record<string, unknown>): string {
  const changeVal = row['change'] ?? row['changePct'] ?? row['pct']
  if (changeVal == null) return ''
  const num = typeof changeVal === 'number' ? changeVal : parseFloat(String(changeVal))
  if (isNaN(num)) return ''
  if (num > 0) return 'row-rise'
  if (num < 0) return 'row-fall'
  return ''
}

function handleExport() {
  const exportColumns = props.columns.map(c => ({
    key: c.key,
    label: c.label,
    format: c.format,
  }))
  exportToCsv(`${props.exportFilename}.csv`, exportColumns, sortedRows.value)
}
</script>

<style scoped>
.data-table-wrap {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.dt-toolbar {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: var(--u2);
  padding: var(--u2) var(--u4);
  border-bottom: 1px solid var(--border-hair);
}

.dt-export-btn {
  margin-left: auto;
}

.dt-scroll {
  overflow: auto;
  flex: 1;
}

.dt {
  width: 100%;
  border-collapse: collapse;
  font-size: var(--fs-sm);
}

.dt thead {
  position: sticky;
  top: 0;
  z-index: 2;
}

.dt th {
  padding: var(--u2) var(--u4);
  text-align: left;
  background: var(--bg-void);
  font-family: var(--font-mono);
  font-size: 10px;
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: var(--text-tertiary);
  border-bottom: 1px solid var(--border-mid);
  user-select: none;
  white-space: nowrap;
}

.dt th.sorted {
  color: var(--text-secondary);
}

.sort-indicator {
  margin-left: 2px;
  font-size: 8px;
}

.sort-arrow {
  color: var(--accent);
}

.sort-dormant {
  opacity: 0;
  transition: opacity var(--dur-fast) var(--ease-mechanical);
}

.dt th:hover .sort-dormant {
  opacity: 0.3;
}

.dt td {
  padding: var(--u2) var(--u4);
  height: 36px;
  border-bottom: 1px solid var(--border-hair);
  white-space: nowrap;
  font-family: var(--font-sans);
  font-size: var(--fs-sm);
  color: var(--text-primary);
}

.dt-row {
  cursor: pointer;
  position: relative;
}

.dt-row:hover td {
  background: rgba(255,255,255,0.025);
}

.dt-row:hover::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 2px;
  background: var(--accent);
}

.dt-row.row-rise:hover::before {
  background: var(--rise);
}

.dt-row.row-fall:hover::before {
  background: var(--fall);
}

.dt-row:active td {
  animation: rowFlash 150ms var(--ease-mechanical);
}

@keyframes rowFlash {
  0% { background: rgba(255,255,255,0.08); }
  100% { background: transparent; }
}

.num-col {
  font-family: var(--font-mono);
  font-variant-numeric: tabular-nums;
  font-weight: 500;
}

.code-col {
  font-family: var(--font-mono);
  color: var(--accent);
  font-size: 11px;
}

.dt-empty {
  text-align: center;
  color: var(--text-muted);
  font-family: var(--font-mono);
  text-transform: uppercase;
  letter-spacing: 0.08em;
  padding: var(--u8) 0;
}

.dt-pagination {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: var(--u2) var(--u4);
  border-top: 1px solid var(--border-hair);
  font-family: var(--font-mono);
  font-size: 11px;
}

.pg-info {
  color: var(--text-tertiary);
  margin-right: auto;
}

.pg-btn {
  background: transparent;
  border: 1px solid var(--border-hair);
  color: var(--text-secondary);
  padding: 2px 8px;
  border-radius: 3px;
  cursor: pointer;
  font-family: var(--font-mono);
  font-size: 11px;
  min-width: 28px;
}

.pg-btn:hover:not(:disabled) {
  background: rgba(255,255,255,0.05);
}

.pg-btn:disabled {
  opacity: 0.3;
  cursor: default;
}

.pg-btn.active {
  background: var(--accent);
  color: var(--bg-void);
  border-color: var(--accent);
}
</style>
