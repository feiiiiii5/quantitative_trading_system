import * as echarts from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart, BarChart, CandlestickChart, PieChart, ScatterChart, HeatmapChart, GaugeChart } from 'echarts/charts'
import {
  TitleComponent, TooltipComponent, GridComponent, LegendComponent,
  DataZoomComponent, VisualMapComponent, MarkLineComponent,
  MarkPointComponent, ToolboxComponent, GraphicComponent,
} from 'echarts/components'

echarts.use([
  CanvasRenderer, LineChart, BarChart, CandlestickChart, PieChart,
  ScatterChart, HeatmapChart, GaugeChart, TitleComponent, TooltipComponent,
  GridComponent, LegendComponent, DataZoomComponent, VisualMapComponent,
  MarkLineComponent, MarkPointComponent, ToolboxComponent, GraphicComponent,
])

export const chartTheme = {
  color: ['#3b82f6', '#22c55e', '#ef4444', '#f59e0b', '#8b5cf6', '#06b6d4', '#ec4899', '#14b8a6'],
  backgroundColor: 'transparent',
  textStyle: { color: '#7c8293', fontFamily: "'Inter', 'JetBrains Mono', sans-serif" },
  title: { textStyle: { color: '#e4e7ec', fontSize: 14, fontWeight: 500 } },
  legend: { textStyle: { color: '#7c8293', fontSize: 11 } },
  tooltip: {
    backgroundColor: 'rgba(15, 17, 23, 0.95)',
    borderColor: 'rgba(255,255,255,0.08)',
    textStyle: { color: '#e4e7ec', fontSize: 12 },
  },
  grid: { containLabel: true },
  categoryAxis: {
    axisLine: { lineStyle: { color: 'rgba(255,255,255,0.06)' } },
    axisTick: { lineStyle: { color: 'rgba(255,255,255,0.06)' } },
    axisLabel: { color: '#7c8293', fontSize: 10 },
    splitLine: { lineStyle: { color: 'rgba(255,255,255,0.03)' } },
  },
  valueAxis: {
    axisLine: { lineStyle: { color: 'rgba(255,255,255,0.06)' } },
    axisTick: { lineStyle: { color: 'rgba(255,255,255,0.06)' } },
    axisLabel: { color: '#7c8293', fontSize: 10 },
    splitLine: { lineStyle: { color: 'rgba(255,255,255,0.03)' } },
  },
}

export default echarts
