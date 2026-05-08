import * as echarts from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import {
  LineChart, BarChart, CandlestickChart, PieChart,
  ScatterChart, HeatmapChart, GaugeChart, TreemapChart,
} from 'echarts/charts'
import {
  TitleComponent, TooltipComponent, GridComponent, LegendComponent,
  DataZoomComponent, VisualMapComponent, MarkLineComponent,
  MarkPointComponent, ToolboxComponent, GraphicComponent,
} from 'echarts/components'
import { CHART_THEME } from './chartTheme'

echarts.use([
  CanvasRenderer, LineChart, BarChart, CandlestickChart, PieChart,
  ScatterChart, HeatmapChart, GaugeChart, TreemapChart, TitleComponent,
  TooltipComponent, GridComponent, LegendComponent, DataZoomComponent,
  VisualMapComponent, MarkLineComponent, MarkPointComponent,
  ToolboxComponent, GraphicComponent,
])

echarts.registerTheme('quantcore', CHART_THEME)

export { CHART_THEME }
export default echarts
