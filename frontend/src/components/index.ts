import BaseChart from './BaseChart.vue'
import MetricCard from './MetricCard.vue'
import PriceTag from './PriceTag.vue'
import SparkLine from './SparkLine.vue'
import SignalBadge from './SignalBadge.vue'
import ToastNotification from './ToastNotification.vue'
import LoadingOverlay from './LoadingOverlay.vue'
import DataTable from './DataTable.vue'

export function registerGlobalComponents(app: any) {
  app.component('BaseChart', BaseChart)
  app.component('MetricCard', MetricCard)
  app.component('PriceTag', PriceTag)
  app.component('SparkLine', SparkLine)
  app.component('SignalBadge', SignalBadge)
  app.component('ToastNotification', ToastNotification)
  app.component('LoadingOverlay', LoadingOverlay)
  app.component('DataTable', DataTable)
}

export { BaseChart, MetricCard, PriceTag, SparkLine, SignalBadge, ToastNotification, LoadingOverlay, DataTable }
