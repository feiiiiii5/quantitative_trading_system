const API_BASE = '/api'

async function _fetch(path: string, params?: Record<string, string>, method = 'GET') {
  const url = new URL(`${API_BASE}${path}`, window.location.origin)
  if (params) {
    for (const [k, v] of Object.entries(params)) {
      url.searchParams.set(k, v)
    }
  }
  const resp = await fetch(url.toString(), { method })
  const data = await resp.json()
  return data.success ? data.data : null
}

export const api = {
  async getMarketOverview() {
    return _fetch('/market/overview')
  },

  async getMarketStatus() {
    return _fetch('/market/status')
  },

  async getRealtime(symbol: string) {
    return _fetch(`/stock/realtime/${symbol}`)
  },

  async getHistory(symbol: string, period = '1y', klineType = 'daily', adjust = '') {
    const params: Record<string, string> = { period, kline_type: klineType }
    if (adjust) params.adjust = adjust
    return _fetch(`/stock/history/${symbol}`, params)
  },

  async getFundamentals(symbol: string) {
    return _fetch(`/stock/fundamentals/${symbol}`)
  },

  async getIndicators(symbol: string, period = '1y', klineType = 'daily') {
    return _fetch(`/stock/indicators/${symbol}`, { period, kline_type: klineType })
  },

  async getDeepAnalysis(symbol: string, period = '1y') {
    return _fetch(`/stock/analysis/${symbol}`, { period })
  },

  async getPrediction(symbol: string, period = '1y') {
    return _fetch(`/stock/prediction/${symbol}`, { period })
  },

  async getSignals(symbol: string, period = '1y', strategy = 'all') {
    return _fetch(`/stock/signals/${symbol}`, { period, strategy })
  },

  async getCorrelation(symbol: string, benchmark = 'sh000300', period = '1y') {
    return _fetch(`/stock/correlation/${symbol}`, { benchmark, period })
  },

  async getFactorAnalysis(symbol: string, period = '1y') {
    return _fetch(`/factor/analysis/${symbol}`, { period })
  },

  async getMarketHeatmap(market = 'A') {
    return _fetch('/market/heatmap', { market })
  },

  async getNorthboundDetail() {
    return _fetch('/market/northbound/detail')
  },

  async getLimitUpPool() {
    return _fetch('/market/limit_up')
  },

  async getDragonTiger(date?: string) {
    const params: Record<string, string> = {}
    if (date) params.date = date
    return _fetch('/market/dragon_tiger', params)
  },

  async getPortfolioRiskAnalysis(symbols: string, period = '1y') {
    return _fetch('/portfolio/risk_analysis', { symbols, period })
  },

  async getPortfolioAttribution(symbols: string, benchmark = 'sh000300', period = '1y') {
    return _fetch('/portfolio/attribution', { symbols, benchmark, period })
  },

  async getWeeklyReport() {
    return _fetch('/report/weekly')
  },

  async runBacktest(symbol: string, strategyName = 'adaptive', startDate = '2022-01-01', endDate = '2024-12-31', initialCapital = 1000000, options: {
    monte_carlo?: boolean
    n_simulations?: number
    sensitivity?: boolean
    walk_forward?: boolean
  } = {}) {
    const params: Record<string, string> = {
      symbol,
      strategy_name: strategyName,
      start_date: startDate,
      end_date: endDate,
      initial_capital: String(initialCapital),
      monte_carlo: String(options.monte_carlo ?? false),
      n_simulations: String(options.n_simulations ?? 500),
    }
    return _fetch('/backtest/advanced', params, 'POST')
  },

  async optimizeStrategy(symbol: string, strategyName = 'ma_cross', startDate = '2023-01-01', endDate = '2024-12-31', metric = 'sharpe_ratio', maxCombinations = 100) {
    return _fetch('/backtest/optimize', {
      symbol,
      strategy_name: strategyName,
      start_date: startDate,
      end_date: endDate,
      metric,
      max_combinations: String(maxCombinations),
    }, 'POST')
  },

  async getBacktestHistory(symbol?: string, limit = 20) {
    const params: Record<string, string> = { limit: String(limit) }
    if (symbol) params.symbol = symbol
    return _fetch('/backtest/history', params)
  },

  async getWatchlist() {
    return _fetch('/watchlist')
  },

  async addToWatchlist(symbol: string) {
    return _fetch('/watchlist/add', { symbol }, 'POST')
  },

  async removeFromWatchlist(symbol: string) {
    return _fetch('/watchlist/remove', { symbol }, 'POST')
  },

  async search(query: string, limit = 10) {
    return _fetch('/search', { q: query, limit: String(limit) })
  },

  async getAccount() {
    return _fetch('/trading/account')
  },

  async getTradeHistory(limit = 100) {
    return _fetch('/trading/history', { limit: String(limit) })
  },

  async buy(symbol: string, price: number, shares: number, options: {
    name?: string
    market?: string
    stopLoss?: number
    takeProfit?: number
    strategy?: string
  } = {}) {
    const params: Record<string, string> = {
      symbol,
      price: String(price),
      shares: String(shares),
    }
    if (options.name) params.name = options.name
    if (options.market) params.market = options.market
    if (options.stopLoss) params.stop_loss = String(options.stopLoss)
    if (options.takeProfit) params.take_profit = String(options.takeProfit)
    if (options.strategy) params.strategy = options.strategy
    return _fetch('/trading/buy', params, 'POST')
  },

  async sell(symbol: string, price: number, shares?: number, reason = 'manual') {
    const params: Record<string, string> = {
      symbol,
      price: String(price),
      reason,
    }
    if (shares) params.shares = String(shares)
    return _fetch('/trading/sell', params, 'POST')
  },

  async getSystemMetrics() {
    return _fetch('/system/metrics')
  },

  async getAiSummary(symbol: string, period = '1y') {
    return _fetch(`/stock/ai_summary/${symbol}`, { period })
  },

  async getPortfolioEquity(symbols: string, period = '1y') {
    return _fetch('/portfolio/equity', { symbols, period })
  },

  async getConfig(key: string) {
    return _fetch(`/config/${key}`)
  },

  async setConfig(key: string, value: string) {
    return _fetch(`/config/${key}`, { value }, 'POST')
  },

  async getAlerts() {
    return _fetch('/watchlist/alert/list')
  },

  async addAlert(symbol: string, alertType: string, value: number) {
    return _fetch('/watchlist/alert/add', { symbol, alert_type: alertType, value: String(value) }, 'POST')
  },

  async removeAlert(id: string) {
    return _fetch('/watchlist/alert/remove', { id }, 'POST')
  },

  async reorderWatchlist(symbols: string[]) {
    return _fetch('/watchlist/reorder', { symbols: symbols.join(',') }, 'POST')
  },
}
