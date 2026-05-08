import { ref, readonly, type Ref } from 'vue'

export interface WebVitalMetric {
  name: string
  value: number
  rating: 'good' | 'needs-improvement' | 'poor'
  delta: number
  navigationType: string
}

export interface UseWebVitalsReturn {
  metrics: Readonly<Ref<Record<string, WebVitalMetric>>>
  isSupported: boolean
}

const GOOD_LCP = 2500
const POOR_LCP = 4000
const GOOD_FID = 100
const POOR_FID = 300
const GOOD_CLS = 0.1
const POOR_CLS = 0.25
const GOOD_INP = 200
const POOR_INP = 500

export function rateMetric(name: string, value: number): 'good' | 'needs-improvement' | 'poor' {
  switch (name) {
    case 'LCP': return value <= GOOD_LCP ? 'good' : value <= POOR_LCP ? 'needs-improvement' : 'poor'
    case 'FID': return value <= GOOD_FID ? 'good' : value <= POOR_FID ? 'needs-improvement' : 'poor'
    case 'CLS': return value <= GOOD_CLS ? 'good' : value <= POOR_CLS ? 'needs-improvement' : 'poor'
    case 'INP': return value <= GOOD_INP ? 'good' : value <= POOR_INP ? 'needs-improvement' : 'poor'
    default: return 'good'
  }
}

function getNavigationType(): string {
  const entries = performance.getEntriesByType('navigation')
  if (entries.length === 0) return 'unknown'
  const nav = entries[0] as PerformanceNavigationTiming
  if (nav.redirectCount > 0) return 'redirect'
  if (nav.type === 'reload') return 'reload'
  if (nav.type === 'back_forward') return 'back_forward'
  return 'navigate'
}

export function useWebVitals(): UseWebVitalsReturn {
  const metrics = ref<Record<string, WebVitalMetric>>({})
  const isSupported = typeof PerformanceObserver !== 'undefined'

  if (!isSupported) {
    return { metrics: readonly(metrics), isSupported: false }
  }

  const navigationType = getNavigationType()

  function recordMetric(name: string, value: number, delta: number): void {
    metrics.value[name] = {
      name,
      value: Math.round(value * 100) / 100,
      rating: rateMetric(name, value),
      delta,
      navigationType,
    }
  }

  try {
    const lcpObserver = new PerformanceObserver((list) => {
      const entries = list.getEntries()
      if (entries.length > 0) {
        const last = entries[entries.length - 1]
        recordMetric('LCP', last.startTime, last.startTime)
      }
    })
    lcpObserver.observe({ type: 'largest-contentful-paint', buffered: true })
  } catch { /* LCP not supported */ }

  try {
    const fidObserver = new PerformanceObserver((list) => {
      for (const entry of list.getEntries()) {
        const fe = entry as PerformanceEntry & { processingStart: number }
        recordMetric('FID', fe.processingStart - fe.startTime, fe.processingStart - fe.startTime)
      }
    })
    fidObserver.observe({ type: 'first-input', buffered: true })
  } catch { /* FID not supported */ }

  try {
    let clsValue = 0
    const clsObserver = new PerformanceObserver((list) => {
      for (const entry of list.getEntries()) {
        const ls = entry as PerformanceEntry & { hadRecentInput: boolean; value: number }
        if (!ls.hadRecentInput) {
          clsValue += ls.value
          recordMetric('CLS', clsValue, ls.value)
        }
      }
    })
    clsObserver.observe({ type: 'layout-shift', buffered: true })
  } catch { /* CLS not supported */ }

  try {
    const inpObserver = new PerformanceObserver((list) => {
      for (const entry of list.getEntries()) {
        const ei = entry as PerformanceEntry & { duration: number }
        recordMetric('INP', ei.duration, ei.duration)
      }
    })
    inpObserver.observe({ type: 'event', buffered: true })
  } catch { /* INP not supported */ }

  return { metrics: readonly(metrics), isSupported: true }
}
