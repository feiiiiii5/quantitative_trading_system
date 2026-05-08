export interface ApiResponse<T = unknown> {
  success: boolean
  data: T
  error: string
}

export interface StockQuote {
  symbol: string
  market: string
  name: string
  price: number
  last_close: number
  open: number
  high: number
  low: number
  volume: number
  amount: number
  change: number
  change_pct: number
  turnover_rate: number
  timestamp: number
  pe?: number
  pb?: number
  total_market_cap?: number
}

export interface KlineBar {
  symbol: string
  market: string
  kline_type: string
  adjust: string
  date: string
  open: number
  high: number
  low: number
  close: number
  volume: number
  amount: number
  turnover_rate: number
}

export interface MarketOverview {
  cn_indices: Record<string, IndexQuote>
  hk_indices: Record<string, IndexQuote>
  us_indices: Record<string, IndexQuote>
}

export interface IndexQuote {
  name: string
  price: number
  change_pct: number
  change: number
}

export interface MarketStatus {
  is_open: boolean
  session: string
  reason: string | null
  next_open: string | null
  current_time: string
  timezone: string
}

export interface HeatmapItem {
  name: string
  change_pct: number
  amount: number
  value: number
  leader: string
}

export interface AnomalyItem {
  symbol: string
  name: string
  price: number
  change_pct: number
  volume_ratio: number
  reason: string
}

export interface NorthboundData {
  sh_buy: number
  sh_sell: number
  sz_buy: number
  sz_sell: number
  total_net: number
  sh_inflow: number
  sz_inflow: number
  net_inflow: number
  top_stocks: unknown[]
}

export interface SignalItem {
  id?: number
  symbol?: string
  name?: string
  type?: string
  strategy?: string
  time?: string
  date?: string
  price?: number
  signals?: StrategySignal[]
}

export interface StrategySignal {
  strategy: string
  signal: string
  confidence: number
  reason: string
}

export interface TrendAnalysis {
  direction: string
  strength: number
  duration_days: number
  key_levels: {
    support: number[]
    resistance: number[]
  }
}

export interface DeepAnalysis {
  trend: TrendAnalysis
  momentum: {
    rsi_signal: string
    macd_signal: string
    kdj_signal: string
    composite_momentum: number
  }
  volume: {
    trend: string
    obv_divergence: boolean
    volume_ratio_5d: number
  }
  patterns: unknown[]
  ichimoku: Record<string, unknown>
  fibonacci_levels: { ratio: number; price: number }[]
  composite_score: number
  signal: string
  signal_confidence: number
  last_price: number
}

export interface PredictionData {
  symbol: string
  last_price: number
  predictions: Record<string, PredictionItem>
  composite_signal: string
  composite_confidence: number
  trend_score: number
  technical_signal: string
  volatility_annual: number
}

export interface PredictionItem {
  price: number
  upper: number
  lower: number
  confidence: number
  direction: string
}

export interface AiSummary {
  symbol: string
  overall: string
  points: string[]
  price_change: {
    '5d': number
    '20d': number
    '60d': number
  }
  generated_at: number
}

export interface Fundamentals {
  pe_ttm?: number
  pb?: number
  roe?: number
  eps?: number
  revenue_yoy?: number
  profit_yoy?: number
  debt_ratio?: number
  name?: string
  price?: number
  market_cap?: number
  source?: string
}

export interface CorrelationData {
  rolling_correlation: { date: string; value: number }[]
  beta: number
  alpha: number
  relative_strength: number
  stability_score: number
  related?: { symbol: string; name: string; coefficient: number }[]
}

export interface DepthLevel {
  price: number
  quantity: number
}

export interface OrderDepth {
  bids: DepthLevel[]
  asks: DepthLevel[]
}

export interface FactorAnalysis {
  factors: Record<string, FactorItem>
  composite_score: number
}

export interface FactorItem {
  value: number
  percentile: number
  direction: string
}

export interface StrategyInfo {
  name: string
  type: string
  param_space: Record<string, ParamRange>
  description?: string
  category?: string
  difficulty?: string
}

export interface ParamRange {
  min: number
  max: number
  step: number
}

export interface BacktestResult {
  strategy_name: string
  total_return: number
  annual_return: number
  sharpe_ratio: number
  max_drawdown: number
  win_rate: number
  profit_factor: number
  total_trades: number
  win_trades?: number
  loss_trades?: number
  avg_profit?: number
  avg_loss?: number
  avg_hold_days?: number
  benchmark_return?: number
  alpha?: number
  beta?: number
  sortino_ratio?: number
  calmar_ratio?: number
  omega_ratio?: number
  tail_ratio?: number
  information_ratio?: number
  cvar_95?: number
  var_95?: number
  annual_volatility?: number
  volatility?: number
  downside_deviation?: number
  max_consecutive_losses?: number
  equity_curve?: { date: string; value: number }[]
  benchmark_curve?: { date: string; value: number }[]
  trades?: TradeRecord[]
  monte_carlo?: Record<string, unknown>
  sensitivity?: unknown[]
  walk_forward?: Record<string, unknown>
}

export interface TradeRecord {
  entry_date?: string
  exit_date?: string
  entry_price?: number
  exit_price?: number
  shares?: number
  pnl?: number
  pnl_pct?: number
  direction?: string
  reason?: string
  action?: string
  price?: number
  amount?: number
  fee?: number
  date?: string
  hold_days?: number
  bar_index?: number
}

export interface AccountInfo {
  total_assets: number
  cash: number
  market_value: number
  total_profit: number
  initial_capital: number
  return_pct: number
  positions: PositionInfo[]
  position_count: number
  risk_report: RiskReport
}

export interface PositionInfo {
  symbol: string
  name: string
  market: string
  shares: number
  avg_cost: number
  current_price: number
  market_value: number
  profit: number
  profit_pct: number
  weight: number
  stop_loss: number
  take_profit: number
  strategy: string
  entry_date: string
}

export interface RiskReport {
  max_concentration: number
  current_daily_pnl: number
  daily_loss_limit: number
  circuit_breaker_active: boolean
  circuit_breaker_time: string | null
  var: number
}

export interface PortfolioRisk {
  symbols: string[]
  correlation_matrix: Record<string, Record<string, number>>
  portfolio_var_95: number
  portfolio_cvar_95: number
  portfolio_volatility: number
  portfolio_sharpe: number
  risk_contribution: Record<string, number>
}

export interface PortfolioEquity {
  symbols: string[]
  weights: Record<string, number>
  equity_curve: { date: string; equity: number }[]
  cumulative_return: number
  max_drawdown: number
  annual_return: number
  annual_volatility: number
  sharpe_ratio: number
}

export interface WatchlistData {
  symbols: string[]
  quotes: Record<string, StockQuote>
}

export interface PriceAlert {
  id: string | number
  symbol: string
  name?: string
  alert_type: string
  value: number
  target_price?: number
  direction?: string
  enabled?: boolean
  triggered: boolean
  trigger_price?: number | null
  trigger_time?: string | null
  created_at: string
  updated_at?: string
}

export interface SearchItem {
  symbol: string
  code: string
  name: string
  market: string
  sector: string
  priority: number
}

export interface SystemMetrics {
  uptime_seconds: number
  memory_mb: number
  cpu_percent: number
  threads: number
  api_requests_total: number
  avg_response_time_ms: number
  ws_connections: number
  cache_size: number
}

export interface WeeklyReport {
  report_date: string
  market_summary: Record<string, { price: number; change_pct: number }>
  sector_performance: {
    top_gainers: { name: string; change_pct: number }[]
    top_losers: { name: string; change_pct: number }[]
  }
  northbound_flow: NorthboundData | null
}

export interface MarketStock {
  symbol: string
  name: string
  price: number
  change_pct: number
  change?: number
  volume: number
  amount: number
  turnover_rate: number
  market?: string
  industry?: string
  pe?: number
  pb?: number
  total_market_cap?: number
}

export interface NewsItem {
  title: string
  source: string
  url: string
  time: string
  content: string
  sentiment: number
  sentiment_label: string
  related_symbols: string[]
}

export interface MarketSentimentData {
  sentiment: {
    fear_greed_index: number
    label: string
    news_sentiment: number
    volume_sentiment: number
    momentum_sentiment: number
    breadth_sentiment: number
    timestamp: number
  }
  summary: {
    total: number
    bullish: number
    bearish: number
    neutral: number
    hot_symbols: { symbol: string; count: number }[]
  }
}

export interface ScreenerPreset {
  id: string
  name: string
  description: string
  category: string
  conditions: { field: string; operator: string; value: number | number[]; label: string }[]
}

export interface ScreenerResult {
  total: number
  stocks: MarketStock[]
}

export interface CapitalFlowData {
  symbol: string
  realtime: CapitalFlowRealtime | null
  history: CapitalFlowHistory[]
  pattern?: FlowPattern
}

export interface CapitalFlowRealtime {
  symbol: string
  name: string
  price: number
  change_pct: number
  main_net_inflow: number
  main_inflow: number
  main_outflow: number
  super_large_net: number
  large_net: number
  medium_net: number
  small_net: number
  main_pct: number
}

export interface CapitalFlowHistory {
  date: string
  main_inflow: number
  main_outflow: number
  main_net_inflow: number
  super_large_net: number
  large_net: number
  medium_net: number
  small_net: number
}

export interface FlowPattern {
  pattern: string
  trend: string
  total_main_net: number
  avg_main_net: number
  max_inflow: number
  max_outflow: number
}

export interface SectorFlowItem {
  name: string
  change_pct: number
  main_net_inflow: number
  main_inflow: number
  main_outflow: number
  code: string
}

export interface ChipData {
  symbol: string
  current_price: number
  avg_cost: number
  profit_ratio: number
  concentration: number
  support_price: number
  resistance_price: number
  peak_price: number
  prices: number[]
  distribution: number[]
  chip_bands: { range: string; price_low: number; price_high: number; weight: number }[]
  fire: ChipFireData
}

export interface ChipFireData {
  status: string
  signal?: string
  short_concentration?: number
  mid_concentration?: number
  long_concentration?: number
  avg_cost_short?: number
  avg_cost_mid?: number
  avg_cost_long?: number
  profit_ratio?: number
  support?: number
  resistance?: number
}

export interface SectorStrengthItem {
  code: string
  name: string
  change_pct: number
  change: number
  amount: number
  turnover_rate: number
  main_net_inflow: number
  up_count: number
  down_count: number
  leading_stock: string
  leading_change: number
  momentum_score: number
  rank: number
}

export interface SectorRotationData {
  snapshot: {
    timestamp: number
    top_sectors: { name: string; change_pct: number; momentum_score: number }[]
    bottom_sectors: { name: string; change_pct: number; momentum_score: number }[]
  }
  trend: { timestamp: number; top_sectors: { name: string; change_pct: number; momentum_score: number }[]; bottom_sectors: { name: string; change_pct: number; momentum_score: number }[] }[]
  signals: { type: string; sector: string; change_pct?: number; signal: string }[]
}

export interface SectorDetail {
  sector: SectorStrengthItem | null
  stocks: { symbol: string; name: string; price: number; change_pct: number; change: number; turnover_rate: number; high: number; low: number; main_net_inflow: number }[]
}

export interface BacktestHistoryItem {
  id?: string
  symbol: string
  strategy_type: string
  strategy_name?: string
  total_return?: number
  annual_return?: number
  sharpe_ratio?: number
  max_drawdown?: number
  win_rate?: number
  result: BacktestResult
  created_at?: string
}

export interface MonteCarloResult {
  ruin_prob: number
  paths: number[][]
  percentiles?: { p5: number[]; p50: number[]; p95: number[] }
  avg_final_value?: number
  median_return?: number
  p5_return?: number
  p95_return?: number
}

export interface SensitivityItem {
  param: string
  value: number
  sharpe_ratio: number
  total_return: number
  max_drawdown: number
  min?: number
  max?: number
  impact?: number
}

export interface StrategyRecommendation {
  analysis: {
    regime?: string
    trend?: number
    volatility?: number
    adx?: number
    rsi?: number
  }
  recommendations: {
    strategy: string
    strategy_class: string
    score: number
    reasons: string[]
  }[]
  strategy?: string
  strategy_class?: string
  score?: number
  reasons?: string[]
}

export interface LimitUpItem {
  symbol: string
  name: string
  price: number
  change_pct: number
  volume: number
  amount: number
  first_limit_up_time?: string
  last_limit_up_time?: string
  limit_up_count?: number
  industry?: string
}

export interface DragonTigerItem {
  symbol: string
  name: string
  date: string
  reason: string
  buy_departments: { name: string; buy_amount: number; sell_amount: number; net_amount: number }[]
  sell_departments: { name: string; buy_amount: number; sell_amount: number; net_amount: number }[]
  net_buy_amount: number
}

export interface PortfolioAttribution {
  total_return: number
  benchmark_return: number
  alpha: number
  beta: number
  sector_attribution: { sector: string; contribution: number; weight: number }[]
  stock_attribution: { symbol: string; name: string; contribution: number; weight: number }[]
}

export interface TradeResult {
  success: boolean
  order_id: string
  symbol: string
  name?: string
  price: number
  shares: number
  amount: number
  commission: number
  timestamp: number
  message?: string
}

export interface StrategyPerformanceItem {
  strategy: string
  total_return: number
  annual_return: number
  sharpe_ratio: number
  max_drawdown: number
  win_rate: number
  profit_factor: number
  trade_count: number
}

export interface PerformanceOverview {
  symbol: string
  period: string
  data_points: number
  benchmark: { name: string; total_return: number; sharpe_ratio: number }
  best_strategy: StrategyPerformanceItem | null
  average_return: number
  average_sharpe: number
  strategy_count: number
  strategies: StrategyPerformanceItem[]
}

export interface MarketEvent {
  type: 'limit_up' | 'limit_down' | 'volume_spike'
  symbol: string
  name: string
  change_pct: number
  price: number
  volume?: number
  volume_ratio?: number
  timestamp: number
}
