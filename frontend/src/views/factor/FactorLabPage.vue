<template>
  <div class="factor-lab-page">
    <div v-if="errorMsg" class="error-banner">
      <span class="error-icon">⚠</span>
      <span class="error-text">{{ errorMsg }}</span>
      <button class="error-dismiss" @click="errorMsg = ''">✕</button>
    </div>
    <div class="flab-body">
      <div class="flab-left">
        <div class="surface-panel">
          <div class="panel-header">
            <span class="panel-title">FACTOR REGISTRY</span>
            <button class="term-btn" @click="loadRegistry" :disabled="loading">REFRESH</button>
          </div>
          <div v-if="loading" class="panel-empty">LOADING<span class="blink-cursor">_</span></div>
          <div v-else-if="registry" class="factor-list">
            <div class="fl-filter">
              <button
                v-for="cat in ['ALL', ...registry.categories]"
                :key="cat"
                class="filter-chip"
                :class="{ active: activeCategory === cat }"
                @click="activeCategory = cat"
              >{{ cat }}</button>
            </div>
            <div class="fl-rows">
              <div
                v-for="f in filteredFactors"
                :key="f.name"
                class="fl-row"
                :class="{ selected: selectedFactor === f.name }"
                @click="selectedFactor = f.name"
              >
                <span class="fl-name mono">{{ f.name }}</span>
                <span class="fl-cat">{{ f.category }}</span>
                <span class="fl-desc">{{ f.description }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div class="flab-right">
        <div class="surface-panel">
          <div class="panel-header">
            <span class="panel-title">IC ANALYSIS</span>
            <button class="term-btn" @click="runIcAnalysis" :disabled="!canRunIc || analyzing">RUN</button>
          </div>
          <div class="ic-form">
            <div class="ic-row">
              <label class="ic-label">FACTOR VALUES</label>
              <textarea v-model="factorValuesText" class="ic-textarea" placeholder="Comma-separated numbers, e.g. 0.1, -0.2, 0.3..." rows="2" />
            </div>
            <div class="ic-row">
              <label class="ic-label">FORWARD RETURNS</label>
              <textarea v-model="forwardReturnsText" class="ic-textarea" placeholder="Comma-separated numbers" rows="2" />
            </div>
            <div class="ic-row-inline">
              <div class="ic-field">
                <label class="ic-label-sm">MAX LAG</label>
                <input v-model.number="icParams.maxLag" class="ic-input" type="number" min="1" max="60" />
              </div>
              <div class="ic-field">
                <label class="ic-label-sm">QUINTILES</label>
                <input v-model.number="icParams.nQuintiles" class="ic-input" type="number" min="3" max="10" />
              </div>
            </div>
          </div>
          <div v-if="icResult" class="ic-result">
            <div class="result-header">IC RESULTS</div>
            <div class="result-metrics">
              <div class="rm-cell">
                <span class="rm-label">MEAN IC</span>
                <span class="rm-value mono" :class="icResult.mean_ic >= 0 ? 'val-rise' : 'val-fall'">{{ icResult.mean_ic.toFixed(6) }}</span>
              </div>
              <div class="rm-cell">
                <span class="rm-label">ICIR</span>
                <span class="rm-value mono">{{ icResult.icir.toFixed(6) }}</span>
              </div>
              <div class="rm-cell">
                <span class="rm-label">TURNOVER</span>
                <span class="rm-value mono">{{ icResult.turnover.toFixed(6) }}</span>
              </div>
              <div class="rm-cell">
                <span class="rm-label">LS RETURN</span>
                <span class="rm-value mono" :class="icResult.long_short_return >= 0 ? 'val-rise' : 'val-fall'">{{ (icResult.long_short_return * 100).toFixed(4) }}%</span>
              </div>
              <div class="rm-cell">
                <span class="rm-label">LS SHARPE</span>
                <span class="rm-value mono">{{ icResult.long_short_sharpe.toFixed(4) }}</span>
              </div>
              <div class="rm-cell">
                <span class="rm-label">MONOTONICITY</span>
                <span class="rm-value mono">{{ icResult.monotonicity.toFixed(4) }}</span>
              </div>
            </div>
            <div v-if="icResult.ic_decay.length" class="ic-decay">
              <div class="decay-header">IC DECAY</div>
              <div class="decay-bars">
                <div v-for="(v, i) in icResult.ic_decay" :key="i" class="decay-bar-wrap">
                  <div class="decay-bar" :style="{ height: Math.abs(v) * 200 + 'px', background: v >= 0 ? 'var(--signal-teal, #1de9b6)' : 'var(--signal-red, #ff5252)' }" />
                  <span class="decay-lag mono">{{ i }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div class="surface-panel">
          <div class="panel-header">
            <span class="panel-title">FACTOR NEUTRALIZATION</span>
            <button class="term-btn" @click="runNeutralize" :disabled="!canRunNeutralize">NEUTRALIZE</button>
          </div>
          <div class="neut-form">
            <div class="ic-row">
              <label class="ic-label">INDUSTRY LABELS</label>
              <input v-model="industryLabelsText" class="ic-input-wide" placeholder="Comma-separated, e.g. tech,fin,cons" />
            </div>
            <div class="ic-row">
              <label class="ic-label">MARKET CAP</label>
              <input v-model="marketCapText" class="ic-input-wide" placeholder="Comma-separated numbers" />
            </div>
          </div>
          <div v-if="neutResult" class="neut-result">
            <div class="result-header">NEUTRALIZED VALUES</div>
            <div class="neut-values mono">
              {{ neutResult.neutralized_values.map((v: number | null) => v !== null ? v.toFixed(4) : 'N/A').join(', ') }}
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { api } from '@/api'

interface FactorDef {
  name: string
  category: string
  description: string
}

interface IcResult {
  factor_name: string
  mean_ic: number
  icir: number
  ic_decay: number[]
  turnover: number
  long_short_return: number
  long_short_sharpe: number
  monotonicity: number
}

interface NeutResult {
  neutralized_values: (number | null)[]
}

const loading = ref(false)
const analyzing = ref(false)
const errorMsg = ref('')
const registry = ref<{ factors: FactorDef[]; categories: string[] } | null>(null)
const activeCategory = ref('ALL')
const selectedFactor = ref('')

const factorValuesText = ref('')
const forwardReturnsText = ref('')
const icParams = ref({ maxLag: 20, nQuintiles: 5 })
const icResult = ref<IcResult | null>(null)

const industryLabelsText = ref('')
const marketCapText = ref('')
const neutResult = ref<NeutResult | null>(null)

const filteredFactors = computed(() => {
  if (!registry.value) return []
  if (activeCategory.value === 'ALL') return registry.value.factors
  return registry.value.factors.filter(f => f.category === activeCategory.value)
})

const canRunIc = computed(() => {
  const fv = factorValuesText.value.split(',').map(s => s.trim()).filter(Boolean)
  const fr = forwardReturnsText.value.split(',').map(s => s.trim()).filter(Boolean)
  return fv.length >= 10 && fr.length >= 10 && fv.length === fr.length
})

const canRunNeutralize = computed(() => {
  const fv = factorValuesText.value.split(',').map(s => s.trim()).filter(Boolean)
  const il = industryLabelsText.value.split(',').map(s => s.trim()).filter(Boolean)
  const mc = marketCapText.value.split(',').map(s => s.trim()).filter(Boolean)
  return fv.length >= 3 && il.length >= 3 && mc.length >= 3
})

async function loadRegistry(): Promise<void> {
  loading.value = true
  errorMsg.value = ''
  try {
    registry.value = await api.factor.registry()
  } catch (e: unknown) {
    registry.value = null
    errorMsg.value = e instanceof Error ? e.message : 'Failed to load factor registry'
  } finally {
    loading.value = false
  }
}

function parseNumbers(text: string): number[] {
  return text.split(',').map(s => parseFloat(s.trim())).filter(n => !isNaN(n))
}

async function runIcAnalysis(): Promise<void> {
  const factorValues = parseNumbers(factorValuesText.value)
  const forwardReturns = parseNumbers(forwardReturnsText.value)
  if (factorValues.length < 10 || forwardReturns.length < 10) return
  analyzing.value = true
  errorMsg.value = ''
  try {
    icResult.value = await api.factor.icAnalysis({
      factor_values: factorValues,
      forward_returns: forwardReturns,
      max_lag: icParams.value.maxLag,
      n_quintiles: icParams.value.nQuintiles,
    })
  } catch (e: unknown) {
    icResult.value = null
    errorMsg.value = e instanceof Error ? e.message : 'IC analysis failed'
  } finally {
    analyzing.value = false
  }
}

async function runNeutralize(): Promise<void> {
  const factorValues = parseNumbers(factorValuesText.value)
  const industryLabels = industryLabelsText.value.split(',').map(s => s.trim()).filter(Boolean)
  const marketCap = parseNumbers(marketCapText.value)
  if (factorValues.length < 3 || industryLabels.length < 3 || marketCap.length < 3) return
  try {
    neutResult.value = await api.factor.neutralize({
      factor_values: factorValues,
      industry_labels: industryLabels,
      market_cap: marketCap,
    })
  } catch (e: unknown) {
    neutResult.value = null
    errorMsg.value = e instanceof Error ? e.message : 'Neutralization failed'
  }
}

onMounted(() => {
  loadRegistry()
})
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

.factor-lab-page {
  padding: 20px;
  min-height: 100vh;
  background: var(--bg-void, #0a0e17);
  color: var(--text-primary, #e0e0e0);
}

.flab-body {
  display: grid;
  grid-template-columns: 320px 1fr;
  gap: 16px;
  max-width: 1400px;
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

.term-btn {
  font-family: var(--font-mono, monospace);
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.08em;
  padding: 4px 12px;
  border: 1px solid var(--accent, #2979ff);
  background: transparent;
  color: var(--accent, #2979ff);
  cursor: pointer;
  transition: all 0.15s ease;
}

.term-btn:hover:not(:disabled) {
  background: rgba(41, 121, 255, 0.15);
}

.term-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.panel-empty {
  font-family: var(--font-mono, monospace);
  font-size: 12px;
  color: var(--text-muted, rgba(255, 255, 255, 0.3));
  padding: 20px 0;
  text-align: center;
}

.blink-cursor {
  animation: blink 1s step-end infinite;
}

@keyframes blink {
  50% { opacity: 0; }
}

.fl-filter {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-bottom: 10px;
}

.filter-chip {
  font-family: var(--font-mono, monospace);
  font-size: 9px;
  letter-spacing: 0.06em;
  padding: 2px 8px;
  border: 1px solid var(--border-dim, rgba(255, 255, 255, 0.06));
  background: transparent;
  color: var(--text-tertiary, rgba(255, 255, 255, 0.38));
  cursor: pointer;
  transition: all 0.15s ease;
}

.filter-chip.active {
  border-color: var(--accent, #2979ff);
  color: var(--accent, #2979ff);
  background: rgba(41, 121, 255, 0.1);
}

.fl-rows {
  max-height: 500px;
  overflow-y: auto;
}

.fl-row {
  display: grid;
  grid-template-columns: 100px 70px 1fr;
  gap: 6px;
  padding: 6px 8px;
  border-bottom: 1px solid var(--border-hair, rgba(255, 255, 255, 0.03));
  cursor: pointer;
  transition: background 0.1s ease;
  font-size: 11px;
}

.fl-row:hover {
  background: rgba(41, 121, 255, 0.06);
}

.fl-row.selected {
  background: rgba(41, 121, 255, 0.1);
  border-left: 2px solid var(--accent, #2979ff);
}

.fl-name {
  color: var(--signal-teal, #1de9b6);
  font-size: 10px;
}

.fl-cat {
  color: var(--text-muted, rgba(255, 255, 255, 0.3));
  font-size: 9px;
  text-transform: uppercase;
}

.fl-desc {
  color: var(--text-secondary, rgba(255, 255, 255, 0.6));
  font-size: 10px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.ic-form {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-bottom: 16px;
}

.ic-row {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.ic-label {
  font-family: var(--font-mono, monospace);
  font-size: 9px;
  letter-spacing: 0.08em;
  color: var(--text-muted, rgba(255, 255, 255, 0.3));
}

.ic-textarea {
  font-family: var(--font-mono, monospace);
  font-size: 11px;
  background: rgba(0, 0, 0, 0.3);
  border: 1px solid var(--border-dim, rgba(255, 255, 255, 0.06));
  color: var(--text-primary, #e0e0e0);
  padding: 6px 8px;
  border-radius: 2px;
  resize: vertical;
  width: 100%;
}

.ic-textarea:focus {
  outline: none;
  border-color: var(--accent, #2979ff);
}

.ic-row-inline {
  display: flex;
  gap: 12px;
}

.ic-field {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.ic-label-sm {
  font-family: var(--font-mono, monospace);
  font-size: 9px;
  letter-spacing: 0.06em;
  color: var(--text-muted, rgba(255, 255, 255, 0.3));
}

.ic-input {
  font-family: var(--font-mono, monospace);
  font-size: 11px;
  background: rgba(0, 0, 0, 0.3);
  border: 1px solid var(--border-dim, rgba(255, 255, 255, 0.06));
  color: var(--text-primary, #e0e0e0);
  padding: 4px 8px;
  border-radius: 2px;
  width: 80px;
}

.ic-input:focus {
  outline: none;
  border-color: var(--accent, #2979ff);
}

.ic-input-wide {
  font-family: var(--font-mono, monospace);
  font-size: 11px;
  background: rgba(0, 0, 0, 0.3);
  border: 1px solid var(--border-dim, rgba(255, 255, 255, 0.06));
  color: var(--text-primary, #e0e0e0);
  padding: 4px 8px;
  border-radius: 2px;
  width: 100%;
}

.ic-input-wide:focus {
  outline: none;
  border-color: var(--accent, #2979ff);
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

.result-metrics {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
  margin-bottom: 12px;
}

.rm-cell {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 6px 8px;
  background: rgba(0, 0, 0, 0.2);
  border: 1px solid var(--border-hair, rgba(255, 255, 255, 0.03));
}

.rm-label {
  font-family: var(--font-mono, monospace);
  font-size: 8px;
  letter-spacing: 0.1em;
  color: var(--text-muted, rgba(255, 255, 255, 0.3));
}

.rm-value {
  font-size: 13px;
  font-weight: 600;
}

.val-rise {
  color: var(--signal-teal, #1de9b6);
}

.val-fall {
  color: var(--signal-red, #ff5252);
}

.mono {
  font-family: var(--font-mono, 'JetBrains Mono', monospace);
}

.ic-decay {
  margin-top: 12px;
}

.decay-header {
  font-family: var(--font-mono, monospace);
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.08em;
  color: var(--text-muted, rgba(255, 255, 255, 0.3));
  margin-bottom: 8px;
}

.decay-bars {
  display: flex;
  align-items: flex-end;
  gap: 2px;
  height: 60px;
  padding: 4px 0;
}

.decay-bar-wrap {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  flex: 1;
  max-width: 16px;
}

.decay-bar {
  width: 100%;
  min-height: 1px;
  border-radius: 1px;
}

.decay-lag {
  font-size: 7px;
  color: var(--text-muted, rgba(255, 255, 255, 0.2));
}

.neut-form {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 12px;
}

.neut-result {
  margin-top: 8px;
}

.neut-values {
  font-size: 11px;
  color: var(--signal-teal, #1de9b6);
  padding: 8px;
  background: rgba(0, 0, 0, 0.2);
  border: 1px solid var(--border-hair, rgba(255, 255, 255, 0.03));
  word-break: break-all;
}

@media (max-width: 900px) {
  .flab-body {
    grid-template-columns: 1fr;
  }
}
</style>
