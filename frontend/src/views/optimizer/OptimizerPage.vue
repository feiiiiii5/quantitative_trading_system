<template>
  <div class="optimizer-page">
    <div class="opt-body">
      <div class="opt-left">
        <div class="surface-panel">
          <div class="panel-header">
            <span class="panel-title">PARAMETER OPTIMIZATION</span>
            <button class="term-btn" @click="runOptimize" :disabled="!canOptimize || optimizing">
              {{ optimizing ? 'OPTIMIZING...' : 'RUN OPTIMIZATION' }}
            </button>
          </div>

          <div v-if="paramSpecs.length" class="param-form">
            <div v-for="spec in paramSpecs" :key="spec.name" class="param-row">
              <label class="param-label">{{ spec.label }}</label>
              <div class="param-inputs">
                <div class="pi-group">
                  <span class="pi-tag">MIN</span>
                  <input
                    v-model.number="params[spec.name].min"
                    class="pi-input"
                    type="number"
                    :step="spec.step || 1"
                  />
                </div>
                <div class="pi-group">
                  <span class="pi-tag">MAX</span>
                  <input
                    v-model.number="params[spec.name].max"
                    class="pi-input"
                    type="number"
                    :step="spec.step || 1"
                  />
                </div>
                <div class="pi-group">
                  <span class="pi-tag">STEP</span>
                  <input
                    v-model.number="params[spec.name].step"
                    class="pi-input"
                    type="number"
                    :step="spec.step || 1"
                  />
                </div>
              </div>
            </div>
          </div>
          <div v-else class="panel-empty">LOADING PARAMS<span class="blink-cursor">_</span></div>

          <div v-if="optResult" class="opt-result">
            <div class="result-header">BEST PARAMETERS</div>
            <div class="result-params">
              <div v-for="(val, key) in optResult.best_params" :key="String(key)" class="rp-item">
                <span class="rp-key mono">{{ key }}</span>
                <span class="rp-val mono">{{ typeof val === 'number' ? val.toFixed(4) : val }}</span>
              </div>
            </div>
            <div class="result-metrics">
              <div class="rm-cell">
                <span class="rm-label">SHARPE</span>
                <span class="rm-value mono">{{ safeToFixed(optResult.sharpe, 4) }}</span>
              </div>
              <div class="rm-cell">
                <span class="rm-label">RETURN</span>
                <span class="rm-value mono" :class="optResult.total_return >= 0 ? 'val-rise' : 'val-fall'">
                  {{ safeToFixed((optResult.total_return ?? 0) * 100, 2) }}%
                </span>
              </div>
              <div class="rm-cell">
                <span class="rm-label">MAX DD</span>
                <span class="rm-value mono val-fall">{{ safeToFixed((optResult.max_drawdown ?? 0) * 100, 2) }}%</span>
              </div>
              <div class="rm-cell">
                <span class="rm-label">WIN RATE</span>
                <span class="rm-value mono">{{ safeToFixed((optResult.win_rate ?? 0) * 100, 1) }}%</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div class="opt-right">
        <div class="surface-panel">
          <div class="panel-header">
            <span class="panel-title">STRESS TEST</span>
            <button class="term-btn" @click="runStressTest" :disabled="stressLoading">
              {{ stressLoading ? 'TESTING...' : 'RUN STRESS TEST' }}
            </button>
          </div>

          <div v-if="stressLoading" class="panel-empty">RUNNING STRESS TEST<span class="blink-cursor">_</span></div>
          <div v-else-if="stressResult" class="stress-grid">
            <div v-for="scenario in stressResult.scenarios" :key="scenario.name" class="stress-card">
              <div class="sc-name">{{ scenario.name }}</div>
              <div class="sc-desc">{{ scenario.description }}</div>
              <div class="sc-impact mono" :class="scenario.impact >= 0 ? 'val-rise' : 'val-fall'">
                {{ scenario.impact >= 0 ? '+' : '' }}{{ safeToFixed((scenario.impact ?? 0) * 100, 2) }}%
              </div>
            </div>
          </div>
          <div v-else class="panel-empty">CLICK RUN TO START STRESS TEST</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, reactive } from 'vue'
import { createLogger } from '@/composables/useLogger'
import { useRequestCancel } from '@/composables/useRequestCancel'
import { useLoadingState } from '@/composables/useLoadingState'
import { api } from '@/api'
import { safeToFixed } from '@/utils/format'

const log = createLogger('Optimizer')

interface ParamSpecItem {
  name: string
  label: string
  default: number
  range?: number
  step?: number
}

interface OptimizeResultData {
  best_params: Record<string, number>
  sharpe: number
  total_return: number
  max_drawdown: number
  win_rate: number
}

interface StressScenario {
  name: string
  description: string
  impact: number
}

interface StressResultData {
  scenarios: StressScenario[]
}

const paramSpecs = ref<ParamSpecItem[]>([])
const params = reactive<Record<string, { min: number; max: number; step: number }>>({})
const optResult = ref<OptimizeResultData | null>(null)
const stressResult = ref<StressResultData | null>(null)
const { cancelAll } = useRequestCancel()
const optLoader = useLoadingState()
const stressLoader = useLoadingState()
const optimizing = optLoader.loading
const stressLoading = stressLoader.loading

const strategyName = ref('dual_ma')
const symbol = ref('sh000300')

const canOptimize = computed(() => Object.keys(params).length > 0)

async function fetchParamSpecs() {
  const result = await optLoader.wrap(() => api.optimizer.paramSpecs(), '获取参数规格失败')
  if (result) paramSpecs.value = Object.values(result) as ParamSpecItem[]
}

async function runOptimize() {
  if (!canOptimize.value) return
  const result = await optLoader.wrap(
    () => api.optimizer.optimizeParams(strategyName.value, symbol.value),
    '优化运行失败',
  )
  optResult.value = result as OptimizeResultData | null
}

async function runStressTest() {
  const result = await stressLoader.wrap(
    () => api.optimizer.stressTest(symbol.value),
    '压力测试失败',
  )
  stressResult.value = result as StressResultData | null
}

onMounted(fetchParamSpecs)

onUnmounted(cancelAll)
</script>

<style scoped>
.optimizer-page {
  max-width: 1440px;
  margin: 0 auto;
}

.opt-body {
  display: flex;
  gap: var(--u4);
}

.opt-left { flex: 1; min-width: 0; }
.opt-right { width: 400px; flex-shrink: 0; }

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
  padding: 3px 12px;
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

.param-form {
  display: flex;
  flex-direction: column;
  gap: var(--u3);
  padding: var(--u4);
}

.param-row {
  display: flex;
  align-items: center;
  gap: var(--u3);
}

.param-label {
  width: 100px;
  font-size: var(--fs-xs);
  color: var(--text-secondary);
  font-family: var(--font-mono);
  text-transform: uppercase;
  letter-spacing: 0.04em;
  flex-shrink: 0;
}

.param-inputs {
  display: flex;
  gap: var(--u2);
  flex: 1;
}

.pi-group {
  display: flex;
  align-items: center;
  gap: var(--u1);
  flex: 1;
}

.pi-tag {
  font-size: var(--fs-3xs);
  color: var(--text-muted);
  font-family: var(--font-mono);
  letter-spacing: 0.04em;
  flex-shrink: 0;
}

.pi-input {
  width: 100%;
  padding: 3px 6px;
  background: var(--bg-plate);
  border: 1px solid var(--border-dim);
  border-radius: var(--r-md);
  color: var(--text-primary);
  font-size: var(--fs-xs);
  font-family: var(--font-mono);
  outline: none;
  transition: border-color var(--dur-fast) var(--ease-mechanical);
}

.pi-input:focus { border-color: var(--accent); }

.opt-result {
  border-top: 1px solid var(--border-hair);
  padding: var(--u4);
}

.result-header {
  font-size: var(--fs-xs);
  color: var(--accent);
  font-family: var(--font-mono);
  text-transform: uppercase;
  letter-spacing: 0.06em;
  font-weight: 600;
  margin-bottom: var(--u3);
}

.result-params {
  display: flex;
  flex-wrap: wrap;
  gap: var(--u2);
  margin-bottom: var(--u4);
}

.rp-item {
  display: flex;
  align-items: center;
  gap: var(--u2);
  padding: 2px 8px;
  background: var(--bg-plate);
  border-radius: var(--r-md);
}

.rp-key {
  font-size: var(--fs-3xs);
  color: var(--text-tertiary);
  text-transform: uppercase;
}

.rp-val {
  font-size: var(--fs-sm);
  color: var(--text-primary);
  font-weight: 600;
}

.result-metrics {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 1px;
  background: var(--border-hair);
}

.rm-cell {
  padding: var(--u3);
  background: var(--bg-surface);
  display: flex;
  flex-direction: column;
  gap: var(--u1);
}

.rm-label {
  font-size: var(--fs-3xs);
  color: var(--text-tertiary);
  font-family: var(--font-mono);
  text-transform: uppercase;
  letter-spacing: 0.06em;
}

.rm-value {
  font-size: var(--fs-lg);
  font-weight: 600;
  color: var(--text-primary);
}

.val-rise { color: var(--rise); }
.val-fall { color: var(--fall); }

.stress-grid {
  display: flex;
  flex-direction: column;
  gap: 1px;
  background: var(--border-hair);
}

.stress-card {
  padding: var(--u3) var(--u4);
  background: var(--bg-surface);
  display: flex;
  align-items: center;
  gap: var(--u3);
}

.sc-name {
  font-size: var(--fs-sm);
  font-weight: 600;
  color: var(--text-primary);
  min-width: 80px;
}

.sc-desc {
  font-size: var(--fs-xs);
  color: var(--text-tertiary);
  flex: 1;
}

.sc-impact {
  font-size: var(--fs-base);
  font-weight: 700;
  min-width: 80px;
  text-align: right;
}

@media (max-width: 900px) {
  .opt-body { flex-direction: column; }
  .opt-right { width: 100%; }
  .result-metrics { grid-template-columns: repeat(2, 1fr); }
}
</style>
