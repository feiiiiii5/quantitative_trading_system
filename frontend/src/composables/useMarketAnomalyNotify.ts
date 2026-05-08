import { watch, onScopeDispose } from 'vue'
import { useWebSocketStore, type WsMessage } from '@/stores/websocket'
import { useToast, type ToastType } from '@/composables/useToast'

const ALERT_TYPE_MAP: Record<string, { label: string; toast: ToastType }> = {
  volume_spike: { label: '量能异动', toast: 'warning' },
  price_spike: { label: '价格异动', toast: 'warning' },
  rapid_rise: { label: '快速拉升', toast: 'info' },
  rapid_fall: { label: '快速下跌', toast: 'warning' },
  price_above: { label: '价格突破', toast: 'info' },
  price_below: { label: '价格跌破', toast: 'warning' },
  change_pct_above: { label: '涨幅达标', toast: 'info' },
  change_pct_below: { label: '跌幅达标', toast: 'warning' },
}

const MAX_NOTIFY_PER_MINUTE = 10
const NOTIFY_WINDOW_MS = 60_000

export function useMarketAnomalyNotify(): void {
  const wsStore = useWebSocketStore()
  const { toast } = useToast()
  const recentTimestamps: number[] = []

  function shouldThrottle(): boolean {
    const now = Date.now()
    while (recentTimestamps.length && now - recentTimestamps[0] > NOTIFY_WINDOW_MS) {
      recentTimestamps.shift()
    }
    return recentTimestamps.length >= MAX_NOTIFY_PER_MINUTE
  }

  function handleSmartAlert(msg: WsMessage) {
    if (shouldThrottle()) return
    recentTimestamps.push(Date.now())

    const d = msg.data
    const symbol = String(d.symbol ?? '')
    const name = String(d.name ?? symbol)
    const alertType = String(d.alert_type ?? '')
    const zScore = d.z_score != null ? Number(d.z_score).toFixed(1) : ''

    const mapped = ALERT_TYPE_MAP[alertType]
    const label = mapped?.label ?? alertType
    const toastType = mapped?.toast ?? 'info'

    toast(toastType, `${name} ${label}${zScore ? ` Z=${zScore}` : ''}`)
  }

  function handleAlertTriggered(msg: WsMessage) {
    if (shouldThrottle()) return
    recentTimestamps.push(Date.now())

    const d = msg.data
    const name = String(d.name ?? d.symbol ?? '')
    const direction = String(d.direction ?? '')
    const targetPrice = d.target_price != null ? Number(d.target_price).toFixed(2) : ''

    const mapped = ALERT_TYPE_MAP[direction] ?? ALERT_TYPE_MAP.price_above
    toast(mapped.toast, `${name} ${mapped.label} ${targetPrice}`)
  }

  function handleRiskAlert(msg: WsMessage) {
    const d = msg.data
    const symbol = String(d.symbol ?? '')
    const action = String(d.action ?? '')
    const reasons: string[] = Array.isArray(d.reasons) ? d.reasons.map(String) : []
    toast('error', `[风控拦截] ${symbol} ${action}: ${reasons.join('；')}`)
  }

  const stopWatch = watch(
    () => wsStore.lastMessage,
    (msg) => {
      if (!msg) return
      if (msg.type === 'smart_alert') handleSmartAlert(msg)
      else if (msg.type === 'alert_triggered') handleAlertTriggered(msg)
      else if (msg.type === 'risk_alert') handleRiskAlert(msg)
    },
  )

  onScopeDispose(() => {
    stopWatch()
  })
}
