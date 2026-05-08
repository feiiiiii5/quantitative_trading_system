<template>
  <Teleport to="body">
    <div class="search-overlay" @click.self="emit('close')">
      <div class="search-modal" role="dialog" aria-label="Search stocks" @keydown="onTrapKeydown">
        <div class="search-input-row">
          <svg class="search-icon" width="16" height="16" viewBox="0 0 16 16" fill="none">
            <circle cx="6.5" cy="6.5" r="5" stroke="currentColor" stroke-width="1.5" />
            <line x1="10.5" y1="10.5" x2="14" y2="14" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" />
          </svg>
          <input
            ref="inputRef"
            v-model="query"
            class="search-input"
            placeholder="搜索股票代码或名称..."
            aria-label="Search stocks by code or name"
          />
          <button class="search-esc" @click="emit('close')">ESC</button>
        </div>
        <div v-if="results.length" class="search-results" role="listbox" ref="resultsRef">
          <div
            v-for="item in results"
            :key="item.symbol"
            class="search-result-item"
            role="option"
            tabindex="0"
            @click="selectItem(item)"
          >
            <span class="result-code">{{ item.code }}</span>
            <span class="result-name">{{ item.name }}</span>
            <span class="result-market">
              <span class="market-dot" :style="{ background: marketColor(item.market) }" />
              <span class="market-label">{{ marketLabel(item.market) }}</span>
            </span>
          </div>
        </div>
        <div v-else-if="query.trim()" class="search-empty">NO RESULTS</div>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, watch, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '@/api'
import { useDebouncedSearch } from '@/composables/useDebouncedSearch'
import type { SearchItem } from '@/types'

const emit = defineEmits<{ close: [] }>()

const router = useRouter()
const inputRef = ref<HTMLInputElement | null>(null)
const resultsRef = ref<HTMLElement | null>(null)
const results = ref<SearchItem[]>([])

async function searchStocks(q: string): Promise<void> {
  try {
    results.value = await api.search.stocks(q)
  } catch {
    results.value = []
  }
}

const { query, loading } = useDebouncedSearch(searchStocks, 300)

watch(query, (q) => {
  if (!q.trim()) results.value = []
})

const marketMap: Record<string, { label: string; color: string }> = {
  A: { label: 'A股', color: 'var(--rise)' },
  HK: { label: '港股', color: 'var(--accent)' },
  US: { label: '美股', color: 'var(--purple)' },
}

function marketLabel(market: string): string {
  return marketMap[market]?.label ?? market
}

function marketColor(market: string): string {
  return marketMap[market]?.color ?? 'var(--text-tertiary)'
}

function selectItem(item: SearchItem) {
  emit('close')
  router.push(`/stock/${item.symbol}`)
}

function onTrapKeydown(e: KeyboardEvent) {
  if (e.key !== 'Tab') return

  const focusable = resultsRef.value
    ? Array.from(resultsRef.value.querySelectorAll<HTMLElement>('[role="option"]'))
    : []

  if (focusable.length === 0) return

  const first = focusable[0]
  const last = focusable[focusable.length - 1]

  if (e.shiftKey && document.activeElement === inputRef.value) {
    e.preventDefault()
    last.focus()
  } else if (!e.shiftKey && document.activeElement === last) {
    e.preventDefault()
    inputRef.value?.focus()
  }
}

function onKeydown(e: KeyboardEvent) {
  if (e.key === 'Escape') emit('close')
}

onMounted(() => {
  window.addEventListener('keydown', onKeydown)
  inputRef.value?.focus()
})

onUnmounted(() => {
  window.removeEventListener('keydown', onKeydown)
})
</script>

<style scoped>
.search-overlay {
  position: fixed;
  inset: 0;
  background: rgba(5, 5, 7, 0.85);
  backdrop-filter: blur(20px);
  z-index: 10000;
  display: flex;
  justify-content: center;
}

.search-modal {
  width: 640px;
  max-height: 520px;
  margin-top: 18vh;
  align-self: flex-start;
  background: var(--bg-surface);
  border: 1px solid var(--border-mid);
  border-radius: var(--r-md);
  overflow: hidden;
  box-shadow: var(--shadow-lg);
}

.search-input-row {
  display: flex;
  align-items: center;
  height: 52px;
  padding: 0 var(--u4);
  gap: var(--u3);
  border-bottom: 1px solid var(--border-mid);
}

.search-icon {
  color: var(--text-tertiary);
  flex-shrink: 0;
}

.search-input {
  flex: 1;
  height: 100%;
  background: transparent;
  border: none;
  outline: none;
  font-family: var(--font-mono);
  font-size: 16px;
  color: var(--text-primary);
}

.search-input::placeholder {
  color: var(--text-muted);
}

.search-esc {
  font-family: var(--font-mono);
  font-size: 10px;
  padding: 2px 6px;
  border-radius: var(--r-xs);
  background: var(--bg-overlay);
  color: var(--text-tertiary);
  border: 1px solid var(--border-hair);
  cursor: pointer;
  flex-shrink: 0;
}

.search-empty {
  font-family: var(--font-mono);
  color: var(--text-muted);
  padding: var(--u8) 0;
  text-align: center;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  font-size: var(--fs-sm);
}

.search-results {
  max-height: 352px;
  overflow-y: auto;
}

.search-result-item {
  display: flex;
  align-items: center;
  height: 44px;
  padding: 0 var(--u4);
  gap: var(--u4);
  cursor: pointer;
  position: relative;
  transition: background var(--dur-fast) var(--ease-mechanical);
}

.search-result-item::before {
  content: '';
  position: absolute;
  left: 0;
  top: 4px;
  bottom: 4px;
  width: 2px;
  background: var(--accent);
  opacity: 0;
  transition: opacity var(--dur-fast) var(--ease-mechanical);
}

.search-result-item:hover {
  background: rgba(255, 255, 255, 0.04);
}

.search-result-item:hover::before {
  opacity: 1;
}

.result-code {
  font-family: var(--font-mono);
  font-size: var(--fs-sm);
  font-weight: 500;
  color: var(--accent);
  min-width: 72px;
}

.result-name {
  flex: 1;
  font-size: var(--fs-sm);
  color: var(--text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.result-market {
  display: flex;
  align-items: center;
  gap: var(--u1);
  flex-shrink: 0;
}

.market-dot {
  width: 2px;
  height: 8px;
}

.market-label {
  font-family: var(--font-mono);
  font-size: var(--fs-xs);
  color: var(--text-tertiary);
}
</style>
