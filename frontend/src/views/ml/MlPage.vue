<template>
  <div class="ml-page">
    <div v-if="errorMsg" class="error-banner">
      <span class="error-icon">⚠</span>
      <span class="error-text">{{ errorMsg }}</span>
      <button class="error-dismiss" @click="errorMsg = ''">✕</button>
    </div>
    <div class="ml-body">
      <div class="ml-left">
        <div class="surface-panel">
          <div class="panel-header">
            <span class="panel-title">TRIPLE BARRIER LABELS</span>
            <button class="term-btn" @click="generateLabels" :disabled="!canGenLabels || generating">
              {{ generating ? 'GENERATING...' : 'GENERATE' }}
            </button>
          </div>
          <div class="ml-form">
            <div class="ml-row">
              <label class="ml-label">PRICES (comma-separated)</label>
              <textarea v-model="pricesText" class="ml-textarea" placeholder="100.5, 101.2, 99.8, ..." rows="3" />
            </div>
            <div class="ml-row-inline">
              <div class="ml-field">
                <label class="ml-label-sm">METHOD</label>
                <select v-model="labelMethod" class="ml-select">
                  <option value="triple_barrier">TRIPLE BARRIER</option>
                  <option value="fixed_horizon">FIXED HORIZON</option>
                </select>
              </div>
            </div>
          </div>
          <div v-if="labelResult" class="label-result">
            <div class="result-header">LABEL DISTRIBUTION</div>
            <div class="label-metrics">
              <div class="lm-cell">
                <span class="lm-label">TOTAL</span>
                <span class="lm-value mono">{{ labelResult.n_labels }}</span>
              </div>
              <div class="lm-cell">
                <span class="lm-label">PROFIT</span>
                <span class="lm-value mono val-rise">{{ labelResult.profit_count }}</span>
              </div>
              <div class="lm-cell">
                <span class="lm-label">LOSS</span>
                <span class="lm-value mono val-fall">{{ labelResult.loss_count }}</span>
              </div>
              <div class="lm-cell">
                <span class="lm-label">TIMEOUT</span>
                <span class="lm-value mono">{{ labelResult.timeout_count }}</span>
              </div>
            </div>
          </div>
        </div>

        <div class="surface-panel">
          <div class="panel-header">
            <span class="panel-title">DRIFT DETECTION</span>
            <button class="term-btn" @click="runDriftCheck" :disabled="!canDriftCheck || driftChecking">{{ driftChecking ? 'CHECKING...' : 'CHECK' }}</button>
          </div>
          <div class="drift-form">
            <div class="ml-row">
              <label class="ml-label">CURRENT FEATURES (JSON)</label>
              <textarea v-model="currentFeaturesText" class="ml-textarea" placeholder='{"f1": [0.1, 0.2, ...], "f2": [0.3, 0.4, ...]}' rows="2" />
            </div>
            <div class="ml-row">
              <label class="ml-label">REFERENCE FEATURES (JSON)</label>
              <textarea v-model="referenceFeaturesText" class="ml-textarea" placeholder='{"f1": [0.1, 0.2, ...], "f2": [0.3, 0.4, ...]}' rows="2" />
            </div>
          </div>
          <div v-if="driftChecking" class="drift-result">
            <div class="panel-empty">CHECKING DRIFT<span class="blink-cursor">_</span></div>
          </div>
          <div v-else-if="driftResult" class="drift-result">
            <div class="result-header">DRIFT REPORT</div>
            <div class="drift-summary">
              <div class="lm-cell">
                <span class="lm-label">DRIFT DETECTED</span>
                <span class="lm-value mono" :class="driftResult.drift_detected ? 'val-fall' : 'val-rise'">
                  {{ driftResult.drift_detected ? 'YES' : 'NO' }}
                </span>
              </div>
              <div class="lm-cell">
                <span class="lm-label">ALERT LEVEL</span>
                <span class="lm-value mono" :class="driftResult.alert_level === 'high' ? 'val-fall' : ''">{{ driftResult.alert_level }}</span>
              </div>
            </div>
            <div v-if="driftResult.drifted_features.length" class="drifted-features">
              <span class="df-label">DRIFTED FEATURES:</span>
              <span v-for="f in driftResult.drifted_features" :key="f" class="df-chip">{{ f }}</span>
            </div>
          </div>
        </div>
      </div>

      <div class="ml-right">
        <div class="surface-panel">
          <div class="panel-header">
            <span class="panel-title">META-LABELING</span>
            <button class="term-btn" @click="runMetaLabel" :disabled="!canMetaLabel || metaLabeling">RUN</button>
          </div>
          <div class="meta-form">
            <div class="ml-row">
              <label class="ml-label">PRIMARY SIGNALS (comma-separated)</label>
              <textarea v-model="primarySignalsText" class="ml-textarea" placeholder="1, -1, 1, 0, -1, ..." rows="2" />
            </div>
            <div class="ml-row">
              <label class="ml-label">ACTUAL RETURNS (comma-separated)</label>
              <textarea v-model="actualReturnsText" class="ml-textarea" placeholder="0.02, -0.01, 0.03, ..." rows="2" />
            </div>
            <div class="ml-row">
              <label class="ml-label">FEATURES (JSON)</label>
              <textarea v-model="metaFeaturesText" class="ml-textarea" placeholder='{"rsi": [50, 60, ...], "vol": [0.2, 0.3, ...]}' rows="3" />
            </div>
          </div>
          <div v-if="metaLabeling && !metaResult" class="meta-result">
            <div class="panel-empty">META-LABELING<span class="blink-cursor">_</span></div>
          </div>
          <div v-else-if="metaResult" class="meta-result">
            <div class="result-header">META-LABELING RESULTS</div>
            <div class="label-metrics">
              <div class="lm-cell">
                <span class="lm-label">SAMPLES</span>
                <span class="lm-value mono">{{ metaResult.n_samples }}</span>
              </div>
              <div class="lm-cell">
                <span class="lm-label">POSITIVE RATE</span>
                <span class="lm-value mono" :class="metaResult.positive_rate > 0.5 ? 'val-rise' : 'val-fall'">
                  {{ (metaResult.positive_rate * 100).toFixed(1) }}%
                </span>
              </div>
              <div class="lm-cell">
                <span class="lm-label">CV MEAN</span>
                <span class="lm-value mono">{{ metaResult.cv_mean.toFixed(4) }}</span>
              </div>
              <div class="lm-cell">
                <span class="lm-label">CV STD</span>
                <span class="lm-value mono">{{ metaResult.cv_std.toFixed(4) }}</span>
              </div>
            </div>
            <div v-if="Object.keys(metaResult.feature_importance).length" class="feat-imp">
              <div class="result-header">FEATURE IMPORTANCE</div>
              <div class="fi-bars">
                <div v-for="(val, key) in sortedImportance" :key="String(key)" class="fi-row">
                  <span class="fi-name mono">{{ key }}</span>
                  <div class="fi-bar-wrap">
                    <div class="fi-bar" :style="{ width: (val / maxImportance * 100) + '%' }" />
                  </div>
                  <span class="fi-val mono">{{ val.toFixed(4) }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { api } from '@/api'

const generating = ref(false)
const driftChecking = ref(false)
const errorMsg = ref('')
const metaLabeling = ref(false)
const labelMethod = ref('triple_barrier')
const pricesText = ref('')
const currentFeaturesText = ref('')
const referenceFeaturesText = ref('')
const primarySignalsText = ref('')
const actualReturnsText = ref('')
const metaFeaturesText = ref('')

const labelResult = ref<{ n_labels: number; labels: number[]; profit_count: number; loss_count: number; timeout_count: number } | null>(null)
const driftResult = ref<{ drift_detected: boolean; drifted_features: string[]; ks_statistics: Record<string, number>; alert_level: string } | null>(null)
const metaResult = ref<{ n_samples: number; positive_rate: number; cv_mean: number; cv_std: number; feature_importance: Record<string, number> } | null>(null)

const canGenLabels = computed(() => {
  const prices = parseNumbers(pricesText.value)
  return prices.length >= 10
})

const canDriftCheck = computed(() => {
  try {
    const cur = JSON.parse(currentFeaturesText.value)
    const ref = JSON.parse(referenceFeaturesText.value)
    return Object.keys(cur).length > 0 && Object.keys(ref).length > 0
  } catch {
    return false
  }
})

const canMetaLabel = computed(() => {
  const signals = parseNumbers(primarySignalsText.value)
  const returns = parseNumbers(actualReturnsText.value)
  try {
    const features = JSON.parse(metaFeaturesText.value)
    return signals.length >= 10 && returns.length >= 10 && Object.keys(features).length > 0
  } catch {
    return false
  }
})

const sortedImportance = computed(() => {
  if (!metaResult.value) return {} as Record<string, number>
  const entries = Object.entries(metaResult.value.feature_importance)
  entries.sort((a, b) => b[1] - a[1])
  return Object.fromEntries(entries) as Record<string, number>
})

const maxImportance = computed(() => {
  if (!metaResult.value) return 1
  const vals = Object.values(metaResult.value.feature_importance)
  return vals.length > 0 ? Math.max(...vals) : 1
})

function parseNumbers(text: string): number[] {
  return text.split(',').map(s => parseFloat(s.trim())).filter(n => !isNaN(n))
}

async function generateLabels(): Promise<void> {
  const prices = parseNumbers(pricesText.value)
  if (prices.length < 10) return
  generating.value = true
  errorMsg.value = ''
  try {
    labelResult.value = await api.ml.labels({
      prices,
      method: labelMethod.value,
    }) as typeof labelResult.value
  } catch (e: unknown) {
    labelResult.value = null
    errorMsg.value = e instanceof Error ? e.message : 'Label generation failed'
  } finally {
    generating.value = false
  }
}

async function runDriftCheck(): Promise<void> {
  errorMsg.value = ''
  driftChecking.value = true
  try {
    const current = JSON.parse(currentFeaturesText.value)
    const reference = JSON.parse(referenceFeaturesText.value)
    driftResult.value = await api.ml.driftCheck({
      current_features: current,
      reference_features: reference,
    }) as typeof driftResult.value
  } catch (e: unknown) {
    driftResult.value = null
    errorMsg.value = e instanceof Error ? e.message : 'Drift check failed'
  } finally {
    driftChecking.value = false
  }
}

async function runMetaLabel(): Promise<void> {
  const primarySignals = parseNumbers(primarySignalsText.value)
  const actualReturns = parseNumbers(actualReturnsText.value)
  errorMsg.value = ''
  try {
    const features = JSON.parse(metaFeaturesText.value)
    metaResult.value = await api.ml.metaLabel({
      primary_signals: primarySignals,
      actual_returns: actualReturns,
      features,
    }) as typeof metaResult.value
  } catch (e: unknown) {
    metaResult.value = null
    errorMsg.value = e instanceof Error ? e.message : 'Meta-labeling failed'
  }
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

.ml-page {
  padding: 20px;
  min-height: 100vh;
  background: var(--bg-void, #0a0e17);
  color: var(--text-primary, #e0e0e0);
}

.ml-body {
  display: grid;
  grid-template-columns: 400px 1fr;
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

.ml-form, .drift-form, .meta-form {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-bottom: 12px;
}

.ml-row {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.ml-row-inline {
  display: flex;
  gap: 10px;
}

.ml-field {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.ml-label {
  font-family: var(--font-mono, monospace);
  font-size: 9px;
  letter-spacing: 0.08em;
  color: var(--text-muted, rgba(255, 255, 255, 0.3));
}

.ml-label-sm {
  font-family: var(--font-mono, monospace);
  font-size: 8px;
  letter-spacing: 0.06em;
  color: var(--text-muted, rgba(255, 255, 255, 0.3));
}

.ml-textarea {
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

.ml-textarea:focus {
  outline: none;
  border-color: var(--accent, #2979ff);
}

.ml-select {
  font-family: var(--font-mono, monospace);
  font-size: 11px;
  background: rgba(0, 0, 0, 0.3);
  border: 1px solid var(--border-dim, rgba(255, 255, 255, 0.06));
  color: var(--text-primary, #e0e0e0);
  padding: 4px 8px;
  border-radius: 2px;
  width: 100%;
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

.label-metrics {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 8px;
}

.lm-cell {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 8px;
  background: rgba(0, 0, 0, 0.2);
  border: 1px solid var(--border-hair, rgba(255, 255, 255, 0.03));
}

.lm-label {
  font-family: var(--font-mono, monospace);
  font-size: 8px;
  letter-spacing: 0.1em;
  color: var(--text-muted, rgba(255, 255, 255, 0.3));
}

.lm-value {
  font-size: 14px;
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

.drift-summary {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 8px;
  margin-bottom: 8px;
}

.drifted-features {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 4px;
  margin-top: 8px;
}

.df-label {
  font-family: var(--font-mono, monospace);
  font-size: 9px;
  color: var(--text-muted, rgba(255, 255, 255, 0.3));
}

.df-chip {
  font-family: var(--font-mono, monospace);
  font-size: 9px;
  padding: 2px 6px;
  background: rgba(255, 82, 82, 0.15);
  border: 1px solid rgba(255, 82, 82, 0.3);
  color: var(--signal-red, #ff5252);
}

.feat-imp {
  margin-top: 12px;
}

.fi-bars {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.fi-row {
  display: grid;
  grid-template-columns: 80px 1fr 60px;
  gap: 6px;
  align-items: center;
}

.fi-name {
  font-size: 10px;
  color: var(--text-secondary, rgba(255, 255, 255, 0.6));
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.fi-bar-wrap {
  height: 8px;
  background: rgba(0, 0, 0, 0.3);
  border: 1px solid var(--border-hair, rgba(255, 255, 255, 0.03));
}

.fi-bar {
  height: 100%;
  background: var(--accent, #2979ff);
  transition: width 0.3s ease;
}

.fi-val {
  font-size: 10px;
  color: var(--text-secondary, rgba(255, 255, 255, 0.6));
  text-align: right;
}

@media (max-width: 900px) {
  .ml-body {
    grid-template-columns: 1fr;
  }
}
</style>
