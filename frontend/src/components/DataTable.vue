<template>
  <div class="data-table-wrapper">
    <div v-if="loading" class="table-skeleton">
      <div v-for="i in 5" :key="i" class="skeleton-row">
        <div v-for="c in columns.slice(0, 4)" :key="c.key" class="skeleton-cell" />
      </div>
    </div>
    <table v-else class="data-table" :class="{ striped, compact }">
      <thead>
        <tr>
          <th
            v-for="col in columns"
            :key="col.key"
            :style="{ width: col.width, textAlign: col.align || 'left' }"
            :class="{ sortable: col.sortable !== false, sorted: sortKey === col.key }"
            @click="handleSort(col)"
          >
            <span class="th-content">
              {{ col.label }}
              <span v-if="sortKey === col.key" class="sort-icon">{{ sortOrder === 1 ? '↑' : '↓' }}</span>
            </span>
          </th>
        </tr>
      </thead>
      <tbody>
        <tr v-if="sortedData.length === 0" class="empty-row">
          <td :colspan="columns.length" class="empty-cell">
            <div class="empty-state">
              <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="var(--text-tertiary)" stroke-width="1.5"><path d="M3 3h18v18H3z"/><path d="M9 9h6M9 13h4"/></svg>
              <span>暂无数据</span>
            </div>
          </td>
        </tr>
        <tr
          v-for="(row, idx) in sortedData"
          :key="rowKey ? row[rowKey] : idx"
          :class="{ clickable: !!rowClick, 'row-hover': true }"
          @click="rowClick && rowClick(row)"
        >
          <td
            v-for="col in columns"
            :key="col.key"
            :style="{ textAlign: col.align || 'left' }"
            :class="col.cellClass"
          >
            <slot :name="`cell-${col.key}`" :row="row" :value="row[col.key]">
              {{ col.format ? col.format(row[col.key], row) : row[col.key] }}
            </slot>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'

interface Column {
  key: string
  label: string
  width?: string
  align?: 'left' | 'center' | 'right'
  sortable?: boolean
  format?: (value: any, row: any) => string
  cellClass?: string
}

const props = withDefaults(defineProps<{
  columns: Column[]
  data: any[]
  loading?: boolean
  striped?: boolean
  compact?: boolean
  rowKey?: string
  rowClick?: (row: any) => void
  defaultSortKey?: string
  defaultSortOrder?: 1 | -1
}>(), {
  loading: false,
  striped: true,
  compact: false,
  defaultSortOrder: -1,
})

const sortKey = ref(props.defaultSortKey || '')
const sortOrder = ref(props.defaultSortOrder)

const sortedData = computed(() => {
  if (!sortKey.value) return props.data
  const key = sortKey.value
  const order = sortOrder.value
  return [...props.data].sort((a, b) => {
    const va = a[key]
    const vb = b[key]
    if (va == null && vb == null) return 0
    if (va == null) return order
    if (vb == null) return -order
    if (typeof va === 'number' && typeof vb === 'number') {
      return (va - vb) * order
    }
    return String(va).localeCompare(String(vb)) * order
  })
})

function handleSort(col: Column) {
  if (col.sortable === false) return
  if (sortKey.value === col.key) {
    sortOrder.value = sortOrder.value === 1 ? -1 : 1
  } else {
    sortKey.value = col.key
    sortOrder.value = -1
  }
}
</script>

<style scoped>
.data-table-wrapper {
  width: 100%;
  overflow-x: auto;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

.data-table th {
  padding: 10px 12px;
  font-weight: 500;
  color: var(--text-secondary);
  border-bottom: 1px solid var(--border-color);
  white-space: nowrap;
  user-select: none;
}

.data-table th.sortable {
  cursor: pointer;
}

.data-table th.sortable:hover {
  color: var(--text-primary);
}

.data-table th.sorted {
  color: var(--accent-blue);
}

.th-content {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.sort-icon {
  font-size: 11px;
  color: var(--accent-blue);
}

.data-table td {
  padding: 10px 12px;
  border-bottom: 1px solid var(--border-color);
  color: var(--text-primary);
}

.data-table.striped tbody tr:nth-child(even) {
  background: var(--bg-hover);
}

.data-table.compact th,
.data-table.compact td {
  padding: 6px 8px;
}

.data-table tbody tr.row-hover:hover {
  background: var(--bg-hover);
}

.data-table tbody tr.clickable {
  cursor: pointer;
}

.table-skeleton {
  padding: 8px;
}

.skeleton-row {
  display: flex;
  gap: 12px;
  margin-bottom: 8px;
}

.skeleton-cell {
  flex: 1;
  height: 16px;
  border-radius: 4px;
  background: linear-gradient(90deg, var(--bg-elevated) 25%, var(--bg-hover) 50%, var(--bg-elevated) 75%);
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
}

.empty-row .empty-cell {
  text-align: center;
  padding: 40px 12px;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  color: var(--text-tertiary);
  font-size: 13px;
}

@keyframes shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}
</style>
