import { describe, it, expect, vi, beforeEach } from 'vitest'
import { useWebVitals, rateMetric } from './useWebVitals'

describe('useWebVitals', () => {
  beforeEach(() => {
    vi.stubGlobal('PerformanceObserver', undefined)
  })

  it('returns isSupported=false when PerformanceObserver is unavailable', () => {
    const { isSupported } = useWebVitals()
    expect(isSupported).toBe(false)
  })

  it('returns isSupported=true when PerformanceObserver exists', () => {
    vi.stubGlobal('PerformanceObserver', class {
      observe() {}
      disconnect() {}
    })
    const { isSupported } = useWebVitals()
    expect(isSupported).toBe(true)
  })

  it('initializes with empty metrics', () => {
    const { metrics } = useWebVitals()
    expect(metrics.value).toEqual({})
  })
})

describe('rateMetric', () => {
  it('rates LCP correctly', () => {
    expect(rateMetric('LCP', 1000)).toBe('good')
    expect(rateMetric('LCP', 3000)).toBe('needs-improvement')
    expect(rateMetric('LCP', 5000)).toBe('poor')
  })

  it('rates FID correctly', () => {
    expect(rateMetric('FID', 50)).toBe('good')
    expect(rateMetric('FID', 200)).toBe('needs-improvement')
    expect(rateMetric('FID', 500)).toBe('poor')
  })

  it('rates CLS correctly', () => {
    expect(rateMetric('CLS', 0.05)).toBe('good')
    expect(rateMetric('CLS', 0.15)).toBe('needs-improvement')
    expect(rateMetric('CLS', 0.5)).toBe('poor')
  })

  it('rates INP correctly', () => {
    expect(rateMetric('INP', 100)).toBe('good')
    expect(rateMetric('INP', 300)).toBe('needs-improvement')
    expect(rateMetric('INP', 600)).toBe('poor')
  })

  it('rates unknown metrics as good', () => {
    expect(rateMetric('UNKNOWN', 99999)).toBe('good')
  })
})
