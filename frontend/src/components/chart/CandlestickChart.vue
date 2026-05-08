<template>
  <div class="candlestick-chart" :style="{ height: height }">
    <div class="period-selector">
      <button
        v-for="p in PERIODS"
        :key="p.value"
        :class="['period-btn', { active: period === p.value }]"
        @click="$emit('update:period', p.value)"
      >{{ p.label }}</button>
    </div>
    <div class="indicator-selector">
      <button
        v-for="ind in INDICATORS"
        :key="ind.key"
        :class="['ind-badge', { active: activeIndicators.includes(ind.key) }]"
        @click="toggleIndicator(ind.key)"
      >{{ ind.label }}</button>
    </div>
    <BaseChart v-if="chartOption" :option="chartOption" :height="height" />
    <div v-else class="chart-empty">加载中...</div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import BaseChart from '@/components/chart/BaseChart.vue'
import { CANDLESTICK_STYLE, MA_COLORS, VOLUME_COLORS } from '@/lib/chartTheme'
import { api, createCancellableRequest } from '@/api'
import { useApiError } from '@/composables/useApiError'
import { formatPrice, formatVolume } from '@/utils/format'
import type { KlineBar, SignalItem } from '@/types'

const PERIODS = [
  { label: '1D', value: '1d' },
  { label: '5D', value: '5d' },
  { label: '3M', value: '3m' },
  { label: '1Y', value: '1y' },
  { label: '3Y', value: '3y' },
] as const

const INDICATORS = [
  { key: 'MA', label: 'MA' },
  { key: 'MACD', label: 'MACD' },
  { key: 'KDJ', label: 'KDJ' },
  { key: 'BOLL', label: 'BOLL' },
] as const

const props = withDefaults(defineProps<{
  symbol: string
  period?: string
  klineType?: string
  showVolume?: boolean
  showSignals?: boolean
  height?: string
}>(), {
  period: '1y',
  klineType: 'daily',
  showVolume: true,
  showSignals: true,
  height: '100%',
})

defineEmits<{
  'update:period': [value: string]
}>()

const klineData = ref<KlineBar[]>([])
const { handleApiError } = useApiError()
const signals = ref<SignalItem[]>([])
const indicators = ref<Record<string, unknown> | null>(null)
const activeIndicators = ref<string[]>(['MA'])

function toggleIndicator(key: string): void {
  const idx = activeIndicators.value.indexOf(key)
  if (idx >= 0) {
    activeIndicators.value.splice(idx, 1)
  } else {
    activeIndicators.value.push(key)
  }
}

function calcMA(data: number[], period: number): (number | null)[] {
  const result: (number | null)[] = []
  for (let i = 0; i < data.length; i++) {
    if (i < period - 1) { result.push(null); continue }
    let sum = 0
    for (let j = 0; j < period; j++) sum += data[i - j]
    result.push(parseFloat((sum / period).toFixed(2)))
  }
  return result
}

const chartOption = computed(() => {
  if (!klineData.value.length) return null
  const data = klineData.value
  const dates = data.map(d => d.date.slice(0, 10))
  const ohlc = data.map(d => [d.open, d.close, d.low, d.high])
  const volumes = data.map(d => d.volume)
  const closes = data.map(d => d.close)

  const showMA = activeIndicators.value.includes('MA')
  const showVOL = props.showVolume

  const ma5 = calcMA(closes, 5)
  const ma10 = calcMA(closes, 10)
  const ma20 = calcMA(closes, 20)
  const ma60 = calcMA(closes, 60)

  const buyMarkers: Record<string, unknown>[] = []
  const sellMarkers: Record<string, unknown>[] = []

  if (props.showSignals) {
    for (const s of signals.value) {
      if (!s.signals) continue
      const hasBuy = s.signals.some(sig => sig.signal === 'buy')
      const hasSell = s.signals.some(sig => sig.signal === 'sell')
      const idx = dates.indexOf((s.date || '').slice(0, 10))
      if (idx < 0) continue
      if (hasBuy) {
        buyMarkers.push({
          coord: [dates[idx], data[idx].low],
          symbol: 'triangle',
          symbolSize: 10,
          symbolRotate: 0,
          symbolOffset: [0, '50%'],
          itemStyle: { color: 'var(--rise)' },
          label: { show: false },
        })
      }
      if (hasSell) {
        sellMarkers.push({
          coord: [dates[idx], data[idx].high],
          symbol: 'triangle',
          symbolSize: 10,
          symbolRotate: 180,
          symbolOffset: [0, '-50%'],
          itemStyle: { color: 'var(--fall)' },
          label: { show: false },
        })
      }
    }
  }

  const lastClose = closes[closes.length - 1]

  const grids = showVOL
    ? [
        { left: 60, right: 60, top: 30, height: '55%' },
        { left: 60, right: 60, top: '72%', height: '18%' },
      ]
    : [
        { left: 60, right: 60, top: 30, height: '80%' },
      ]

  const xAxes = showVOL
    ? [
        { type: 'category', data: dates, gridIndex: 0, axisLabel: { show: false }, axisTick: { show: false } },
        { type: 'category', data: dates, gridIndex: 1, axisLabel: { fontSize: 10, color: '#555568' } },
      ]
    : [
        { type: 'category', data: dates, gridIndex: 0, axisLabel: { fontSize: 10, color: '#555568' } },
      ]

  const yAxes = showVOL
    ? [
        {
          type: 'value',
          gridIndex: 0,
          scale: true,
          splitLine: { lineStyle: { color: 'rgba(255,255,255,0.03)' } },
          axisLabel: { fontSize: 10, color: '#555568' },
          axisPointer: {
            label: {
              formatter: (params: { value: number }) => formatPrice(params.value),
              backgroundColor: 'rgba(41,121,255,0.8)',
              padding: [4, 8],
            },
          },
        },
        {
          type: 'value',
          gridIndex: 1,
          splitLine: { show: false },
          axisLabel: {
            fontSize: 10,
            color: '#555568',
            formatter: (v: number) => v >= 1e4 ? (v / 1e4).toFixed(0) + '万' : v.toFixed(0),
          },
        },
      ]
    : [
        {
          type: 'value',
          gridIndex: 0,
          scale: true,
          splitLine: { lineStyle: { color: 'rgba(255,255,255,0.03)' } },
          axisLabel: { fontSize: 10, color: '#555568' },
          axisPointer: {
            label: {
              formatter: (params: { value: number }) => formatPrice(params.value),
              backgroundColor: 'rgba(41,121,255,0.8)',
              padding: [4, 8],
            },
          },
        },
      ]

  const series: Record<string, unknown>[] = [
    {
      name: 'K线',
      type: 'candlestick',
      data: ohlc,
      xAxisIndex: 0,
      yAxisIndex: 0,
      itemStyle: CANDLESTICK_STYLE,
      markPoint: {
        data: [...buyMarkers, ...sellMarkers],
        animation: false,
      },
      markLine: {
        silent: true,
        symbol: 'none',
        data: [
          {
            yAxis: lastClose,
            lineStyle: { color: 'rgba(255,255,255,0.2)', width: 0.5, type: 'solid' },
            label: {
              position: 'end',
              formatter: formatPrice(lastClose),
              fontSize: 10,
              fontFamily: 'JetBrains Mono',
              backgroundColor: 'rgba(41,121,255,0.8)',
              color: '#fff',
              padding: [2, 6],
              borderRadius: 2,
            },
          },
        ],
      },
    },
  ]

  if (showMA) {
    series.push(
      { name: 'MA5', type: 'line', data: ma5, xAxisIndex: 0, yAxisIndex: 0, smooth: true, showSymbol: false, lineStyle: { width: 1 }, itemStyle: { color: MA_COLORS.MA5 } },
      { name: 'MA10', type: 'line', data: ma10, xAxisIndex: 0, yAxisIndex: 0, smooth: true, showSymbol: false, lineStyle: { width: 1 }, itemStyle: { color: MA_COLORS.MA10 } },
      { name: 'MA20', type: 'line', data: ma20, xAxisIndex: 0, yAxisIndex: 0, smooth: true, showSymbol: false, lineStyle: { width: 1 }, itemStyle: { color: MA_COLORS.MA20 } },
      { name: 'MA60', type: 'line', data: ma60, xAxisIndex: 0, yAxisIndex: 0, smooth: true, showSymbol: false, lineStyle: { width: 1 }, itemStyle: { color: MA_COLORS.MA60 } },
    )
  }

  if (showVOL) {
    series.push({
      name: '成交量',
      type: 'bar',
      data: volumes,
      xAxisIndex: 1,
      yAxisIndex: 1,
      itemStyle: {
        color: (params: { dataIndex: number }) => {
          const d = data[params.dataIndex]
          return d.close >= d.open ? VOLUME_COLORS.rise : VOLUME_COLORS.fall
        },
      },
    })
  }

  const legendData = ['K线']
  if (showMA) legendData.push('MA5', 'MA10', 'MA20', 'MA60')
  if (showVOL) legendData.push('成交量')

  const result: Record<string, unknown> = {
    animation: false,
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'cross',
        crossStyle: { color: 'rgba(255,255,255,0.2)', width: 0.5 },
        lineStyle: { color: 'rgba(255,255,255,0.2)', width: 0.5 },
      },
      backgroundColor: 'rgba(13, 13, 26, 0.95)',
      borderColor: 'rgba(255,255,255,0.08)',
      textStyle: { color: '#f0f0f8', fontSize: 11, fontFamily: "'JetBrains Mono', monospace" },
      formatter: (params: Record<string, unknown>[]) => {
        if (!Array.isArray(params) || !params.length) return ''
        const date = (params[0] as Record<string, unknown>).axisValue as string
        let html = `<div style="margin-bottom:4px;font-size:11px;color:#9898b0">${date}</div>`
        for (const p of params) {
          const s = p as Record<string, unknown>
          const seriesName = s.seriesName as string
          const marker = s.marker as string
          if (seriesName === 'K线') {
            const val = s.data as number[]
            html += `<div style="display:flex;justify-content:space-between;gap:12px">`
            html += `<span>${marker}开 ${formatPrice(val[0])}</span>`
            html += `<span>收 ${formatPrice(val[1])}</span></div>`
            html += `<div style="display:flex;justify-content:space-between;gap:12px">`
            html += `<span>低 ${formatPrice(val[2])}</span>`
            html += `<span>高 ${formatPrice(val[3])}</span></div>`
          } else if (seriesName === '成交量') {
            html += `<div>${marker}${seriesName} ${formatVolume(s.data as number)}</div>`
          } else {
            const v = s.data as number | null
            if (v != null) html += `<div>${marker}${seriesName} ${formatPrice(v)}</div>`
          }
        }
        return html
      },
    },
    legend: {
      data: legendData,
      top: 0,
      left: 60,
      textStyle: { color: '#9898b0', fontSize: 10 },
      itemWidth: 14,
      itemHeight: 8,
    },
    grid: grids,
    xAxis: xAxes,
    yAxis: yAxes,
    dataZoom: [
      { type: 'inside', xAxisIndex: showVOL ? [0, 1] : [0], start: 70, end: 100 },
    ],
    series,
  }

  if (showVOL) {
    result.graphic = [{
      type: 'line',
      left: 60,
      right: 60,
      top: '70.5%',
      shape: { x1: 0, y1: 0, x2: 1, y2: 0 },
      style: { stroke: 'rgba(255,255,255,0.05)', lineWidth: 1 },
      silent: true,
    }]
  }

  return result
})

let _pendingRequest: ReturnType<typeof createCancellableRequest> | null = null

async function fetchData(): Promise<void> {
  if (!props.symbol) return
  if (_pendingRequest) _pendingRequest.cancel()
  const req = createCancellableRequest()
  _pendingRequest = req

  try {
    const [k, s, ind] = await Promise.allSettled([
      api.stock.history(props.symbol, props.period, props.klineType),
      api.stock.signals(props.symbol, props.period),
      api.stock.indicators(props.symbol, props.period, props.klineType),
    ])

    if (k.status === 'fulfilled') klineData.value = k.value
    if (s.status === 'fulfilled') signals.value = s.value?.signals ?? []
    if (ind.status === 'fulfilled') indicators.value = ind.value
  } catch (err) {
    handleApiError(err, '获取K线数据失败')
    klineData.value = []
  }
}

watch(() => [props.symbol, props.period, props.klineType], fetchData)

onMounted(fetchData)
</script>

<style scoped>
.candlestick-chart {
  position: relative;
  width: 100%;
  min-height: 300px;
}

.period-selector {
  position: absolute;
  top: 4px;
  left: 8px;
  z-index: 10;
  display: flex;
  gap: 2px;
}

.period-btn {
  background: transparent;
  border: none;
  color: var(--text-muted);
  font-family: var(--font-mono);
  font-size: 10px;
  padding: 2px 6px;
  cursor: pointer;
  border-radius: var(--r-xs);
  transition: all var(--dur-normal) var(--ease-smooth);
}

.period-btn:hover {
  color: var(--text-secondary);
  background: var(--bg-raised);
}

.period-btn.active {
  color: var(--accent);
  background: var(--accent-muted);
}

.indicator-selector {
  position: absolute;
  top: 4px;
  right: 8px;
  z-index: 10;
  display: flex;
  gap: 4px;
}

.ind-badge {
  background: var(--bg-plate);
  border: 1px solid var(--border-hair);
  color: var(--text-muted);
  font-family: var(--font-mono);
  font-size: 10px;
  padding: 1px 6px;
  cursor: pointer;
  border-radius: var(--r-xs);
  transition: all var(--dur-normal) var(--ease-smooth);
}

.ind-badge:hover {
  color: var(--text-secondary);
  border-color: var(--border-hover);
}

.ind-badge.active {
  color: var(--accent);
  background: var(--accent-muted);
  border-color: var(--accent);
}

.chart-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: var(--text-muted);
  font-size: var(--fs-sm);
}
</style>
