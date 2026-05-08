<template>
  <div class="chip-page">
    <div class="chip-top">
      <div class="chart-col">
        <div class="surface-panel chart-panel">
          <div class="panel-header">
            <span class="panel-title">{{ symbol ? `CHIP DIST — ${symbol}` : 'CHIP DISTRIBUTION' }}</span>
            <div class="symbol-input-bar">
              <input
                v-model="inputSymbol"
                placeholder="ENTER CODE"
                class="term-input"
                @keyup.enter="loadChip"
              />
              <button class="term-btn" @click="loadChip" :disabled="!inputSymbol.trim()">LOAD</button>
            </div>
          </div>
          <div v-if="loading" class="panel-empty">LOADING<span class="blink-cursor">_</span></div>
          <div v-else-if="chipData" ref="canvasContainerRef" class="canvas-wrap">
            <canvas ref="canvasRef" @mousemove="onCanvasMouseMove" @mouseleave="onCanvasMouseLeave" />
            <div v-if="canvasTooltip.visible" class="canvas-tooltip" :style="{ left: canvasTooltip.x + 'px', top: canvasTooltip.y + 'px' }">
              <span class="ct-price">¥{{ canvasTooltip.price }}</span>
              <span class="ct-pct">{{ canvasTooltip.pct }}%</span>
              <span class="ct-zone" :class="canvasTooltip.zone === 'PROFIT' ? 'zone-profit' : 'zone-loss'">{{ canvasTooltip.zone }}</span>
            </div>
          </div>
          <div v-else class="panel-empty">ENTER A STOCK CODE TO VIEW CHIP DISTRIBUTION</div>
        </div>
      </div>

      <div class="info-col">
        <div class="surface-panel">
          <div class="panel-header"><span class="panel-title">KEY METRICS</span></div>
          <div v-if="chipData" class="metrics-grid">
            <div class="metric-cell">
              <span class="mc-label">PROFIT RATIO</span>
              <span class="mc-value" :class="chipData.profit_ratio >= 0.5 ? 'val-profit' : 'val-loss'">
                {{ safeToFixed((chipData.profit_ratio ?? 0) * 100, 1) }}%
              </span>
            </div>
            <div class="metric-cell">
              <span class="mc-label">CONCENTRATION</span>
              <span class="mc-value">{{ safeToFixed((chipData.concentration ?? 0) * 100, 1) }}%</span>
            </div>
            <div class="metric-cell">
              <span class="mc-label">SUPPORT</span>
              <span class="mc-value val-support">{{ safeToFixed(chipData.support_price, 2) }}</span>
            </div>
            <div class="metric-cell">
              <span class="mc-label">RESISTANCE</span>
              <span class="mc-value val-resist">{{ safeToFixed(chipData.resistance_price, 2) }}</span>
            </div>
            <div class="metric-cell">
              <span class="mc-label">PEAK COST</span>
              <span class="mc-value">{{ safeToFixed(chipData.peak_price, 2) }}</span>
            </div>
            <div class="metric-cell">
              <span class="mc-label">AVG COST</span>
              <span class="mc-value val-avg-cost">{{ safeToFixed(chipData.avg_cost, 2) }}</span>
            </div>
          </div>
          <div v-else class="panel-empty">NO DATA</div>
        </div>

        <div v-if="chipData?.chip_bands?.length" class="surface-panel">
          <div class="panel-header"><span class="panel-title">CHIP BANDS</span></div>
          <div class="bands-list">
            <div v-for="(band, idx) in chipData.chip_bands" :key="idx" class="band-row">
              <span class="band-range">{{ band.range }}</span>
              <div class="band-bar-track">
                <div class="band-bar-fill" :style="{ width: (band.weight * 100).toFixed(1) + '%' }" />
              </div>
              <span class="band-weight">{{ safeToFixed(band.weight * 100, 1) }}%</span>
            </div>
          </div>
        </div>

        <div v-if="chipData?.fire" class="surface-panel">
          <div class="panel-header">
            <span class="panel-title">CHIP FIRE</span>
            <span class="fire-status" :class="chipData.fire.signal === 'bullish' ? 'fire-bull' : chipData.fire.signal === 'bearish' ? 'fire-bear' : 'fire-neutral'">
              {{ (chipData.fire.signal ?? chipData.fire.status ?? '—').toUpperCase() }}
            </span>
          </div>
          <div class="fire-grid">
            <div v-if="chipData.fire.short_concentration != null" class="fire-cell">
              <span class="fc-label">SHORT CONC</span>
              <span class="fc-value">{{ safeToFixed(chipData.fire.short_concentration * 100, 1) }}%</span>
            </div>
            <div v-if="chipData.fire.mid_concentration != null" class="fire-cell">
              <span class="fc-label">MID CONC</span>
              <span class="fc-value">{{ safeToFixed(chipData.fire.mid_concentration * 100, 1) }}%</span>
            </div>
            <div v-if="chipData.fire.long_concentration != null" class="fire-cell">
              <span class="fc-label">LONG CONC</span>
              <span class="fc-value">{{ safeToFixed(chipData.fire.long_concentration * 100, 1) }}%</span>
            </div>
            <div v-if="chipData.fire.avg_cost_short != null" class="fire-cell">
              <span class="fc-label">AVG COST S</span>
              <span class="fc-value">{{ safeToFixed(chipData.fire.avg_cost_short, 2) }}</span>
            </div>
            <div v-if="chipData.fire.avg_cost_mid != null" class="fire-cell">
              <span class="fc-label">AVG COST M</span>
              <span class="fc-value">{{ safeToFixed(chipData.fire.avg_cost_mid, 2) }}</span>
            </div>
            <div v-if="chipData.fire.avg_cost_long != null" class="fire-cell">
              <span class="fc-label">AVG COST L</span>
              <span class="fc-value">{{ safeToFixed(chipData.fire.avg_cost_long, 2) }}</span>
            </div>
          </div>
        </div>

        <div class="surface-panel">
          <div class="panel-header"><span class="panel-title">ANALYSIS</span></div>
          <div v-if="chipData" class="analysis-body">
            <div class="analysis-row">
              <span class="an-label">PROFIT RATIO</span>
              <span class="an-value" :class="chipData.profit_ratio >= 0.5 ? 'val-profit' : chipData.profit_ratio <= 0.2 ? 'val-loss' : ''">
                {{ chipData.profit_ratio >= 0.5 ? 'BULLISH — MAJORITY PROFITABLE' : chipData.profit_ratio <= 0.2 ? 'BEARISH — MAJORITY TRAPPED' : 'NEUTRAL — MIXED SIGNALS' }}
              </span>
            </div>
            <div class="analysis-row">
              <span class="an-label">CONCENTRATION</span>
              <span class="an-value" :class="chipData.concentration >= 0.6 ? 'val-profit' : ''">
                {{ chipData.concentration >= 0.6 ? 'HIGH — STRONG CONSENSUS' : chipData.concentration <= 0.3 ? 'LOW — DISPERSED' : 'MODERATE' }}
              </span>
            </div>
            <div class="analysis-row">
              <span class="an-label">SUPPORT / RESIST</span>
              <span class="an-value">{{ safeToFixed(chipData.support_price, 2) }} / {{ safeToFixed(chipData.resistance_price, 2) }}</span>
            </div>
          </div>
          <div v-else class="panel-empty">NO DATA</div>
        </div>
      </div>
    </div>

    <div class="surface-panel">
      <div class="panel-header"><span class="panel-title">POPULAR STOCKS</span></div>
      <div class="popular-list">
        <button
          v-for="s in popularSymbols"
          :key="s"
          class="popular-tag"
          :class="{ active: symbol === s }"
          @click="quickLoad(s)"
        >{{ s }}</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch, nextTick } from 'vue'
import { useRoute } from 'vue-router'
import { createLogger } from '@/composables/useLogger'
import { useRequestCancel } from '@/composables/useRequestCancel'
import { useApiError } from '@/composables/useApiError'
import { safeToFixed } from '@/utils/format'
import { api } from '@/api'
import type { ChipData } from '@/types'

const log = createLogger('Chip')
const { handleApiError } = useApiError()

const route = useRoute()
const props = defineProps<{ symbol?: string }>()

const inputSymbol = ref('')
const chipData = ref<ChipData | null>(null)
const loading = ref(false)
const symbol = ref('')
const { cancelAll } = useRequestCancel()

const popularSymbols = [
  '600519', '000858', '601318', '000001', '600036',
  '601012', '000333', '002594', '601888', '300750',
]

const canvasContainerRef = ref<HTMLDivElement>()
const canvasRef = ref<HTMLCanvasElement>()
const canvasTooltip = ref<{ visible: boolean; x: number; y: number; price: string; pct: string; zone: string }>({
  visible: false, x: 0, y: 0, price: '', pct: '', zone: '',
})

let resizeObserver: ResizeObserver | null = null
let animFrameId: number | null = null

const PAD = { top: 28, right: 72, bottom: 32, left: 72 }

function getThemeVar(name: string, fallback: string): string {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim() || fallback
}

function drawButterfly(): void {
  const canvas = canvasRef.value
  const container = canvasContainerRef.value
  if (!canvas || !container || !chipData.value) return

  const rect = container.getBoundingClientRect()
  if (rect.width === 0 || rect.height === 0) return

  const dpr = window.devicePixelRatio || 1
  const w = rect.width
  const h = rect.height
  canvas.width = w * dpr
  canvas.height = h * dpr
  canvas.style.width = w + 'px'
  canvas.style.height = h + 'px'

  const ctx = canvas.getContext('2d')
  if (!ctx) return
  ctx.scale(dpr, dpr)
  ctx.clearRect(0, 0, w, h)

  const { prices, distribution, current_price, avg_cost, support_price, resistance_price } = chipData.value
  if (!prices.length || !distribution.length) return

  const plotW = w - PAD.left - PAD.right
  const plotH = h - PAD.top - PAD.bottom
  const minPrice = Math.min(...prices)
  const maxPrice = Math.max(...prices)
  const priceRange = maxPrice - minPrice || 1
  const maxDist = Math.max(...distribution) || 1
  const centerX = PAD.left + plotW / 2

  const priceToY = (p: number): number => PAD.top + plotH - ((p - minPrice) / priceRange) * plotH

  const profitColor = getThemeVar('--fall', '#00e676')
  const lossColor = getThemeVar('--rise', '#ff3b3b')
  const warnColor = getThemeVar('--warn', '#ffd600')
  const purpleColor = getThemeVar('--purple', '#e040fb')
  const labelColor = getThemeVar('--text-tertiary', '#55556a')
  const gridColor = getThemeVar('--border-hair', 'rgba(255,255,255,0.06)')

  ctx.strokeStyle = gridColor
  ctx.lineWidth = 1
  for (let i = 0; i <= 4; i++) {
    const y = PAD.top + (plotH / 4) * i
    ctx.beginPath()
    ctx.moveTo(PAD.left, y)
    ctx.lineTo(PAD.left + plotW, y)
    ctx.stroke()
  }

  ctx.strokeStyle = gridColor
  ctx.lineWidth = 1
  ctx.beginPath()
  ctx.moveTo(centerX, PAD.top)
  ctx.lineTo(centerX, PAD.top + plotH)
  ctx.stroke()

  for (let i = 0; i < prices.length; i++) {
    const price = prices[i]
    const dist = distribution[i]
    if (dist <= 0) continue

    const y = priceToY(price)
    const barLen = (dist / maxDist) * (plotW / 2 - 4)
    const isProfit = price <= current_price

    if (isProfit) {
      const grad = ctx.createLinearGradient(centerX, y, centerX - barLen, y)
      grad.addColorStop(0, profitColor + '33')
      grad.addColorStop(1, profitColor + 'cc')
      ctx.fillStyle = grad
      ctx.fillRect(centerX - barLen, y - 1, barLen, 2)
    } else {
      const grad = ctx.createLinearGradient(centerX, y, centerX + barLen, y)
      grad.addColorStop(0, lossColor + '33')
      grad.addColorStop(1, lossColor + 'cc')
      ctx.fillStyle = grad
      ctx.fillRect(centerX, y - 1, barLen, 2)
    }
  }

  const drawHLine = (p: number, color: string, dash: number[], width: number, label: string, side: 'left' | 'right') => {
    const y = priceToY(p)
    ctx.beginPath()
    ctx.setLineDash(dash)
    ctx.strokeStyle = color
    ctx.lineWidth = width
    ctx.moveTo(PAD.left, y)
    ctx.lineTo(PAD.left + plotW, y)
    ctx.stroke()
    ctx.setLineDash([])

    ctx.font = '10px JetBrains Mono, monospace'
    const textW = ctx.measureText(label).width + 10
    if (side === 'right') {
      ctx.fillStyle = color
      ctx.fillRect(PAD.left + plotW + 2, y - 8, textW, 16)
      ctx.fillStyle = '#000'
      ctx.textAlign = 'left'
      ctx.textBaseline = 'middle'
      ctx.fillText(label, PAD.left + plotW + 7, y)
    } else {
      ctx.fillStyle = color
      ctx.fillRect(PAD.left - textW - 2, y - 8, textW, 16)
      ctx.fillStyle = '#000'
      ctx.textAlign = 'right'
      ctx.textBaseline = 'middle'
      ctx.fillText(label, PAD.left - 7, y)
    }
  }

  drawHLine(current_price, warnColor, [6, 4], 2, `CUR ${safeToFixed(current_price, 2)}`, 'right')
  drawHLine(avg_cost, purpleColor, [4, 3], 1.5, `AVG ${safeToFixed(avg_cost, 2)}`, 'left')

  const drawSRLine = (p: number, color: string, label: string) => {
    const y = priceToY(p)
    if (y < PAD.top || y > PAD.top + plotH) return
    ctx.beginPath()
    ctx.setLineDash([2, 4])
    ctx.strokeStyle = color + '88'
    ctx.lineWidth = 1
    ctx.moveTo(PAD.left, y)
    ctx.lineTo(PAD.left + plotW, y)
    ctx.stroke()
    ctx.setLineDash([])

    ctx.fillStyle = color + '44'
    ctx.font = '9px JetBrains Mono, monospace'
    ctx.textAlign = 'right'
    ctx.textBaseline = 'middle'
    ctx.fillText(label, PAD.left + plotW - 4, y - 6)
  }

  drawSRLine(support_price, profitColor, 'SUPPORT')
  drawSRLine(resistance_price, lossColor, 'RESIST')

  ctx.font = '9px JetBrains Mono, monospace'
  ctx.fillStyle = profitColor + '99'
  ctx.textAlign = 'center'
  ctx.textBaseline = 'top'
  ctx.fillText('PROFIT', centerX - plotW / 4, PAD.top + plotH + 8)

  ctx.fillStyle = lossColor + '99'
  ctx.fillText('TRAPPED', centerX + plotW / 4, PAD.top + plotH + 8)

  const tickCount = Math.min(6, prices.length)
  const step = Math.max(1, Math.floor(prices.length / tickCount))
  ctx.fillStyle = labelColor
  ctx.font = '9px JetBrains Mono, monospace'
  ctx.textAlign = 'center'
  ctx.textBaseline = 'top'
  for (let i = 0; i < prices.length; i += step) {
    const y = priceToY(prices[i])
    ctx.fillText(safeToFixed(prices[i], 2), centerX, y + 3)
  }
}

function onCanvasMouseMove(e: MouseEvent): void {
  const canvas = canvasRef.value
  const container = canvasContainerRef.value
  if (!canvas || !container || !chipData.value) return

  const rect = canvas.getBoundingClientRect()
  const mouseX = e.clientX - rect.left
  const mouseY = e.clientY - rect.top

  const { prices, distribution, current_price } = chipData.value
  const w = rect.width
  const h = rect.height
  const plotW = w - PAD.left - PAD.right
  const plotH = h - PAD.top - PAD.bottom
  const minPrice = Math.min(...prices)
  const maxPrice = Math.max(...prices)
  const priceRange = maxPrice - minPrice || 1
  const centerX = PAD.left + plotW / 2
  const maxDist = Math.max(...distribution) || 1

  let found = false
  for (let i = 0; i < prices.length; i++) {
    const price = prices[i]
    const dist = distribution[i]
    if (dist <= 0) continue

    const y = PAD.top + plotH - ((price - minPrice) / priceRange) * plotH
    const barLen = (dist / maxDist) * (plotW / 2 - 4)
    const isProfit = price <= current_price

    const left = isProfit ? centerX - barLen : centerX
    const right = isProfit ? centerX : centerX + barLen

    if (mouseX >= left && mouseX <= right && mouseY >= y - 6 && mouseY <= y + 6) {
      canvasTooltip.value = {
        visible: true,
        x: e.clientX - rect.left + 14,
        y: e.clientY - rect.top - 28,
        price: safeToFixed(price, 2),
        pct: (dist * 100).toFixed(2),
        zone: isProfit ? 'PROFIT' : 'LOSS',
      }
      found = true
      break
    }
  }

  if (!found) {
    canvasTooltip.value.visible = false
  }
}

function onCanvasMouseLeave(): void {
  canvasTooltip.value.visible = false
}

function setupResize(): void {
  if (resizeObserver) {
    if (canvasContainerRef.value) resizeObserver.unobserve(canvasContainerRef.value)
    resizeObserver.disconnect()
    resizeObserver = null
  }
  if (!canvasContainerRef.value) return
  resizeObserver = new ResizeObserver(() => {
    if (animFrameId) cancelAnimationFrame(animFrameId)
    animFrameId = requestAnimationFrame(drawButterfly)
  })
  resizeObserver.observe(canvasContainerRef.value)
}

async function loadChip() {
  const s = inputSymbol.value.trim()
  if (!s) return
  symbol.value = s
  loading.value = true
  try {
    chipData.value = await api.chip.distribution(s)
    await nextTick()
    drawButterfly()
    setupResize()
  } catch (err) {
    handleApiError(err, '加载筹码分布失败')
    chipData.value = null
  } finally {
    loading.value = false
  }
}

function quickLoad(s: string) {
  inputSymbol.value = s
  loadChip()
}

onMounted(() => {
  const routeSymbol = (route.params.symbol as string) || props.symbol
  if (routeSymbol) {
    inputSymbol.value = routeSymbol
    loadChip()
  }
})

watch(() => route.params.symbol, (newSymbol) => {
  if (newSymbol) {
    inputSymbol.value = newSymbol as string
    loadChip()
  }
})

watch(() => chipData.value, () => {
  nextTick(drawButterfly)
})

onUnmounted(() => {
  cancelAll()
  if (animFrameId) {
    cancelAnimationFrame(animFrameId)
    animFrameId = null
  }
  if (resizeObserver && canvasContainerRef.value) {
    resizeObserver.unobserve(canvasContainerRef.value)
    resizeObserver.disconnect()
  }
  resizeObserver = null
})
</script>

<style scoped>
.chip-page {
  max-width: 1440px;
  margin: 0 auto;
  display: grid;
  gap: var(--u4);
}

.chip-top {
  display: grid;
  grid-template-columns: 1fr 340px;
  gap: var(--u4);
}

.chart-col { min-width: 0; }

.info-col {
  display: grid;
  gap: var(--u4);
  align-content: start;
}

.chart-panel { display: flex; flex-direction: column; }

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

.symbol-input-bar {
  display: flex;
  align-items: center;
  gap: var(--u2);
}

.term-input {
  width: 120px;
  padding: 3px 8px;
  background: var(--bg-plate);
  border: 1px solid var(--border-dim);
  border-radius: var(--r-md);
  color: var(--text-primary);
  font-size: var(--fs-xs);
  font-family: var(--font-mono);
  font-variant-numeric: tabular-nums;
  outline: none;
  transition: border-color var(--dur-fast) var(--ease-mechanical);
}

.term-input:focus { border-color: var(--accent); }

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
  text-transform: uppercase;
  letter-spacing: 0.08em;
  transition: opacity var(--dur-fast) var(--ease-mechanical);
}

.term-btn:hover { opacity: 0.85; }
.term-btn:disabled { opacity: 0.4; cursor: not-allowed; }

.canvas-wrap {
  position: relative;
  width: 100%;
  min-height: 360px;
  flex: 1;
}

.canvas-wrap canvas {
  display: block;
  width: 100%;
  height: 100%;
  position: absolute;
  inset: 0;
}

.canvas-tooltip {
  position: absolute;
  pointer-events: none;
  background: rgba(13, 13, 26, 0.94);
  border: 1px solid var(--border-mid);
  border-radius: var(--r-md);
  padding: 4px 8px;
  font-family: var(--font-mono);
  font-size: var(--fs-xs);
  color: var(--text-primary);
  white-space: nowrap;
  z-index: 10;
  display: flex;
  gap: var(--u2);
  align-items: center;
}

.ct-price { color: var(--text-primary); font-variant-numeric: tabular-nums; }
.ct-pct { color: var(--text-secondary); font-variant-numeric: tabular-nums; }
.ct-zone { font-weight: 700; letter-spacing: 0.06em; }
.zone-profit { color: var(--fall); }
.zone-loss { color: var(--rise); }

.panel-empty {
  padding: var(--u10) var(--u4);
  text-align: center;
  color: var(--text-muted);
  font-size: var(--fs-xs);
  font-family: var(--font-mono);
  text-transform: uppercase;
  letter-spacing: 0.1em;
}

.blink-cursor { animation: blink 1s step-end infinite; }

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 1px;
  background: var(--border-hair);
}

.metric-cell {
  padding: var(--u3) var(--u4);
  background: var(--bg-surface);
  display: flex;
  flex-direction: column;
  gap: var(--u1);
}

.mc-label {
  font-size: var(--fs-3xs);
  color: var(--text-tertiary);
  font-family: var(--font-mono);
  text-transform: uppercase;
  letter-spacing: 0.1em;
}

.mc-value {
  font-size: var(--fs-lg);
  font-weight: 600;
  color: var(--text-primary);
  font-family: var(--font-mono);
  font-variant-numeric: tabular-nums;
}

.val-profit { color: var(--fall); }
.val-loss { color: var(--rise); }
.val-support { color: var(--teal); }
.val-resist { color: var(--warn); }
.val-avg-cost { color: var(--purple); }

.bands-list { display: grid; gap: 1px; }

.band-row {
  display: flex;
  align-items: center;
  gap: var(--u3);
  padding: var(--u2) var(--u4);
  border-bottom: 1px solid var(--border-hair);
}

.band-row:last-child { border-bottom: none; }

.band-range {
  font-size: var(--fs-xs);
  color: var(--text-secondary);
  font-family: var(--font-mono);
  font-variant-numeric: tabular-nums;
  min-width: 100px;
}

.band-bar-track {
  flex: 1;
  height: 3px;
  background: var(--bg-plate);
  border-radius: 2px;
  overflow: hidden;
}

.band-bar-fill {
  height: 100%;
  background: var(--accent);
  border-radius: 2px;
  transition: width var(--dur-normal) var(--ease-mechanical);
}

.band-weight {
  font-size: var(--fs-xs);
  color: var(--text-tertiary);
  font-family: var(--font-mono);
  font-variant-numeric: tabular-nums;
  min-width: 44px;
  text-align: right;
}

.fire-status {
  font-size: var(--fs-3xs);
  font-weight: 700;
  padding: 1px 6px;
  border-radius: var(--r-md);
  font-family: var(--font-mono);
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.fire-bull { background: var(--fall-bg); color: var(--fall); }
.fire-bear { background: var(--rise-bg); color: var(--rise); }
.fire-neutral { background: var(--accent-muted); color: var(--accent); }

.fire-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 1px;
  background: var(--border-hair);
}

.fire-cell {
  padding: var(--u2) var(--u3);
  background: var(--bg-surface);
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.fc-label {
  font-size: var(--fs-3xs);
  color: var(--text-tertiary);
  font-family: var(--font-mono);
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.fc-value {
  font-size: var(--fs-sm);
  color: var(--text-primary);
  font-family: var(--font-mono);
  font-variant-numeric: tabular-nums;
  font-weight: 500;
}

.analysis-body { display: grid; gap: var(--u3); padding: var(--u3) var(--u4); }

.analysis-row { display: grid; gap: var(--u1); }

.an-label {
  font-size: var(--fs-3xs);
  color: var(--text-tertiary);
  font-family: var(--font-mono);
  text-transform: uppercase;
  letter-spacing: 0.1em;
}

.an-value {
  font-size: var(--fs-sm);
  color: var(--text-secondary);
  font-weight: 500;
  font-family: var(--font-mono);
  font-variant-numeric: tabular-nums;
}

.popular-list {
  display: flex;
  flex-wrap: wrap;
  gap: var(--u2);
  padding: var(--u3) var(--u4);
}

.popular-tag {
  padding: 2px 10px;
  background: var(--bg-plate);
  border: 1px solid var(--border-hair);
  border-radius: var(--r-md);
  color: var(--text-secondary);
  font-size: var(--fs-xs);
  font-family: var(--font-mono);
  font-variant-numeric: tabular-nums;
  cursor: pointer;
  transition: border-color var(--dur-fast) var(--ease-mechanical),
              color var(--dur-fast) var(--ease-mechanical);
}

.popular-tag:hover { border-color: var(--accent); color: var(--accent); }
.popular-tag.active { background: var(--accent-muted); border-color: var(--accent); color: var(--accent); }

@media (max-width: 900px) {
  .chip-top { grid-template-columns: 1fr; }
}
</style>
