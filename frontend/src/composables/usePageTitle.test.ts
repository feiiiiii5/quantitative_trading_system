import { describe, it, expect, vi, beforeEach } from 'vitest'

const mockRoute = { name: 'Dashboard' }
vi.mock('vue-router', () => ({
  useRoute: () => mockRoute,
}))

const { usePageTitle, ROUTE_TITLE_MAP } = await import('./usePageTitle')

describe('usePageTitle', () => {
  beforeEach(() => {
    document.title = ''
  })

  it('sets document.title from ROUTE_TITLE_MAP', () => {
    mockRoute.name = 'Dashboard'
    usePageTitle()
    expect(document.title).toBe('DASHBOARD · QUANTCORE')
  })

  it('appends suffix when provided', () => {
    mockRoute.name = 'StockDetail'
    usePageTitle(() => '600519')
    expect(document.title).toBe('STOCK DETAIL — 600519 · QUANTCORE')
  })

  it('uses APP_NAME only for Landing route', () => {
    mockRoute.name = 'Landing'
    usePageTitle()
    expect(document.title).toBe('QUANTCORE')
  })

  it('falls back to uppercase route name for unknown routes', () => {
    mockRoute.name = 'CustomPage'
    usePageTitle()
    expect(document.title).toBe('CUSTOMPAGE · QUANTCORE')
  })

  it('ROUTE_TITLE_MAP has entries for all major routes', () => {
    const expectedRoutes = ['Dashboard', 'Market', 'StockDetail', 'Portfolio', 'Watchlist', 'Chip', 'FactorLab', 'TCA', 'ML']
    for (const r of expectedRoutes) {
      expect(ROUTE_TITLE_MAP[r]).toBeDefined()
    }
  })
})
