export function formatNumber(n: number, digits = 2): string {
  if (n == null || isNaN(n)) return '-'
  if (Math.abs(n) >= 1e8) return (n / 1e8).toFixed(digits) + '亿'
  if (Math.abs(n) >= 1e4) return (n / 1e4).toFixed(digits) + '万'
  return n.toFixed(digits)
}

export function formatVolume(v: number): string {
  if (v == null || isNaN(v)) return '-'
  if (v >= 1e8) return (v / 1e8).toFixed(2) + '亿'
  if (v >= 1e4) return (v / 1e4).toFixed(0) + '万'
  return v.toFixed(0)
}

export function formatAmount(a: number): string {
  if (a == null || isNaN(a)) return '-'
  if (a >= 1e12) return (a / 1e12).toFixed(2) + '万亿'
  if (a >= 1e8) return (a / 1e8).toFixed(2) + '亿'
  if (a >= 1e4) return (a / 1e4).toFixed(0) + '万'
  return a.toFixed(0)
}

export function formatPct(p: number, digits = 2): string {
  if (p == null || isNaN(p)) return '-'
  return (p >= 0 ? '+' : '') + p.toFixed(digits) + '%'
}

export function formatPrice(p: number): string {
  if (p == null || isNaN(p)) return '-'
  if (p >= 10000) return p.toFixed(2)
  if (p >= 100) return p.toFixed(2)
  return p.toFixed(2)
}

export function formatDate(d: string | number | Date): string {
  if (!d) return '-'
  const date = new Date(d)
  if (isNaN(date.getTime())) return String(d).slice(0, 10)
  const y = date.getFullYear()
  const m = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

export function formatTime(d: string | number | Date): string {
  if (!d) return '-'
  const date = new Date(d)
  if (isNaN(date.getTime())) return '-'
  const h = String(date.getHours()).padStart(2, '0')
  const m = String(date.getMinutes()).padStart(2, '0')
  return `${h}:${m}`
}

export function changeClass(pct: number): string {
  if (pct > 0) return 'text-rise'
  if (pct < 0) return 'text-fall'
  return 'text-secondary'
}

export function changeBg(pct: number): string {
  if (pct > 0) return 'bg-rise'
  if (pct < 0) return 'bg-fall'
  return ''
}

export function debounce<T extends (...args: unknown[]) => unknown>(fn: T, delay: number): T {
  let timer: ReturnType<typeof setTimeout>
  return ((...args: unknown[]) => {
    clearTimeout(timer)
    timer = setTimeout(() => fn(...args), delay)
  }) as T
}

export function throttle<T extends (...args: unknown[]) => unknown>(fn: T, interval: number): T {
  let last = 0
  return ((...args: unknown[]) => {
    const now = Date.now()
    if (now - last >= interval) {
      last = now
      fn(...args)
    }
  }) as T
}

export function getMarketLabel(market: string): string {
  const map: Record<string, string> = { A: 'A股', HK: '港股', US: '美股' }
  return map[market] || market
}

export function signalColor(signal: string): string {
  if (signal === 'buy' || signal === 'bullish') return 'var(--rise)'
  if (signal === 'sell' || signal === 'bearish') return 'var(--fall)'
  return 'var(--text-secondary)'
}

export function signalLabel(signal: string): string {
  const map: Record<string, string> = {
    buy: '买入', sell: '卖出', hold: '持有', neutral: '中性',
    bullish: '看多', bearish: '看空', overbought: '超买', oversold: '超卖',
  }
  return map[signal] || signal
}

export function strategyDisplayName(name: string): string {
  const map: Record<string, string> = {
    DualMAStrategy: '双均线策略',
    MACDStrategy: 'MACD策略',
    KDJStrategy: 'KDJ策略',
    BollingerBreakoutStrategy: '布林带突破策略',
    MomentumStrategy: '动量策略',
    MultiFactorConfluenceStrategy: '多因子共振策略',
    AdaptiveTrendFollowingStrategy: '自适应趋势跟踪策略',
    MeanReversionProStrategy: '均值回归Pro策略',
    VolatilitySqueezeBreakoutStrategy: '波动率收缩突破策略',
    RSIMeanReversionStrategy: 'RSI均值回归策略',
    SuperTrendStrategy: '超级趋势策略',
    IchimokuCloudStrategy: '一目均衡策略',
    VWAPDeviationStrategy: 'VWAP偏离策略',
    OrderFlowImbalanceStrategy: '订单流失衡策略',
    RegimeSwitchingStrategy: '市场状态切换策略',
    FractalBreakoutStrategy: '分形突破策略',
    WyckoffAccumulationStrategy: '威科夫吸筹策略',
    ElliottWaveAIStrategy: '艾略特波浪AI策略',
    MarketMicrostructureStrategy: '市场微观结构策略',
    CopulaCorrelationStrategy: 'Copula相关性策略',
    QuantileRegressionStrategy: '分位数回归策略',
    TurtleTradingStrategy: '海龟交易策略',
    DualThrustStrategy: 'Dual Thrust策略',
    ATRChannelBreakoutStrategy: 'ATR通道突破策略',
    DonchianChannelStrategy: '唐奇安通道策略',
    ChandeKrollStopStrategy: 'Chande-Kroll止损策略',
    VolumeWeightedMACDStrategy: '成交量加权MACD策略',
    OrnsteinUhlenbeckStrategy: 'OU过程均值回归策略',
    KaufmanAdaptiveStrategy: '考夫曼自适应策略',
    GARCHVolatilityStrategy: 'GARCH波动率策略',
    MultiTimeframeMomentumStrategy: '多时间框架动量策略',
    AdaptiveEngine: '自适应量化引擎',
  }
  return map[name] || name
}
