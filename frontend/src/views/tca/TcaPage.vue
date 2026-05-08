<template>
  <div class="tca-page">
    <div v-if="errorMsg" class="error-banner">
      <span class="error-icon">⚠</span>
      <span class="error-text">{{ errorMsg }}</span>
      <button class="error-dismiss" @click="errorMsg = ''">✕</button>
    </div>
    <div class="tca-body">
      <div class="tca-left">
        <div class="surface-panel">
          <div class="panel-header">
            <span class="panel-title">TRADE COST ANALYZER</span>
          </div>
          <div class="tca-form">
            <div class="tca-row">
              <label class="tca-label">SYMBOL</label>
              <input v-model="trade.symbol" class="tca-input" placeholder="600000" />
            </div>
            <div class="tca-row-inline">
              <div class="tca-field">
                <label class="tca-label-sm">SIDE</label>
                <select v-model="trade.side" class="tca-select">
                  <option value="buy">BUY</option>
                  <option value="sell">SELL</option>
                </select>
              </div>
              <div class="tca-field">
                <label class="tca-label-sm">QUANTITY</label>
                <input v-model.number="trade.quantity" class="tca-input-sm" type="number" min="1" />
              </div>
            </div>
            <div class="tca-row-inline">
              <div class="tca-field">
                <label class="tca-label-sm">DECISION PX</label>
                <input v-model.number="trade.decision_price" class="tca-input-sm" type="number" step="0.01" />
              </div>
              <div class="tca-field">
                <label class="tca-label-sm">ARRIVAL PX</label>
                <input v-model.number="trade.arrival_price" class="tca-input-sm" type="number" step="0.01" />
              </div>
            </div>
            <div class="tca-row-inline">
              <div class="tca-field">
                <label class="tca-label-sm">EXEC PX</label>
                <input v-model.number="trade.execution_price" class="tca-input-sm" type="number" step="0.01" />
              </div>
              <div class="tca-field">
                <label class="tca-label-sm">VWAP</label>
                <input v-model.number="trade.vwap_benchmark" class="tca-input-sm" type="number" step="0.01" />
              </div>
            </div>
            <div class="tca-row-inline">
              <div class="tca-field">
                <label class="tca-label-sm">TWAP</label>
                <input v-model.number="trade.twap_benchmark" class="tca-input-sm" type="number" step="0.01" />
              </div>
              <div class="tca-field">
                <label class="tca-label-sm">STRATEGY</label>
                <input v-model="trade.strategy_name" class="tca-input-sm" placeholder="default" />
              </div>
            </div>
            <button class="term-btn" @click="analyzeTrade" :disabled="!canAnalyze || analyzing">
              {{ analyzing ? 'ANALYZING...' : 'ANALYZE TRADE' }}
            </button>
          </div>
        </div>

        <div class="surface-panel">
          <div class="panel-header">
            <span class="panel-title">EXECUTION RECOMMEND</span>
          </div>
          <div class="rec-form">
            <div class="tca-row">
              <label class="tca-label">SYMBOL</label>
              <input v-model="recSymbol" class="tca-input" placeholder="600000" />
            </div>
            <button class="term-btn" @click="getRecommendation" :disabled="!recSymbol">
              GET RECOMMENDATION
            </button>
          </div>
          <div v-if="recommendation" class="rec-result">
            <div class="result-header">RECOMMENDED EXECUTION</div>
            <div class="rec-rows">
              <div class="rec-row">
                <span class="rec-key">ALGORITHM</span>
                <span class="rec-val mono">{{ recommendation.recommended_algorithm }}</span>
              </div>
              <div class="rec-row">
                <span class="rec-key">TIME WINDOW</span>
                <span class="rec-val mono">{{ recommendation.recommended_time_window }}</span>
              </div>
              <div class="rec-row">
                <span class="rec-key">SLICES</span>
                <span class="rec-val mono">{{ recommendation.recommended_slice_count }}</span>
              </div>
              <div class="rec-row">
                <span class="rec-key">EST COST (bps)</span>
                <span class="rec-val mono" :class="recommendation.estimated_cost_bps > 10 ? 'val-fall' : 'val-rise'">
                  {{ recommendation.estimated_cost_bps.toFixed(2) }}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div class="tca-right">
        <div v-if="analyzing" class="surface-panel">
          <div class="panel-empty">ANALYZING<span class="blink-cursor">_</span></div>
        </div>
        <div v-else-if="analysisResult" class="surface-panel">
          <div class="panel-header">
            <span class="panel-title">COST METRICS</span>
          </div>
          <div class="metrics-grid">
            <div v-for="(val, key) in analysisResult.cost_metrics" :key="String(key)" class="metric-cell">
              <span class="metric-label">{{ formatKey(String(key)) }}</span>
              <span class="metric-value mono" :class="metricClass(String(key), Number(val))">
                {{ formatMetric(String(key), val) }}
              </span>
            </div>
          </div>
        </div>

        <div v-else class="surface-panel">
          <div class="panel-empty">ENTER TRADE DETAILS & ANALYZE<span class="blink-cursor">_</span></div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { api } from '@/api'

const analyzing = ref(false)
const errorMsg = ref('')
const analysisResult = ref<Record<string, unknown> | null>(null)
const recommendation = ref<{ symbol: string; recommended_algorithm: string; recommended_time_window: string; recommended_slice_count: number; estimated_cost_bps: number } | null>(null)
const recSymbol = ref('')

const trade = ref({
  symbol: '',
  side: 'buy' as 'buy' | 'sell',
  quantity: 1000,
  decision_price: 0,
  arrival_price: 0,
  execution_price: 0,
  vwap_benchmark: 0,
  twap_benchmark: 0,
  strategy_name: '',
})

const canAnalyze = computed(() => {
  return trade.value.symbol && trade.value.execution_price > 0 && trade.value.quantity > 0
})

async function analyzeTrade(): Promise<void> {
  analyzing.value = true
  errorMsg.value = ''
  try {
    analysisResult.value = await api.tca.analyze({
      symbol: trade.value.symbol,
      side: trade.value.side,
      quantity: trade.value.quantity,
      decision_price: trade.value.decision_price,
      arrival_price: trade.value.arrival_price,
      execution_price: trade.value.execution_price,
      vwap_benchmark: trade.value.vwap_benchmark || undefined,
      twap_benchmark: trade.value.twap_benchmark || undefined,
      strategy_name: trade.value.strategy_name || undefined,
    }) as Record<string, unknown>
  } catch (e: unknown) {
    analysisResult.value = null
    errorMsg.value = e instanceof Error ? e.message : 'Analysis failed'
  } finally {
    analyzing.value = false
  }
}

async function getRecommendation(): Promise<void> {
  errorMsg.value = ''
  try {
    recommendation.value = await api.tca.recommend(recSymbol.value) as typeof recommendation.value
  } catch (e: unknown) {
    recommendation.value = null
    errorMsg.value = e instanceof Error ? e.message : 'Recommendation failed'
  }
}

function formatKey(key: string): string {
  return key.replace(/_/g, ' ').toUpperCase()
}

function formatMetric(key: string, val: unknown): string {
  const num = Number(val)
  if (isNaN(num)) return String(val)
  if (key.includes('bps') || key.includes('shortfall') || key.includes('slippage') || key.includes('impact') || key.includes('cost')) {
    return num.toFixed(4)
  }
  return num.toFixed(2)
}

function metricClass(key: string, val: number): string {
  if (key.includes('cost') || key.includes('impact') || key.includes('slippage') || key.includes('shortfall')) {
    return val > 0 ? 'val-fall' : 'val-rise'
  }
  return ''
}
</script>

<style scoped>
.error-banner {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  margin-bottom: 12px;
  background: rgba(255, 82, 82, 0.12);
  border: 1px solid rgba(255, 82, 82, 0.3);
  border-radius: 4px;
  font-family: var(--font-mono, monospace);
  font-size: 11px;
  color: #ff5252;
}
.error-icon { flex-shrink: 0; }
.error-text { flex: 1; }
.error-dismiss {
  background: none;
  border: none;
  color: #ff5252;
  cursor: pointer;
  font-size: 12px;
  padding: 0 4px;
}

.tca-page {
  padding: 20px;
  min-height: 100vh;
  background: var(--bg-void, #0a0e17);
  color: var(--text-primary, #e0e0e0);
}

.tca-body {
  display: grid;
  grid-template-columns: 360px 1fr;
  gap: 16px;
  max-width: 1200px;
  margin: 0 auto;
}

.surface-panel {
  background: var(--bg-surface, rgba(255, 255, 255, 0.03));
  border: 1px solid var(--border-dim, rgba(255, 255, 255, 0.06));
  border-radius: 4px;
  padding: 16px;
  margin-bottom: 16px;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--border-hair, rgba(255, 255, 255, 0.04));
}

.panel-title {
  font-family: var(--font-mono, 'JetBrains Mono', monospace);
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.1em;
  color: var(--text-secondary, rgba(255, 255, 255, 0.7));
}

.panel-empty {
  font-family: var(--font-mono, monospace);
  font-size: 12px;
  color: var(--text-muted, rgba(255, 255, 255, 0.3));
  padding: 40px 0;
  text-align: center;
}

.blink-cursor {
  animation: blink 1s step-end infinite;
}

@keyframes blink {
  50% { opacity: 0; }
}

.tca-form {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.tca-row {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.tca-row-inline {
  display: flex;
  gap: 10px;
}

.tca-field {
  display: flex;
  flex-direction: column;
  gap: 2px;
  flex: 1;
}

.tca-label {
  font-family: var(--font-mono, monospace);
  font-size: 9px;
  letter-spacing: 0.08em;
  color: var(--text-muted, rgba(255, 255, 255, 0.3));
}

.tca-label-sm {
  font-family: var(--font-mono, monospace);
  font-size: 8px;
  letter-spacing: 0.06em;
  color: var(--text-muted, rgba(255, 255, 255, 0.3));
}

.tca-input {
  font-family: var(--font-mono, monospace);
  font-size: 12px;
  background: rgba(0, 0, 0, 0.3);
  border: 1px solid var(--border-dim, rgba(255, 255, 255, 0.06));
  color: var(--text-primary, #e0e0e0);
  padding: 6px 8px;
  border-radius: 2px;
  width: 100%;
}

.tca-input:focus {
  outline: none;
  border-color: var(--accent, #2979ff);
}

.tca-input-sm {
  font-family: var(--font-mono, monospace);
  font-size: 11px;
  background: rgba(0, 0, 0, 0.3);
  border: 1px solid var(--border-dim, rgba(255, 255, 255, 0.06));
  color: var(--text-primary, #e0e0e0);
  padding: 4px 8px;
  border-radius: 2px;
  width: 100%;
}

.tca-input-sm:focus {
  outline: none;
  border-color: var(--accent, #2979ff);
}

.tca-select {
  font-family: var(--font-mono, monospace);
  font-size: 11px;
  background: rgba(0, 0, 0, 0.3);
  border: 1px solid var(--border-dim, rgba(255, 255, 255, 0.06));
  color: var(--text-primary, #e0e0e0);
  padding: 4px 8px;
  border-radius: 2px;
  width: 100%;
}

.term-btn {
  font-family: var(--font-mono, monospace);
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.08em;
  padding: 6px 16px;
  border: 1px solid var(--accent, #2979ff);
  background: transparent;
  color: var(--accent, #2979ff);
  cursor: pointer;
  transition: all 0.15s ease;
  margin-top: 4px;
}

.term-btn:hover:not(:disabled) {
  background: rgba(41, 121, 255, 0.15);
}

.term-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.rec-form {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 12px;
}

.rec-result {
  margin-top: 8px;
}

.result-header {
  font-family: var(--font-mono, monospace);
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.1em;
  color: var(--signal-teal, #1de9b6);
  margin-bottom: 8px;
  padding-bottom: 4px;
  border-bottom: 1px solid var(--border-hair, rgba(255, 255, 255, 0.04));
}

.rec-rows {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.rec-row {
  display: flex;
  justify-content: space-between;
  padding: 4px 0;
  border-bottom: 1px solid var(--border-hair, rgba(255, 255, 255, 0.02));
}

.rec-key {
  font-family: var(--font-mono, monospace);
  font-size: 9px;
  letter-spacing: 0.06em;
  color: var(--text-muted, rgba(255, 255, 255, 0.3));
}

.rec-val {
  font-size: 11px;
  color: var(--text-primary, #e0e0e0);
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
}

.metric-cell {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 10px;
  background: rgba(0, 0, 0, 0.2);
  border: 1px solid var(--border-hair, rgba(255, 255, 255, 0.03));
}

.metric-label {
  font-family: var(--font-mono, monospace);
  font-size: 8px;
  letter-spacing: 0.08em;
  color: var(--text-muted, rgba(255, 255, 255, 0.3));
}

.metric-value {
  font-size: 16px;
  font-weight: 600;
}

.mono {
  font-family: var(--font-mono, 'JetBrains Mono', monospace);
}

.val-rise {
  color: var(--signal-teal, #1de9b6);
}

.val-fall {
  color: var(--signal-red, #ff5252);
}

@media (max-width: 900px) {
  .tca-body {
    grid-template-columns: 1fr;
  }
}
</style>
