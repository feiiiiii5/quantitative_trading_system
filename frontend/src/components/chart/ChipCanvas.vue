<template>
  <div ref="containerRef" class="chip-canvas" role="img" aria-label="Chip distribution chart">
    <canvas ref="canvasRef" @mousemove="onMouseMove" @mouseleave="onMouseLeave" />
    <div v-if="tooltip.visible" class="chip-tooltip" :style="{ left: tooltip.x + 'px', top: tooltip.y + 'px' }">
      持仓占比 {{ tooltip.pct }}%
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch, nextTick } from 'vue'
import { formatPrice } from '@/utils/format'
import type { ChipData } from '@/types'

const props = defineProps<{
  data: ChipData
}>()

const containerRef = ref<HTMLDivElement>()
const canvasRef = ref<HTMLCanvasElement>()

const tooltip = ref<{ visible: boolean; x: number; y: number; pct: string }>({
  visible: false,
  x: 0,
  y: 0,
  pct: '',
})

let resizeObserver: ResizeObserver | null = null
let animFrameId: number | null = null
let dpr = 1

const PADDING = { top: 24, right: 70, bottom: 30, left: 10 }

function getThemeColors(): { bg: string; profit: string; trapped: string; currentPrice: string; avgCost: string; axisLabel: string } {
  const style = getComputedStyle(document.documentElement)
  return {
    bg: style.getPropertyValue('--bg-base').trim() || '#080810',
    profit: style.getPropertyValue('--rise').trim() || '#ff3b3b',
    trapped: style.getPropertyValue('--fall').trim() || '#00e676',
    currentPrice: style.getPropertyValue('--warn').trim() || '#ffd600',
    avgCost: style.getPropertyValue('--purple').trim() || '#e040fb',
    axisLabel: style.getPropertyValue('--text-tertiary').trim() || '#9aa0a6',
  }
}

function draw(): void {
  const canvas = canvasRef.value
  const container = containerRef.value
  if (!canvas || !container || !props.data) return

  const rect = container.getBoundingClientRect()
  if (rect.width === 0 || rect.height === 0) return

  const colors = getThemeColors()
  dpr = window.devicePixelRatio || 1
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

  ctx.fillStyle = colors.bg
  ctx.fillRect(0, 0, w, h)

  const { prices, distribution, current_price, avg_cost } = props.data
  if (!prices.length || !distribution.length) return

  const plotW = w - PADDING.left - PADDING.right
  const plotH = h - PADDING.top - PADDING.bottom

  const minPrice = Math.min(...prices)
  const maxPrice = Math.max(...prices)
  const priceRange = maxPrice - minPrice || 1
  const maxDist = Math.max(...distribution) || 1

  const centerX = PADDING.left + plotW / 2

  for (let i = 0; i < prices.length; i++) {
    const price = prices[i]
    const dist = distribution[i]
    if (dist <= 0) continue

    const y = PADDING.top + plotH - ((price - minPrice) / priceRange) * plotH
    const barHalfWidth = (dist / maxDist) * (plotW / 2)
    const isProfitable = price >= current_price

    ctx.fillStyle = isProfitable ? colors.profit : colors.trapped
    ctx.fillRect(centerX - barHalfWidth, y - 1, barHalfWidth * 2, 2)
  }

  const priceToY = (p: number): number =>
    PADDING.top + plotH - ((p - minPrice) / priceRange) * plotH

  const currentY = priceToY(current_price)
  ctx.beginPath()
  ctx.setLineDash([6, 4])
  ctx.strokeStyle = colors.currentPrice
  ctx.lineWidth = 2
  ctx.moveTo(PADDING.left, currentY)
  ctx.lineTo(PADDING.left + plotW, currentY)
  ctx.stroke()
  ctx.setLineDash([])

  ctx.fillStyle = colors.currentPrice
  ctx.font = '10px JetBrains Mono, monospace'
  ctx.textAlign = 'left'
  ctx.textBaseline = 'middle'
  const cpLabel = `现价 ${formatPrice(current_price)}`
  const cpLabelW = ctx.measureText(cpLabel).width + 8
  ctx.fillRect(PADDING.left + plotW + 2, currentY - 8, cpLabelW, 16)
  ctx.fillStyle = '#000'
  ctx.fillText(cpLabel, PADDING.left + plotW + 6, currentY)

  const avgY = priceToY(avg_cost)
  ctx.beginPath()
  ctx.setLineDash([4, 3])
  ctx.strokeStyle = colors.avgCost
  ctx.lineWidth = 1.5
  ctx.moveTo(PADDING.left, avgY)
  ctx.lineTo(PADDING.left + plotW, avgY)
  ctx.stroke()
  ctx.setLineDash([])

  ctx.fillStyle = colors.avgCost
  const acLabel = `成本 ${formatPrice(avg_cost)}`
  const acLabelW = ctx.measureText(acLabel).width + 8
  ctx.fillRect(PADDING.left + plotW + 2, avgY - 8, acLabelW, 16)
  ctx.fillStyle = '#000'
  ctx.fillText(acLabel, PADDING.left + plotW + 6, avgY)

  const tickCount = Math.min(6, prices.length)
  const step = Math.max(1, Math.floor(prices.length / tickCount))
  ctx.fillStyle = colors.axisLabel
  ctx.font = '10px JetBrains Mono, monospace'
  ctx.textAlign = 'right'
  ctx.textBaseline = 'middle'
  for (let i = 0; i < prices.length; i += step) {
    const y = priceToY(prices[i])
    ctx.fillText(formatPrice(prices[i]), PADDING.left + plotW - 2, y)
  }
}

function onMouseMove(e: MouseEvent): void {
  const canvas = canvasRef.value
  const container = containerRef.value
  if (!canvas || !container || !props.data) return

  const rect = canvas.getBoundingClientRect()
  const mouseX = e.clientX - rect.left
  const mouseY = e.clientY - rect.top

  const { prices, distribution, current_price } = props.data
  const w = rect.width
  const h = rect.height
  const plotW = w - PADDING.left - PADDING.right
  const plotH = h - PADDING.top - PADDING.bottom
  const minPrice = Math.min(...prices)
  const maxPrice = Math.max(...prices)
  const priceRange = maxPrice - minPrice || 1
  const centerX = PADDING.left + plotW / 2
  const maxDist = Math.max(...distribution) || 1

  let found = false
  for (let i = 0; i < prices.length; i++) {
    const price = prices[i]
    const dist = distribution[i]
    if (dist <= 0) continue

    const y = PADDING.top + plotH - ((price - minPrice) / priceRange) * plotH
    const barHalfWidth = (dist / maxDist) * (plotW / 2)

    if (mouseX >= centerX - barHalfWidth && mouseX <= centerX + barHalfWidth &&
        mouseY >= y - 4 && mouseY <= y + 4) {
      const pct = (dist * 100).toFixed(2)
      tooltip.value = {
        visible: true,
        x: e.clientX - rect.left + 12,
        y: e.clientY - rect.top - 20,
        pct,
      }
      found = true
      break
    }
  }

  if (!found) {
    tooltip.value.visible = false
  }
}

function onMouseLeave(): void {
  tooltip.value.visible = false
}

function setupResize(): void {
  if (!containerRef.value) return
  resizeObserver = new ResizeObserver(() => {
    if (animFrameId) cancelAnimationFrame(animFrameId)
    animFrameId = requestAnimationFrame(draw)
  })
  resizeObserver.observe(containerRef.value)
}

watch(() => props.data, () => {
  nextTick(draw)
})

onMounted(() => {
  nextTick(() => {
    draw()
    setupResize()
  })
})

onUnmounted(() => {
  if (animFrameId) {
    cancelAnimationFrame(animFrameId)
    animFrameId = null
  }
  if (resizeObserver && containerRef.value) {
    resizeObserver.unobserve(containerRef.value)
    resizeObserver.disconnect()
  }
  resizeObserver = null
})
</script>

<style scoped>
.chip-canvas {
  position: relative;
  width: 100%;
  min-height: 300px;
}

.chip-canvas canvas {
  display: block;
  width: 100%;
  height: 100%;
}

.chip-tooltip {
  position: absolute;
  pointer-events: none;
  background: rgba(13, 13, 26, 0.92);
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: var(--r-xs);
  padding: 4px 8px;
  font-family: var(--font-mono);
  font-size: var(--fs-xs);
  color: var(--text-primary);
  white-space: nowrap;
  z-index: 10;
}
</style>
