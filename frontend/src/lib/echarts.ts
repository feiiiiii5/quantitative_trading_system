import * as echarts from 'echarts/core'
import { CandlestickChart, LineChart, BarChart, ScatterChart, HeatmapChart, TreemapChart, PieChart, RadarChart, GaugeChart } from 'echarts/charts'
import {
  GridComponent, TooltipComponent, DataZoomComponent,
  LegendComponent, MarkPointComponent, MarkLineComponent,
  VisualMapComponent, GraphicComponent, ToolboxComponent,
} from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'

echarts.use([
  CandlestickChart, LineChart, BarChart, ScatterChart, HeatmapChart,
  TreemapChart, PieChart, RadarChart, GaugeChart,
  GridComponent, TooltipComponent, DataZoomComponent,
  LegendComponent, MarkPointComponent, MarkLineComponent,
  VisualMapComponent, GraphicComponent, ToolboxComponent,
  CanvasRenderer,
])

export default echarts
