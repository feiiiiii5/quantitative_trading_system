import axios from 'axios'
import type {
  ApiResponse,
  MarketOverview,
  MarketStatus,
  StockQuote,
  KlineBar,
  HeatmapItem,
  AnomalyItem,
  NorthboundData,
  SignalItem,
  DeepAnalysis,
  PredictionData,
  AiSummary,
  Fundamentals,
  CorrelationData,
  FactorAnalysis,
  StrategyInfo,
  BacktestResult,
  AccountInfo,
  PortfolioRisk,
  PortfolioEquity,
  WatchlistData,
  PriceAlert,
  SearchItem,
  SystemMetrics,
  WeeklyReport,
  MarketStock,
  NewsItem,
  MarketSentimentData,
  ScreenerPreset,
  ScreenerResult,
  CapitalFlowData,
  CapitalFlowRealtime,
  SectorFlowItem,
  ChipData,
  SectorStrengthItem,
  SectorRotationData,
  SectorDetail,
} from '@/types'

const http = axios.create({ baseURL: '/api', timeout: 30000 })

async function get<T>(url: string, params?: Record<string, unknown>): Promise<T> {
  const { data } = await http.get<ApiResponse<T>>(url, { params })
  if (!data.success) throw new Error(data.error || '请求失败')
  return data.data
}

async function post<T>(url: string, data?: Record<string, unknown>): Promise<T> {
  const { data: resp } = await http.post<ApiResponse<T>>(url, data)
  if (!resp.success) throw new Error(resp.error || '请求失败')
  return resp.data
}

export const api = {
  market: {
    overview: () => get<MarketOverview>('/market/overview'),
    status: () => get<Record<string, MarketStatus>>('/market/status'),
    heatmap: (market = 'A') => get<{ market: string; items: HeatmapItem[] }>('/market/heatmap', { market }),
    stocks: (market = 'A', limit = 5000) => get<MarketStock[]>('/market/stocks', { market, limit }),
    anomaly: () => get<AnomalyItem[]>('/market/anomaly'),
    northbound: () => get<NorthboundData>('/market/northbound/detail'),
    limitUp: () => get<unknown[]>('/market/limit_up'),
    dragonTiger: () => get<unknown[]>('/market/dragon_tiger'),
  },

  stock: {
    realtime: (symbol: string) => get<StockQuote>(`/stock/realtime/${symbol}`),
    history: (symbol: string, period = '1y', klineType = 'daily', adjust = '') =>
      get<KlineBar[]>(`/stock/history/${symbol}`, { period, kline_type: klineType, adjust }),
    indicators: (symbol: string, period = '1y', klineType = 'daily') =>
      get<Record<string, unknown>>(`/stock/indicators/${symbol}`, { period, kline_type: klineType }),
    analysis: (symbol: string, period = '1y') => get<DeepAnalysis>(`/stock/analysis/${symbol}`, { period }),
    prediction: (symbol: string, period = '1y') => get<PredictionData>(`/stock/prediction/${symbol}`, { period }),
    signals: (symbol: string, period = '1y', strategy = 'all') =>
      get<{ symbol: string; signals: SignalItem[] }>(`/stock/signals/${symbol}`, { period, strategy }),
    aiSummary: (symbol: string, period = '1y') => get<AiSummary>(`/stock/ai_summary/${symbol}`, { period }),
    fundamentals: (symbol: string) => get<Fundamentals>(`/stock/fundamentals/${symbol}`),
    correlation: (symbol: string, benchmark = 'sh000300', period = '1y') =>
      get<CorrelationData>(`/stock/correlation/${symbol}`, { benchmark, period }),
  },

  factor: {
    analysis: (symbol: string, period = '1y') => get<FactorAnalysis>(`/factor/analysis/${symbol}`, { period }),
  },

  backtest: {
    strategies: () => get<Record<string, StrategyInfo>>('/backtest/strategies'),
    run: (params: { symbol: string; strategy_type?: string; start_date?: string; end_date?: string; initial_capital?: number }) =>
      post<BacktestResult>('/backtest/run', params),
    compare: (symbol: string, startDate = '2024-01-01', endDate = '2025-12-31') =>
      get<BacktestResult[]>('/backtest/compare', { symbol, start_date: startDate, end_date: endDate }),
    advanced: (params: Record<string, unknown>) => post<BacktestResult>('/backtest/advanced', params),
    recommend: (symbol: string, startDate = '2024-01-01', endDate = '2025-12-31') =>
      get<{ analysis: Record<string, unknown>; recommendations: { strategy: string; strategy_class: string; score: number; reasons: string[] }[] }>('/backtest/recommend', { symbol, start_date: startDate, end_date: endDate }),
    history: (symbol?: string, limit = 20) => get<unknown[]>('/backtest/history', { symbol, limit }),
  },

  portfolio: {
    riskAnalysis: (symbols: string[], period = '1y') =>
      get<PortfolioRisk>('/portfolio/risk_analysis', { symbols: symbols.join(','), period }),
    attribution: (symbols: string[], benchmark = 'sh000300', period = '1y') =>
      get<unknown>('/portfolio/attribution', { symbols: symbols.join(','), benchmark, period }),
    equity: (symbols: string[], period = '1y') =>
      get<PortfolioEquity>('/portfolio/equity', { symbols: symbols.join(','), period }),
  },

  trading: {
    account: () => get<AccountInfo>('/trading/account'),
    buy: (params: { symbol: string; name?: string; market?: string; price: number; shares: number; stop_loss?: number; take_profit?: number; strategy?: string }) =>
      post<unknown>('/trading/buy', params),
    sell: (params: { symbol: string; price: number; shares?: number; reason?: string }) =>
      post<unknown>('/trading/sell', params),
    history: (limit = 100) => get<{ trades: unknown[]; total: number }>('/trading/history', { limit }),
  },

  watchlist: {
    get: () => get<WatchlistData>('/watchlist'),
    add: (symbol: string) => post<string[]>('/watchlist/add', { symbol }),
    remove: (symbol: string) => post<string[]>('/watchlist/remove', { symbol }),
    reorder: (symbols: string) => post<string[]>('/watchlist/reorder', { symbols }),
    alerts: () => get<PriceAlert[]>('/watchlist/alert/list'),
    addAlert: (params: { symbol: string; alert_type: string; value: number }) =>
      post<PriceAlert>('/watchlist/alert/add', params),
    removeAlert: (alertId: string) => post<unknown>('/watchlist/alert/remove', { alert_id: alertId }),
  },

  search: {
    stocks: (q: string, limit = 10) => get<SearchItem[]>('/search', { q, limit }),
  },

  report: {
    weekly: () => get<WeeklyReport>('/report/weekly'),
  },

  system: {
    metrics: () => get<SystemMetrics>('/system/metrics'),
  },

  news: {
    latest: (count = 40) => get<NewsItem[]>('/news/latest', { count }),
    stock: (symbol: string, count = 20) => get<NewsItem[]>(`/news/stock/${symbol}`, { count }),
    sentiment: () => get<MarketSentimentData>('/news/sentiment'),
  },

  screener: {
    presets: () => get<ScreenerPreset[]>('/screener/presets'),
    run: (preset?: string, sortBy = 'change_pct', sortDesc = true, limit = 50) =>
      get<ScreenerResult>('/screener/run', { preset, sort_by: sortBy, sort_desc: sortDesc, limit }),
    custom: (conditions: Record<string, unknown>[], sortBy = 'change_pct', sortDesc = true, limit = 50) =>
      post<ScreenerResult>('/screener/custom', { conditions, sort_by: sortBy, sort_desc: sortDesc, limit }),
  },

  moneyFlow: {
    stock: (symbol: string, days = 10) => get<CapitalFlowData>(`/moneyflow/stock/${symbol}`, { days }),
    ranking: (sortBy = 'main_net', count = 30) => get<CapitalFlowRealtime[]>('/moneyflow/ranking', { sort_by: sortBy, count }),
    sector: () => get<SectorFlowItem[]>('/moneyflow/sector'),
  },

  chip: {
    distribution: (symbol: string, period = '1y') => get<ChipData>(`/chip/${symbol}`, { period }),
  },

  sector: {
    strength: (topN = 20) => get<SectorStrengthItem[]>('/sector/strength', { top_n: topN }),
    rotation: () => get<SectorRotationData>('/sector/rotation'),
    detail: (sectorCode: string) => get<SectorDetail>(`/sector/${sectorCode}/stocks`),
  },
}
