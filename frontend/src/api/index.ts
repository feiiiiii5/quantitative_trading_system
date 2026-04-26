const BASE = '/api'

async function request(url: string, options?: RequestInit) {
  const res = await fetch(`${BASE}${url}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  const json = await res.json()
  if (json.success) return json.data
  throw new Error(json.error || 'Request failed')
}

export const api = {
  search: (q: string, limit = 10, market?: string) =>
    request(`/search?q=${encodeURIComponent(q)}&limit=${limit}${market ? `&market=${market}` : ''}`),

  getRealtime: (symbol: string) =>
    request(`/realtime?symbol=${encodeURIComponent(symbol)}`),

  getKline: (symbol: string, period = 'daily', limit = 500) =>
    request(`/kline?symbol=${encodeURIComponent(symbol)}&period=${period}&limit=${limit}`),

  getMarketOverview: () => request('/market/overview'),
  getMarketHot: (limit = 20) => request(`/market/hot?limit=${limit}`),
  getMarketTemperature: () => request('/market/temperature'),
  getMarketNorthbound: (limit = 30) => request(`/market/northbound?limit=${limit}`),
  getMarketSectors: () => request('/market/sectors'),
  getMarketList: (params: Record<string, any>) => {
    const qs = new URLSearchParams(params).toString()
    return request(`/market/list?${qs}`)
  },
  getMarketIndices: () => request('/market/indices'),

  getStockInfo: (symbol: string) =>
    request(`/stock/info?symbol=${encodeURIComponent(symbol)}`),
  getStockFinancial: (symbol: string) =>
    request(`/stock/financial?symbol=${encodeURIComponent(symbol)}`),
  getStockIndicators: (symbol: string, period = 'daily', limit = 500) =>
    request(`/stock/indicators?symbol=${encodeURIComponent(symbol)}&period=${period}&limit=${limit}`),

  getIndustries: () => request('/industries'),

  getStrategyList: () => request('/strategy/list'),
  runBacktest: (params: Record<string, any>) =>
    request('/strategy/backtest', { method: 'POST', body: JSON.stringify(params) }),
  getStrategySignals: (symbol: string, strategy: string, params?: string) =>
    request(`/strategy/signals?symbol=${encodeURIComponent(symbol)}&strategy_name=${strategy}${params ? `&params=${encodeURIComponent(params)}` : ''}`),

  getPortfolioSummary: () => request('/portfolio/summary'),
  getPortfolioPositions: () => request('/portfolio/positions'),
  getPortfolioTrades: (symbol?: string, limit = 100) =>
    request(`/portfolio/trades?${symbol ? `symbol=${symbol}&` : ''}limit=${limit}`),
  buyStock: (symbol: string, quantity: number, price: number) =>
    request('/portfolio/buy', { method: 'POST', body: JSON.stringify({ symbol, quantity, price }) }),
  sellStock: (symbol: string, quantity: number, price: number) =>
    request('/portfolio/sell', { method: 'POST', body: JSON.stringify({ symbol, quantity, price }) }),
  resetPortfolio: () =>
    request('/portfolio/reset', { method: 'POST' }),

  getWatchlist: () => request('/watchlist'),
  addToWatchlist: (symbol: string) =>
    request('/watchlist/add', { method: 'POST', body: JSON.stringify({ symbol }) }),
  removeFromWatchlist: (symbol: string) =>
    request('/watchlist/remove', { method: 'POST', body: JSON.stringify({ symbol }) }),
}

export default api
