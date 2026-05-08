import { watch, computed } from 'vue'
import { useRoute } from 'vue-router'

const APP_NAME = 'QUANTCORE'

export const ROUTE_TITLE_MAP: Record<string, string> = {
  Dashboard: 'DASHBOARD',
  Market: 'MARKET',
  StockDetail: 'STOCK DETAIL',
  StrategyIntro: 'STRATEGY',
  StrategyRun: 'STRATEGY RUN',
  StrategyDashboard: 'STRATEGY DASHBOARD',
  Optimizer: 'OPTIMIZER',
  Portfolio: 'PORTFOLIO',
  Watchlist: 'WATCHLIST',
  News: 'NEWS',
  Screener: 'SCREENER',
  MoneyFlow: 'MONEY FLOW',
  Chip: 'CHIP',
  ChipDetail: 'CHIP DETAIL',
  Alerts: 'ALERTS',
  Sector: 'SECTOR',
  FactorLab: 'FACTOR LAB',
  TCA: 'TRADE COST ANALYZER',
  ML: 'ML STRATEGY',
  Login: 'LOGIN',
  Landing: 'QUANTCORE',
}

export function usePageTitle(suffix?: () => string) {
  const route = useRoute()

  const title = computed(() => {
    const base = ROUTE_TITLE_MAP[route.name as string]
      ?? String(route.name ?? '').toUpperCase()
    const extra = suffix?.()
    return extra ? `${base} — ${extra}` : base
  })

  watch(title, (t) => {
    document.title = t === APP_NAME ? t : `${t} · ${APP_NAME}`
  }, { immediate: true })

  return { title, ROUTE_TITLE_MAP }
}
