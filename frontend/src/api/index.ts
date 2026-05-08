import axios from 'axios'
import { createLogger } from '@/composables/useLogger'
import { dedupedRequest } from '@/composables/useDedupedRequest'
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
  BacktestHistoryItem,
  AccountInfo,
  PortfolioRisk,
  PortfolioEquity,
  PortfolioAttribution,
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
  LimitUpItem,
  DragonTigerItem,
  TradeResult,
  TradeRecord,
  PerformanceOverview,
  MarketEvent,
} from '@/types'

const HTTP_STATUS_UNAUTHORIZED = 401
const HTTP_STATUS_TOO_MANY_REQUESTS = 429
const HTTP_STATUS_SERVER_ERROR = 500

const http = axios.create({ baseURL: '/api', timeout: 30_000 })
const log = createLogger('API')

let _requestSeq = 0

const MAX_RETRIES = 2
const RETRY_DELAY_MS = 500

const _feCache = new Map<string, { data: unknown; ts: number; ttl: number }>()
const _FE_CACHE_MAX = 2000

function _feCacheGet<T>(key: string): T | null {
  const entry = _feCache.get(key)
  if (!entry) return null
  if (Date.now() - entry.ts > entry.ttl) {
    _feCache.delete(key)
    return null
  }
  return entry.data as T
}

function _feCacheSet(key: string, data: unknown, ttl: number): void {
  if (_feCache.size >= _FE_CACHE_MAX) {
    let oldestKey: string | null = null
    let oldestTs = Infinity
    for (const [k, v] of _feCache) {
      if (v.ts < oldestTs) {
        oldestTs = v.ts
        oldestKey = k
      }
    }
    if (oldestKey !== null) _feCache.delete(oldestKey)
  }
  _feCache.set(key, { data, ts: Date.now(), ttl })
}

function _feCacheKey(url: string, params?: Record<string, unknown>): string {
  return `get:${url}:${JSON.stringify(params ?? {})}`
}

function _feCacheInvalidate(prefix?: string): void {
  if (!prefix) {
    _feCache.clear()
    return
  }
  for (const key of _feCache.keys()) {
    if (key.includes(prefix)) {
      _feCache.delete(key)
    }
  }
}

function isRetryableError(error: unknown): boolean {
  if (!axios.isAxiosError(error)) return false
  if (error.code === 'ECONNABORTED' || error.code === 'ERR_CANCELED') return false
  if (!error.response) return true
  const status = error.response.status
  return status >= HTTP_STATUS_SERVER_ERROR || status === HTTP_STATUS_TOO_MANY_REQUESTS
}

async function withRetry<T>(fn: () => Promise<T>, retries = MAX_RETRIES): Promise<T> {
  let lastError: unknown
  for (let attempt = 0; attempt <= retries; attempt++) {
    try {
      return await fn()
    } catch (error) {
      lastError = error
      if (attempt < retries && isRetryableError(error)) {
        const delay = RETRY_DELAY_MS * Math.pow(2, attempt)
        await new Promise(resolve => setTimeout(resolve, delay))
        continue
      }
      throw error
    }
  }
  throw lastError
}

http.interceptors.request.use((config) => {
  const token = localStorage.getItem('auth_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  _requestSeq++
  config.headers['X-Request-ID'] = `fe-${Date.now().toString(36)}-${_requestSeq}`
  return config
})

http.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.code === 'ECONNABORTED' || error.code === 'ERR_CANCELED') {
      log.warn('请求超时或已取消', error.config?.url)
    } else if (error.response) {
      const status = error.response.status
      if (status === 401) {
        localStorage.removeItem('auth_token')
        if (window.location.pathname !== '/login') {
          window.location.href = '/login'
        }
      } else if (status === HTTP_STATUS_TOO_MANY_REQUESTS) {
        log.warn('请求频率超限')
      } else if (status >= HTTP_STATUS_SERVER_ERROR) {
        log.error('服务器错误: ' + status, error.config?.url)
      } else if (status >= 400) {
        log.warn('客户端错误: ' + status, error.config?.url)
      }
    } else if (error.request) {
      log.error('网络错误: 无响应', error.config?.url)
    }
    return Promise.reject(error)
  }
)

async function get<T>(url: string, params?: Record<string, unknown>, signal?: AbortSignal, cacheTtl?: number): Promise<T> {
  const cacheKey = _feCacheKey(url, params)
  if (cacheTtl !== undefined && cacheTtl > 0) {
    const cached = _feCacheGet<T>(cacheKey)
    if (cached !== null) return cached
  }
  const dedupKey = `get:${cacheKey}`
  const result = await dedupedRequest<T>(dedupKey, () =>
    withRetry(async () => {
      const { data } = await http.get<ApiResponse<T>>(url, { params, signal })
      if (!data.success) throw new Error(data.error || '请求失败')
      return data.data
    })
  )
  if (cacheTtl !== undefined && cacheTtl > 0) {
    _feCacheSet(cacheKey, result, cacheTtl)
  }
  return result
}

async function post<T>(url: string, data?: Record<string, unknown>, signal?: AbortSignal): Promise<T> {
  const result = await withRetry(async () => {
    const { data: resp } = await http.post<ApiResponse<T>>(url, data, { signal })
    if (!resp.success) throw new Error(resp.error || '请求失败')
    return resp.data
  })
  _feCacheInvalidate(url)
  return result
}

async function postForm<T>(url: string, data?: Record<string, unknown>, signal?: AbortSignal): Promise<T> {
  const result = await withRetry(async () => {
    const params = new URLSearchParams()
    if (data) {
      for (const [k, v] of Object.entries(data)) {
        params.append(k, String(v))
      }
    }
    const { data: resp } = await http.post<ApiResponse<T>>(url, params, {
      signal,
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    })
    if (!resp.success) throw new Error(resp.error || '请求失败')
    return resp.data
  })
  _feCacheInvalidate(url)
  return result
}

async function putForm<T>(url: string, data?: Record<string, unknown>, signal?: AbortSignal): Promise<T> {
  const result = await withRetry(async () => {
    const params = new URLSearchParams()
    if (data) {
      for (const [k, v] of Object.entries(data)) {
        params.append(k, String(v))
      }
    }
    const { data: resp } = await http.put<ApiResponse<T>>(url, params, {
      signal,
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    })
    if (!resp.success) throw new Error(resp.error || '请求失败')
    return resp.data
  })
  _feCacheInvalidate(url)
  return result
}

async function del<T>(url: string, signal?: AbortSignal): Promise<T> {
  const result = await withRetry(async () => {
    const { data: resp } = await http.delete<ApiResponse<T>>(url, { signal })
    if (!resp.success) throw new Error(resp.error || '请求失败')
    return resp.data
  })
  _feCacheInvalidate(url)
  return result
}

export function createCancellableRequest() {
  const controller = new AbortController()
  const signal = controller.signal
  const cancel = () => controller.abort()
  return { signal, cancel }
}

export const api = {
  auth: {
    login: (username: string, password: string) =>
      post<{ token: string; username: string; role: string }>('/auth/login', { username, password }),
    register: (username: string, password: string) =>
      post<{ username: string }>('/auth/register', { username, password }),
    me: () => get<{ username: string; role: string }>('/auth/me'),
  },
  market: {
    overview: () => get<MarketOverview>('/market/overview', undefined, undefined, 15000),
    status: () => get<Record<string, MarketStatus>>('/market/status', undefined, undefined, 60000),
    heatmap: (market = 'A') => get<{ market: string; items: HeatmapItem[] }>('/market/heatmap', { market }, undefined, 30000),
    events: (limit = 20) => get<MarketEvent[]>('/market/events', { limit }, undefined, 30000),
    stocks: (market = 'A', limit = 5000) => get<MarketStock[]>('/market/stocks', { market, limit }, undefined, 30000),
    anomaly: () => get<AnomalyItem[]>('/market/anomaly', undefined, undefined, 30000),
    northbound: () => get<NorthboundData>('/market/northbound/detail', undefined, undefined, 60000),
    limitUp: () => get<LimitUpItem[]>('/market/limit_up', undefined, undefined, 30000),
    dragonTiger: () => get<DragonTigerItem[]>('/market/dragon_tiger', undefined, undefined, 30000),
  },

  stock: {
    realtime: (symbol: string) => get<StockQuote>(`/stock/realtime/${symbol}`, undefined, undefined, 10000),
    history: (symbol: string, period = '1y', klineType = 'daily', adjust = '') =>
      get<KlineBar[]>(`/stock/history/${symbol}`, { period, kline_type: klineType, adjust }, undefined, 60000),
    indicators: (symbol: string, period = '1y', klineType = 'daily') =>
      get<Record<string, unknown>>(`/stock/indicators/${symbol}`, { period, kline_type: klineType }, undefined, 120000),
    analysis: (symbol: string, period = '1y') => get<DeepAnalysis>(`/stock/analysis/${symbol}`, { period }, undefined, 30000),
    prediction: (symbol: string, period = '1y') => get<PredictionData>(`/stock/prediction/${symbol}`, { period }),
    signals: (symbol: string, period = '1y', strategy = 'all') =>
      get<{ symbol: string; signals: SignalItem[] }>(`/stock/signals/${symbol}`, { period, strategy }),
    aiSummary: (symbol: string, period = '1y') => get<AiSummary>(`/stock/ai_summary/${symbol}`, { period }, undefined, 60000),
    fundamentals: (symbol: string) => get<Fundamentals>(`/stock/fundamentals/${symbol}`, undefined, undefined, 600000),
    correlation: (symbol: string, benchmark = 'sh000300', period = '1y') =>
      get<CorrelationData>(`/stock/correlation/${symbol}`, { benchmark, period }, undefined, 120000),
    regime: (symbol: string, period = '1y') =>
      get<Record<string, unknown>>(`/market/regime`, { symbol, period }, undefined, 60000),
  },

  factor: {
    analysis: (symbol: string, period = '1y') => get<FactorAnalysis>(`/factor/analysis/${symbol}`, { period }, undefined, 60000),
    registry: () => get<{ factors: { name: string; category: string; description: string }[]; categories: string[] }>('/factor/registry', undefined, undefined, 60000),
    icAnalysis: (params: { factor_values: number[]; forward_returns: number[]; max_lag?: number; n_quintiles?: number }) =>
      post<{ factor_name: string; mean_ic: number; icir: number; ic_decay: number[]; turnover: number; long_short_return: number; long_short_sharpe: number; monotonicity: number }>('/factor/ic-analysis', params),
    quintileTest: (params: { factor_values: number[]; forward_returns: number[]; n_quintiles?: number }) =>
      post<Record<string, number>>('/factor/quintile-test', params),
    neutralize: (params: { factor_values: number[]; industry_labels: string[]; market_cap: number[]; style_factors?: Record<string, number[]> }) =>
      post<{ neutralized_values: (number | null)[] }>('/factor/neutralize', params),
    rotation: (params: { factor_names: string[]; factor_values_ts: Record<string, number[]>; forward_returns_ts: Record<string, number[]>; recent_window?: number; long_term_window?: number }) =>
      post<{ factor_name: string; recent_ic: number; long_term_ic: number; ic_change: number; recommendation: string }[]>('/factor/rotation', params),
    optimize: (params: { expected_returns: number[]; cov_matrix: number[][]; factor_exposures: number[][]; factor_constraints: number[]; max_weight?: number; risk_free_rate?: number }) =>
      post<{ weights: number[] }>('/factor/optimize', params),
  },

  backtest: {
    strategies: () => get<Record<string, StrategyInfo>>('/backtest/strategies', undefined, undefined, 60000),
    run: (params: { symbol: string; strategy_type?: string; start_date?: string; end_date?: string; initial_capital?: number }) =>
      post<BacktestResult>('/backtest/run', params),
    compare: (symbol: string, startDate = '2024-01-01', endDate = '2025-12-31') =>
      get<BacktestResult[]>('/backtest/compare', { symbol, start_date: startDate, end_date: endDate }),
    advanced: (params: Record<string, unknown>) => post<BacktestResult>('/backtest/advanced', params),
    recommend: (symbol: string, startDate = '2024-01-01', endDate = '2025-12-31') =>
      get<{ analysis: Record<string, unknown>; recommendations: { strategy: string; strategy_class: string; score: number; reasons: string[] }[] }>('/backtest/recommend', { symbol, start_date: startDate, end_date: endDate }),
    history: (symbol?: string, limit = 20) => get<BacktestHistoryItem[]>('/backtest/history', { symbol, limit }),
    performanceOverview: (symbol = '600000', period = '1y') =>
      get<PerformanceOverview>('/backtest/performance_overview', { symbol, period }),
    attribution: (symbol: string, strategy = 'dual_ma', period = 250) =>
      get<{ total_return: number; factor_contributions: Record<string, number>; factor_weights: Record<string, number>; residual: number; r_squared: number }>('/backtest/attribution', { symbol, strategy, period }, undefined, 60000),
  },

  portfolio: {
    riskAnalysis: (symbols: string[], period = '1y') =>
      get<PortfolioRisk>('/portfolio/risk_analysis', { symbols: symbols.join(','), period }),
    attribution: (symbols: string[], benchmark = 'sh000300', period = '1y') =>
      get<PortfolioAttribution>('/portfolio/attribution', { symbols: symbols.join(','), benchmark, period }),
    equity: (symbols: string[], period = '1y') =>
      get<PortfolioEquity>('/portfolio/equity', { symbols: symbols.join(','), period }),
    correlation: (symbols: string[], period = '1y') =>
      get<{ symbols: string[]; matrix: number[][] }>('/portfolio/correlation', { symbols: symbols.join(','), period }),
    rebalance: (symbols: string[], capital = 100000, driftThreshold = 0.05) =>
      get<{ needs_rebalance: boolean; reason: string; total_turnover: number; max_drift: number; trades: { symbol: string; name: string; current_weight: number; target_weight: number; weight_delta: number; action: string; shares: number; price: number }[] }>('/portfolio/rebalance', { symbols: symbols.join(','), capital, drift_threshold: driftThreshold }, undefined, 60000),
    stressScenarios: () =>
      get<{ name: string; description: string; equity_shock: number; bond_shock: number; commodity_shock: number; volatility_mult: number }[]>('/portfolio/stress/scenarios'),
    stressRun: (positions: { symbol: string; value: number; type: string }[], runMonteCarlo = false, horizonDays = 20, nSimulations = 5000) =>
      post<{ scenarios: { scenario_name: string; portfolio_impact_pct: number; position_impacts: Record<string, number>; description: string }[]; monte_carlo: Record<string, unknown> | null }>('/portfolio/stress/run', { positions, run_monte_carlo: runMonteCarlo, horizon_days: horizonDays, n_simulations: nSimulations }),
    optimize: (symbols: string[], method = 'max_sharpe', period = '1y') =>
      get<{ method: string; allocations: { symbol: string; weight: number; weight_pct: number }[]; metrics: { expected_annual_return: number; expected_volatility: number; sharpe_ratio: number; risk_free_rate: number }; symbols: string[]; period: string }>('/portfolio/optimize', { symbols: symbols.join(','), method, period }),
  },

  trading: {
    account: () => get<AccountInfo>('/trading/account', undefined, undefined, 5000),
    buy: (params: { symbol: string; name?: string; market?: string; price: number; shares: number; stop_loss?: number; take_profit?: number; strategy?: string }) =>
      post<TradeResult>('/trading/buy', params),
    sell: (params: { symbol: string; price: number; shares?: number; reason?: string }) =>
      post<TradeResult>('/trading/sell', params),
    history: (limit = 100) => get<{ trades: TradeRecord[]; total: number }>('/trading/history', { limit }, undefined, 30000),
  },

  watchlist: {
    get: () => get<WatchlistData>('/watchlist', undefined, undefined, 5000),
    add: (symbol: string) => post<string[]>('/watchlist/add', { symbol }),
    remove: (symbol: string) => post<string[]>('/watchlist/remove', { symbol }),
    reorder: (symbols: string) => post<string[]>('/watchlist/reorder', { symbols }),
    alerts: () => get<PriceAlert[]>('/watchlist/alert/list', undefined, undefined, 10000),
    addAlert: (params: { symbol: string; alert_type: string; value: number }) =>
      post<PriceAlert>('/watchlist/alert/add', params),
    removeAlert: (alertId: string) => post<PriceAlert>('/watchlist/alert/remove', { alert_id: alertId }),
  },

  alerts: {
    list: (enabled?: boolean) => get<PriceAlert[]>('/alerts', enabled !== undefined ? { enabled: String(enabled) } : undefined, undefined, 10000),
    create: (params: { symbol: string; target_price: number; direction: string; name?: string }) =>
      postForm<{ id: number }>('/alerts', params),
    update: (id: number, params: Record<string, unknown>) =>
      putForm<{ id: number }>(`/alerts/${id}`, params),
    delete: (id: number) => del<{ id: number }>(`/alerts/${id}`),
    history: (limit = 50) => get<PriceAlert[]>(`/alerts/history`, { limit }, undefined, 30000),
  },

  smartAlerts: {
    history: (limit = 50) => get<{ alerts: unknown[]; count: number }>('/smart-alerts/history', { limit }, undefined, 30000),
    stats: (symbol: string) => get<Record<string, unknown>>(`/smart-alerts/stats/${symbol}`, undefined, undefined, 10000),
  },

  journal: {
    list: (symbol?: string, tag?: string, limit = 50) => get<{ entries: { id: number; symbol: string; name: string; trade_type: string; price: number; quantity: number; notes: string; tags: string[]; emotion: string; rating: number; timestamp: number }[]; count: number }>('/journal', { symbol, tag, limit }),
    add: (params: { symbol: string; name?: string; trade_type?: string; price?: number; quantity?: number; notes?: string; tags?: string[]; emotion?: string; rating?: number }) => post<{ id: number }>('/journal', params),
    update: (id: number, params: Record<string, unknown>) => putForm<{ id: number }>(`/journal/${id}`, params),
    delete: (id: number) => del<{ id: number }>(`/journal/${id}`),
    stats: () => get<Record<string, unknown>>('/journal/stats', undefined, undefined, 30000),
  },

  search: {
    stocks: (q: string, limit = 10) => get<SearchItem[]>('/search', { q, limit }, undefined, 60000),
  },

  report: {
    weekly: () => get<WeeklyReport>('/report/weekly', undefined, undefined, 300000),
  },

  system: {
    metrics: () => get<SystemMetrics>('/system/metrics', undefined, undefined, 5000),
  },

  news: {
    latest: (count = 40) => get<NewsItem[]>('/news/latest', { count }, undefined, 15000),
    stock: (symbol: string, count = 20) => get<NewsItem[]>(`/news/stock/${symbol}`, { count }, undefined, 15000),
    sentiment: () => get<MarketSentimentData>('/news/sentiment', undefined, undefined, 30000),
  },

  screener: {
    presets: () => get<ScreenerPreset[]>('/screener/presets', undefined, undefined, 60000),
    run: (preset?: string, sortBy = 'change_pct', sortDesc = true, limit = 50) =>
      get<ScreenerResult>('/screener/run', { preset, sort_by: sortBy, sort_desc: sortDesc, limit }, undefined, 10000),
    custom: (conditions: Record<string, unknown>[], sortBy = 'change_pct', sortDesc = true, limit = 50) =>
      post<ScreenerResult>('/screener/custom', { conditions, sort_by: sortBy, sort_desc: sortDesc, limit }),
  },

  moneyFlow: {
    stock: (symbol: string, days = 10) => get<CapitalFlowData>(`/moneyflow/stock/${symbol}`, { days }, undefined, 15000),
    ranking: (sortBy = 'main_net', count = 30) => get<CapitalFlowRealtime[]>('/moneyflow/ranking', { sort_by: sortBy, count }, undefined, 8000),
    sector: () => get<SectorFlowItem[]>('/moneyflow/sector', undefined, undefined, 15000),
  },

  chip: {
    distribution: (symbol: string, period = '1y') => get<ChipData>(`/chip/${symbol}`, { period }, undefined, 30000),
  },

  sector: {
    strength: (topN = 20) => get<SectorStrengthItem[]>('/sector/strength', { top_n: topN }, undefined, 10000),
    rotation: () => get<SectorRotationData>('/sector/rotation', undefined, undefined, 15000),
    detail: (sectorCode: string) => get<SectorDetail>(`/sector/${sectorCode}/stocks`, undefined, undefined, 15000),
  },

  optimizer: {
    paramSpecs: () => get<Record<string, unknown>>('/strategy/param-specs'),
    optimizeParams: (strategyName: string, symbol: string, metric = 'sharpe_ratio', period = '1y', maxCombos = 200) =>
      post<Record<string, unknown>>(`/strategy/optimize-params?strategy_name=${encodeURIComponent(strategyName)}&symbol=${encodeURIComponent(symbol)}&metric=${metric}&period=${period}&max_combos=${maxCombos}`),
    stressTest: (symbol: string, period = '1y', scenarios = '') =>
      post<Record<string, unknown>>(`/stress-test?symbol=${encodeURIComponent(symbol)}&period=${period}${scenarios ? '&scenarios=' + encodeURIComponent(scenarios) : ''}`),
  },

  volatility: {
    garch: (symbol: string, period = '1y') => get<Record<string, unknown>>(`/volatility/garch/${encodeURIComponent(symbol)}`, { period }),
  },

  regime: {
    hmm: (symbol: string, period = '1y', nStates = 3) => get<Record<string, unknown>>(`/regime/hmm/${encodeURIComponent(symbol)}`, { period, n_states: nStates }),
  },

  tca: {
    analyze: (params: { symbol: string; strategy_name?: string; side: string; decision_price: number; arrival_price: number; execution_price: number; vwap_benchmark?: number; twap_benchmark?: number; quantity: number; execution_timestamp?: string }) =>
      post<Record<string, unknown>>('/tca/analyze', params),
    batch: (params: { trades: Record<string, unknown>[] }) =>
      post<Record<string, unknown>>('/tca/batch', params),
    recommend: (symbol: string) =>
      post<{ symbol: string; recommended_algorithm: string; recommended_time_window: string; recommended_slice_count: number; estimated_cost_bps: number }>('/tca/recommend', { symbol }),
  },

  ml: {
    labels: (params: { prices: number[]; method?: string }) =>
      post<{ n_labels: number; labels: number[]; profit_count: number; loss_count: number; timeout_count: number }>('/ml/labels', params),
    train: (params: { features: Record<string, number[]>; labels: number[]; cv_method?: string; model_type?: string; n_splits?: number }) =>
      post<{ cv_mean: number; cv_std: number; feature_importance: Record<string, number>; n_samples: number }>('/ml/train', params),
    driftCheck: (params: { current_features: Record<string, number[]>; reference_features: Record<string, number[]>; significance_level?: number }) =>
      post<{ drift_detected: boolean; drifted_features: string[]; ks_statistics: Record<string, number>; alert_level: string }>('/ml/drift-check', params),
    metaLabel: (params: { primary_signals: number[]; actual_returns: number[]; features: Record<string, number[]> }) =>
      post<{ n_samples: number; positive_rate: number; cv_mean: number; cv_std: number; feature_importance: Record<string, number> }>('/ml/meta-label', params),
  },
}
