<template>
  <div class="si-root">
    <header class="si-header">
      <div class="si-header-row">
        <div class="si-header-left">
          <h1 class="si-title">STRATEGY ENCYCLOPEDIA</h1>
          <span class="si-count mono">{{ filteredStrategies.length }} STRATEGIES</span>
        </div>
        <nav class="si-nav">
          <router-link to="/strategy/dashboard" class="si-nav-btn">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="3" y="3" width="18" height="18" rx="2"/><path d="M3 9h18M9 3v18"/></svg>
            DASHBOARD
          </router-link>
          <router-link to="/strategy/run" class="si-nav-btn si-nav-btn-accent">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="5,3 19,12 5,21"/></svg>
            RUN BACKTEST
          </router-link>
        </nav>
      </div>
      <p class="si-subtitle">Explore each strategy's principle, use cases, risks, and parameter descriptions</p>
    </header>

    <div class="si-filter-bar">
      <button
        v-for="cat in categories"
        :key="cat.key"
        class="si-filter-btn"
        :class="{ 'si-filter-active': activeCategory === cat.key }"
        @click="activeCategory = cat.key"
      >
        {{ cat.label }}
        <span v-if="activeCategory === cat.key" class="si-filter-count mono">{{ filteredStrategies.length }}</span>
      </button>
    </div>

    <div class="si-grid">
      <div
        v-for="s in filteredStrategies"
        :key="s.name"
        class="si-card surface-panel"
        @click="selectedStrategy = s"
      >
        <div class="si-card-stripe"></div>
        <div class="si-card-head">
          <span class="si-card-name mono">{{ strategyDisplayName(s.name) }}</span>
          <span class="si-card-diff" :class="'diff-' + s.difficulty">
            {{ difficultyLabel(s.difficulty) }}
          </span>
        </div>
        <p class="si-card-desc">{{ s.description }}</p>
        <div class="si-card-foot">
          <div class="si-card-tags">
            <span class="si-card-tag">{{ categoryLabel(s.category) }}</span>
            <span v-if="s.paramCount" class="si-card-tag mono">{{ s.paramCount }}P</span>
          </div>
          <router-link
            :to="`/strategy/run?strategy=${s.name}`"
            class="si-card-go"
            @click.stop
          >
            BACKTEST →
          </router-link>
        </div>
      </div>
    </div>

    <transition name="fade">
      <div v-if="selectedStrategy" class="si-overlay" @click.self="selectedStrategy = null">
        <div class="si-modal surface-panel">
          <button class="si-modal-close" @click="selectedStrategy = null">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 6L6 18M6 6l12 12"/></svg>
          </button>

          <div class="si-modal-head">
            <h2 class="si-modal-name mono">{{ strategyDisplayName(selectedStrategy.name) }}</h2>
            <span class="si-card-diff" :class="'diff-' + selectedStrategy.difficulty">
              {{ difficultyLabel(selectedStrategy.difficulty) }}
            </span>
          </div>

          <div class="si-modal-body">
            <DataPanel title="PRINCIPLE">
              <p class="si-modal-text">{{ selectedStrategy.principle }}</p>
            </DataPanel>

            <DataPanel title="USE CASES">
              <p class="si-modal-text">{{ selectedStrategy.scenario }}</p>
            </DataPanel>

            <DataPanel title="RISKS">
              <p class="si-modal-text">{{ selectedStrategy.risk }}</p>
            </DataPanel>

            <DataPanel v-if="selectedStrategy.params.length" title="PARAMETERS">
              <div class="si-params">
                <div v-for="p in selectedStrategy.params" :key="p.name" class="si-param">
                  <div class="si-param-head">
                    <span class="si-param-name mono">{{ p.label }}</span>
                    <span class="si-param-range mono">{{ p.min }} → {{ p.max }} <span class="si-param-step">step {{ p.step }}</span></span>
                  </div>
                  <p class="si-param-desc">{{ p.desc }}</p>
                </div>
              </div>
            </DataPanel>

            <div class="si-modal-action">
              <router-link :to="`/strategy/run?strategy=${selectedStrategy.name}`" class="si-nav-btn si-nav-btn-accent">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="5,3 19,12 5,21"/></svg>
                RUN BACKTEST
              </router-link>
            </div>
          </div>
        </div>
      </div>
    </transition>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { createLogger } from '@/composables/useLogger'
import { useRequestCancel } from '@/composables/useRequestCancel'
import { useApiError } from '@/composables/useApiError'
import { api } from '@/api'
import DataPanel from '@/components/ui/DataPanel.vue'
import { strategyDisplayName } from '@/utils/format'
import type { StrategyInfo } from '@/types'

const log = createLogger('StrategyIntro')
const { handleApiError } = useApiError()
const { cancelAll } = useRequestCancel()

interface StrategyDetail {
  name: string
  description: string
  principle: string
  scenario: string
  risk: string
  difficulty: string
  category: string
  paramCount: number
  params: { name: string; label: string; desc: string; min: number; max: number; step: number }[]
}

const activeCategory = ref('all')
const selectedStrategy = ref<StrategyDetail | null>(null)
const rawStrategies = ref<Record<string, StrategyInfo>>({})

const categories = [
  { key: 'all', label: '全部' },
  { key: 'trend', label: '趋势' },
  { key: 'reversal', label: '均值回归' },
  { key: 'breakout', label: '动量' },
  { key: 'advanced', label: '波动率' },
  { key: 'multi_factor', label: '多因子' },
]

const strategyDetails: Record<string, Omit<StrategyDetail, 'name' | 'paramCount' | 'params'>> = {
  DualMAStrategy: {
    description: 'Dual moving average crossover strategy. Golden cross (short MA above long MA) triggers buy; death cross triggers sell.',
    principle: 'Moving averages smooth price data. When the short-term MA crosses above the long-term MA, short-term momentum is increasing and an uptrend may be forming. The core logic is trend-following: enter after trend confirmation, exit before reversal.',
    scenario: 'Best in trending markets (sustained up or down moves). Generates frequent false signals in range-bound markets. Use on daily or higher timeframes with volume confirmation.',
    risk: 'Lagging indicator: signals arrive after price has already moved. In sideways markets, repeated crossovers produce whipsaw losses. Combine with ADX to filter weak trends.',
    difficulty: 'beginner',
    category: 'trend',
  },
  MACDStrategy: {
    description: 'MACD-based strategy using DIF/DEA crossovers, zero-line position, and histogram changes to identify buy/sell timing.',
    principle: 'MACD consists of DIF (fast EMA minus slow EMA), DEA (DIF EMA), and histogram (DIF minus DEA). DIF crossing above DEA above the zero line is a strong buy signal. Histogram turning from green to red indicates weakening bullish momentum.',
    scenario: 'Best for medium-to-long-term trending markets. Unreliable in narrow ranges. Use on daily or weekly timeframes with support/resistance analysis.',
    risk: 'MACD is a lagging indicator; signals may appear after half the move is done. Frequent false signals in choppy markets. Zero-line crossovers are less reliable. Wait for histogram confirmation before entry.',
    difficulty: 'beginner',
    category: 'trend',
  },
  KDJStrategy: {
    description: 'Stochastic oscillator strategy. Uses K/D lines in overbought/oversold zones to capture short-term turning points.',
    principle: 'KDJ measures where the close sits relative to the recent high-low range. K crossing above D in oversold zone (K<20) is a buy signal; K crossing below D in overbought zone (K>80) is a sell signal. J line is most sensitive and can anticipate reversals.',
    scenario: 'Best for short-term trading and range-bound mean reversion. In strong trends, KDJ can stay overbought/oversold for extended periods, causing premature counter-trend entries.',
    risk: 'KDJ "freezes" in strong trends, staying in overbought/oversold zones. Counter-trend signals can cause severe losses. J line is noisy. Only use in confirmed range-bound conditions.',
    difficulty: 'beginner',
    category: 'reversal',
  },
  BollingerBreakoutStrategy: {
    description: 'Bollinger Band squeeze-and-breakout strategy. Narrow bands signal low volatility; breakout direction signals the new trend.',
    principle: 'Bollinger Bands consist of a 20-period SMA middle band and upper/lower bands at 2 standard deviations. When bands contract (squeeze), volatility is low and a large move is imminent. A breakout above the upper band after a squeeze signals bullish expansion.',
    scenario: 'Best for catching breakouts after prolonged consolidation. The longer the squeeze, the larger the expected move. Not suitable when bands are already wide (trend in progress).',
    risk: 'False breakouts are the primary risk: price briefly pierces a band then returns inside. Wait for close confirmation and volume surge. Use the middle band as a stop-loss reference.',
    difficulty: 'intermediate',
    category: 'breakout',
  },
  MomentumStrategy: {
    description: 'Price momentum strategy. Buy when momentum is positive and accelerating; sell when momentum decelerates. "Strong stays strong."',
    principle: 'Momentum = current price / N-period-ago price - 1. Rising momentum indicates accelerating trend; falling momentum (even with price still rising) signals weakening trend. The strategy also computes momentum acceleration (rate of change of momentum) for early reversal detection.',
    scenario: 'Best in early-to-mid trend phases, especially during acceleration. In choppy markets, momentum oscillates and generates false signals. Filter with trend direction.',
    risk: 'Momentum peaks often coincide with trend exhaustion ("buying at the top"). Momentum reversal signals lag, potentially missing optimal exits. Use strict stop-losses and begin reducing position when momentum decelerates, not after it reverses.',
    difficulty: 'intermediate',
    category: 'trend',
  },
  RSIMeanReversionStrategy: {
    description: 'RSI mean-reversion strategy. Buy when RSI exits oversold zone; sell when RSI exits overbought zone. "Extremes revert to mean."',
    principle: 'RSI measures the ratio of upward vs total price change over N periods (range 0-100). RSI<30 = oversold (price dropped too far), RSI>70 = overbought (price rose too far). Buy when RSI crosses back above 30; sell when RSI crosses below 70.',
    scenario: 'Best in range-bound markets and near support/resistance levels. In strong trends, RSI stays overbought/oversold for extended periods, making counter-trend entries dangerous.',
    risk: 'Counter-trend risk: in a strong uptrend, RSI can stay overbought for weeks (selling = missed gains). In a crash, RSI stays oversold (buying = catching falling knives). Only take signals aligned with the higher-timeframe trend.',
    difficulty: 'intermediate',
    category: 'reversal',
  },
  SuperTrendStrategy: {
    description: 'ATR-based trend-following strategy. SuperTrend dynamically adjusts support/resistance using ATR. Price breaking above/below the line triggers signals.',
    principle: 'SuperTrend = (High+Low)/2 +/- N*ATR. When price is above SuperTrend, the market is bullish (green line); when price breaks below, it flips bearish (red line). ATR makes the line adapt to volatility automatically: wider in volatile markets, tighter in calm markets.',
    scenario: 'Best for medium-to-long-term trend following in moderate-volatility environments. Frequent flips in choppy markets. Use on daily or weekly timeframes.',
    risk: 'Frequent whipsaws in sideways markets. ATR parameter sensitivity: too tight = noise, too loose = late signals. Combine with ADX to filter low-trend conditions.',
    difficulty: 'beginner',
    category: 'trend',
  },
  IchimokuCloudStrategy: {
    description: 'Japanese technical analysis system using conversion line, base line, cloud, and lagging span to identify trend, support/resistance, and timing simultaneously.',
    principle: 'Five components: Tenkan-sen (9-period midpoint), Kijun-sen (26-period midpoint), Senkou Span A (Tenkan+Kijun midpoint shifted 26 periods ahead), Senkou Span B (52-period midpoint shifted 26 periods ahead), Chikou Span (close shifted 26 periods back). Price above cloud = bullish; below cloud = bearish. Cloud itself acts as support/resistance.',
    scenario: 'Best for medium-to-long-term trend identification. Cloud support/resistance is reliable on daily and weekly timeframes. Not suitable for short-term trading due to significant lag.',
    risk: 'Fixed parameters (9/26/52) may not suit all instruments or timeframes. Cloud lag means signals arrive late. In choppy markets, price oscillates within the cloud, producing unclear signals. Do not use alone; confirm with other indicators.',
    difficulty: 'advanced',
    category: 'trend',
  },
  TurtleTradingStrategy: {
    description: 'Classic "Turtle Trader" system by Richard Dennis. Breakout entry, trend following, and strict risk management. Textbook trend-following implementation.',
    principle: 'Buy when price breaks above N-day high (breakout entry); sell when it breaks below N-day low. Position size is calculated from ATR (larger position when volatility is low, smaller when high). Risk 1-2% of account per trade. Pyramid adding on profits. Stop-loss at 2 ATR below entry. "Cut losses short, let profits run."',
    scenario: 'Best in liquid, strongly trending markets (commodities, forex). Requires significant capital to endure consecutive losses (10+ losses before catching a big trend). In sideways markets, continuous losses occur, but one large trend can cover many small losses.',
    risk: 'Very low win rate (30-40%). Requires extreme psychological discipline. Drawdowns can reach 30-50%. Strict money management and rule-based execution are mandatory. Not for emotionally unstable traders.',
    difficulty: 'intermediate',
    category: 'trend',
  },
  DualThrustStrategy: {
    description: 'Classic intraday breakout strategy by Michael Chalek. Computes upper/lower rails from prior N-day price ranges. Breakout above upper rail = buy; below lower rail = sell.',
    principle: 'Compute HH (max high), HC (max close), LC (min close), LL (min low) over N days. Range = max(HH-LC, HC-LL). Upper = Open + K1*Range; Lower = Open - K2*Range. K1<K2 biases long; K1>K2 biases short. When price breaks the upper rail, go long; when it breaks the lower rail, go short.',
    scenario: 'Best for intraday trading on volatile, liquid instruments. Not suitable for low-volatility or stagnant instruments. Better suited for futures; A-share T+1 limits intraday effectiveness.',
    risk: 'Intraday strategies are highly sensitive to slippage and commissions. Opening gaps can cause entry prices far from theoretical levels. K1/K2 parameter selection significantly impacts results and is prone to overfitting. Thoroughly test in simulation before live trading.',
    difficulty: 'advanced',
    category: 'breakout',
  },
  MeanReversionProStrategy: {
    description: 'Advanced mean-reversion using Z-score to measure price deviation from the mean. When Z-score exceeds a threshold, price is expected to revert.',
    principle: 'Z-score = (current price - N-period mean) / N-period std dev. Z-score measures how many standard deviations price has deviated from the mean. When Z-score > entry threshold (e.g., 2.0), price is overextended upward (sell); when Z-score < -threshold, price is oversold (buy). Close when Z-score returns near zero. Pro version adds volatility and trend filters to avoid counter-trend trades.',
    scenario: 'Best in range-bound markets and instruments with confirmed mean-reverting statistical properties (e.g., pairs trading, spread trading). In strong trends, price can deviate far and stay deviated.',
    risk: '"Mean reversion" does not guarantee reversion: price can deviate further and for longer than expected. Structural changes (fundamental shifts) can invalidate historical means. Use strict stop-losses; never average down into losses.',
    difficulty: 'advanced',
    category: 'reversal',
  },
  VolatilitySqueezeBreakoutStrategy: {
    description: 'Combines Bollinger Bands and Keltner Channel to detect volatility squeeze. When BB contracts inside KC, a squeeze is active; breakout direction signals the move.',
    principle: 'BB is based on standard deviation; KC is based on ATR. When BB narrows inside KC, volatility is extremely low ("coiling"). When BB re-expands outside KC, the squeeze releases and a directional breakout is likely. Breakout direction is confirmed by momentum indicators.',
    scenario: 'Best for catching large moves after prolonged low-volatility periods. Longer squeezes tend to produce larger releases. Use on daily timeframes. Not suitable for already high-volatility instruments.',
    risk: 'Not all squeezes produce large moves; some release briefly then re-squeeze. Wrong breakout direction leads to losses. Wait for the first strong candle after squeeze release to confirm direction before entry.',
    difficulty: 'intermediate',
    category: 'breakout',
  },
  DonchianChannelStrategy: {
    description: 'Classic channel breakout strategy, prototype of the Turtle system. Buy on N-day high breakout; sell on N-day low breakout. Simple and effective trend-following entry.',
    principle: 'Donchian Channel: upper = N-day high, lower = N-day low, middle = average. Price breaking above the upper channel means bulls have overcome all recent resistance, suggesting trend continuation. Using different periods for entry (e.g., 20-day) and exit (e.g., 10-day) can optimize results.',
    scenario: 'Best in strongly trending markets, particularly commodities and forex. Frequent false breakouts in sideways markets. Use longer periods (20+) to reduce noise.',
    risk: 'False breakouts are the main risk. Channel breakout signals lag; entry price may be far from optimal. Confirm with volume and use reasonable stop-losses.',
    difficulty: 'beginner',
    category: 'breakout',
  },
  ATRChannelBreakoutStrategy: {
    description: 'EMA-centered channel with ATR multiples for width. Breakout above upper channel = buy; below lower channel = sell. ATR channels focus on true volatility range.',
    principle: 'Middle = EMA(N); Upper = EMA + M*ATR; Lower = EMA - M*ATR. ATR captures true range including gaps, making it more practical than standard deviation. Price breaking above the upper channel suggests it has exceeded normal volatility, potentially starting a new trend.',
    scenario: 'Best in markets with variable volatility where ATR auto-adapts. Good in trending markets; many false signals in ranges. Combine with trend direction filters.',
    risk: 'ATR multiplier M significantly impacts results: too small = false breakouts, too large = late signals. In low-volatility periods, narrow channels are easily triggered by normal noise. M values between 1.5-3.0 are typical.',
    difficulty: 'intermediate',
    category: 'breakout',
  },
  FractalBreakoutStrategy: {
    description: 'Bill Williams fractal-based strategy. Identifies local highs/lows (fractals); breakout above fractal high = buy; below fractal low = sell.',
    principle: 'Up fractal = middle bar high is higher than the 2 bars on each side (5-bar pattern). Down fractal is the reverse. Fractals represent "hesitation points" where the market encountered resistance or support. Breaking above an up fractal means bulls overcame prior resistance.',
    scenario: 'Works across all markets and timeframes, especially effective when support/resistance levels are clear. Fractal breakouts confirm that a prior high/low has been breached, making them more meaningful than simple N-day breakouts.',
    risk: 'Many fractals form in choppy markets, leading to frequent breakout failures. Fractal identification requires 5 bars minimum, introducing lag. Confirm with volume and trend indicators.',
    difficulty: 'intermediate',
    category: 'breakout',
  },
  WyckoffAccumulationStrategy: {
    description: 'Wyckoff volume-price analysis strategy. Identifies institutional accumulation phases. Follow smart money direction after accumulation completes.',
    principle: 'Wyckoff accumulation model has 4 phases: A (selling stops), B (sideways accumulation), C (spring/false breakdown test), D (markup begins), E (range breakout). Strategy analyzes price-volume relationships to identify the current phase. Key signals: volume decline after selling climax (A), price-volume divergence in range (B), spring recovery (C), volume breakout (D).',
    scenario: 'Best after prolonged downtrends in bottom areas, identifying when smart money has finished accumulating. Not applicable to instruments already in uptrends. Use weekly timeframes for accumulation identification, daily for breakout confirmation.',
    risk: 'Wyckoff analysis is highly subjective; different traders may interpret the same chart differently. Accumulation can last months or years. "Springs" may be real breakdowns, not false moves. Confirm with fundamental analysis before committing significant capital.',
    difficulty: 'advanced',
    category: 'advanced',
  },
  GARCHVolatilityStrategy: {
    description: 'Uses GARCH (Generalized Autoregressive Conditional Heteroskedasticity) to forecast future volatility. Reduce position when volatility spikes; add when it subsides. Common institutional risk management strategy.',
    principle: 'GARCH models assume volatility clusters: large moves follow large moves, small moves follow small moves. The model predicts next-period volatility from historical squared returns and prior volatility. When predicted volatility exceeds a threshold, reduce exposure or hedge with options.',
    scenario: 'Best for portfolio risk management. Excels around market crises by providing early volatility warnings. Not a return-seeking strategy. Use as a risk overlay alongside other strategies.',
    risk: 'GARCH assumes volatility follows a specific distribution; real markets can produce "black swan" events beyond model predictions. Parameters require periodic re-estimation. Do not rely solely on GARCH; combine with other risk indicators (e.g., VIX).',
    difficulty: 'advanced',
    category: 'advanced',
  },
  AdaptiveEngine: {
    description: 'Automatically selects the optimal strategy combination based on current market regime (trending/ranging/high-vol/low-vol). No manual strategy selection required.',
    principle: 'The engine first detects the current market state using multiple indicators (ADX, ATR, volatility, etc.), then selects the best-suited strategy from the library. Trend markets get trend-following strategies; range markets get mean-reversion strategies; high volatility triggers position reduction. The engine continuously monitors regime changes and dynamically switches strategies.',
    scenario: 'Suitable for all market environments as an "all-weather" strategy. Especially useful for traders unsure of the current market state. However, regime-switching has inherent lag and may not adapt quickly enough in rapidly changing markets.',
    risk: 'Incorrect market state classification leads to inappropriate strategy selection. Strategy switching has costs (may require closing and reopening positions). Validate the engine classification accuracy in backtests and implement switching cooldown periods to avoid rapid toggling.',
    difficulty: 'beginner',
    category: 'advanced',
  },
  MultiFactorConfluenceStrategy: {
    description: 'Multi-factor confluence strategy combining trend, momentum, volume, and volatility signals for high-conviction entries.',
    principle: 'Aggregates signals from multiple independent factors (MA trend, RSI momentum, volume confirmation, ATR volatility regime). Only triggers when a minimum number of factors align, reducing false signals at the cost of fewer trades.',
    scenario: 'Best when multiple market dimensions align simultaneously. Fewer trades but higher quality signals. Works across all timeframes.',
    risk: 'Over-filtering can eliminate valid signals. Factor correlation may reduce diversification benefit. Requires careful factor selection and weighting.',
    difficulty: 'advanced',
    category: 'multi_factor',
  },
  KaufmanAdaptiveStrategy: {
    description: 'Kaufman Adaptive Moving Average strategy. Uses Efficiency Ratio to adapt between trending and ranging modes automatically.',
    principle: 'ER = |direction| / volatility measures trend efficiency (0=range, 1=trend). Fast SC in trends, slow SC in ranges. The adaptive smoothing constant blends fast and slow EMA speeds based on ER, creating a self-adjusting moving average.',
    scenario: 'Best in markets that alternate between trending and ranging phases. The adaptive nature reduces whipsaws in ranges while maintaining responsiveness in trends.',
    risk: 'ER calculation uses fixed lookback which may not match actual regime duration. Extreme ER values near 0 or 1 can cause over-sensitivity or excessive lag.',
    difficulty: 'intermediate',
    category: 'trend',
  },
}

const allStrategies = computed<StrategyDetail[]>(() => {
  const result: StrategyDetail[] = []
  for (const [name, info] of Object.entries(rawStrategies.value)) {
    const detail = strategyDetails[name]
    if (!detail) continue
    const params = Object.entries(info.param_space || {}).map(([pName, range]) => ({
      name: pName,
      label: paramLabel(pName),
      desc: paramDesc(pName),
      min: range.min,
      max: range.max,
      step: range.step,
    }))
    result.push({
      name,
      ...detail,
      paramCount: params.length,
      params,
    })
  }
  return result
})

const filteredStrategies = computed(() => {
  if (activeCategory.value === 'all') return allStrategies.value
  return allStrategies.value.filter(s => s.category === activeCategory.value)
})

function difficultyLabel(d: string): string {
  const map: Record<string, string> = { beginner: 'BASIC', intermediate: 'PRO', advanced: 'EXPERT' }
  return map[d] || d.toUpperCase()
}

function categoryLabel(c: string): string {
  const map: Record<string, string> = {
    trend: '趋势', reversal: '均值回归', breakout: '动量',
    advanced: '波动率', multi_factor: '多因子',
  }
  return map[c] || c.toUpperCase()
}

function paramLabel(name: string): string {
  const map: Record<string, string> = {
    period: 'Period', accel_period: 'Accel Period', window: 'Window',
    entry_z: 'Entry Z-Score', bb_period: 'BB Period', kc_mult: 'KC Multiplier',
    tenkan_period: 'Tenkan Period', kijun_period: 'Kijun Period',
    vwap_window: 'VWAP Window', sigma_mult: 'Sigma Multiplier',
    ofi_window: 'OFI Window', lookback: 'Lookback',
    min_bars: 'Min Bars', illiq_window: 'Illiquidity Window',
    corr_window: 'Correlation Window', entry_window: 'Entry Window',
    exit_window: 'Exit Window', k1: 'K1 Upper', k2: 'K2 Lower',
    ema_period: 'EMA Period', atr_mult: 'ATR Multiplier',
    upper_period: 'Upper Period', lower_period: 'Lower Period',
    atr_period: 'ATR Period', atr_mult_first: 'ATR First Mult',
    vol_ma_window: 'Vol MA Window', entry_sigma: 'Entry Sigma',
    er_period: 'ER Period', er_threshold: 'ER Threshold',
    vol_lookback: 'Vol Lookback', vol_surge_threshold: 'Vol Surge Threshold',
    short_period: 'Short Period', mid_period: 'Mid Period',
  }
  return map[name] || name
}

function paramDesc(name: string): string {
  const map: Record<string, string> = {
    period: 'Lookback period for momentum calculation; shorter = more sensitive but noisier',
    accel_period: 'Period for momentum acceleration; used to anticipate trend reversals',
    window: 'Statistical window for calculations; affects MA and std dev sensitivity',
    entry_z: 'Z-score entry threshold; higher = fewer but more reliable signals',
    lookback: 'Number of bars to look back for fractal identification or indicator computation',
    entry_window: 'Lookback period for breakout entry signals',
    exit_window: 'Lookback period for breakout exit signals',
    k1: 'Upper rail coefficient; smaller = easier to trigger long signals',
    k2: 'Lower rail coefficient; smaller = easier to trigger short signals',
    atr_mult: 'ATR multiplier determining channel width',
    ema_period: 'EMA period for the center line',
  }
  return map[name] || 'Adjusting this parameter affects strategy sensitivity and signal frequency'
}

onMounted(async () => {
  try {
    rawStrategies.value = await api.backtest.strategies()
  } catch (err) {
    handleApiError(err, '加载策略列表失败')
  }
})

onUnmounted(cancelAll)
</script>

<style scoped>
.si-root {
  max-width: 1200px;
  margin: 0 auto;
  display: grid;
  gap: var(--u4);
}

.si-header {
  display: flex;
  flex-direction: column;
  gap: var(--u2);
}

.si-header-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: var(--u4);
}

.si-header-left {
  display: flex;
  align-items: baseline;
  gap: var(--u3);
}

.si-title {
  font-family: var(--font-mono);
  font-size: var(--fs-xl);
  font-weight: 700;
  color: var(--text-primary);
  letter-spacing: -0.02em;
}

.si-count {
  font-size: var(--fs-xs);
  color: var(--text-tertiary);
  letter-spacing: 0.06em;
}

.si-nav {
  display: flex;
  gap: var(--u2);
}

.si-nav-btn {
  display: inline-flex;
  align-items: center;
  gap: var(--u2);
  padding: var(--u2) var(--u4);
  font-family: var(--font-mono);
  font-size: var(--fs-xs);
  font-weight: 500;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  border: 1px solid var(--border-mid);
  border-radius: var(--r-md);
  background: var(--bg-overlay);
  color: var(--text-secondary);
  transition: all var(--dur-fast) var(--ease-mechanical);
  text-decoration: none;
}

.si-nav-btn:hover {
  border-color: var(--accent);
  color: var(--text-primary);
  text-decoration: none;
}

.si-nav-btn-accent {
  background: var(--accent);
  border-color: var(--accent);
  color: #fff;
}

.si-nav-btn-accent:hover {
  filter: brightness(1.15);
  border-color: var(--accent);
  color: #fff;
}

.si-subtitle {
  font-size: var(--fs-sm);
  color: var(--text-tertiary);
  font-family: var(--font-mono);
  letter-spacing: 0.02em;
}

.si-filter-bar {
  display: flex;
  gap: 0;
  border-bottom: 1px solid var(--border-hair);
}

.si-filter-btn {
  padding: var(--u2) var(--u4);
  font-family: var(--font-mono);
  font-size: var(--fs-xs);
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--text-tertiary);
  border-bottom: 2px solid transparent;
  background: none;
  cursor: pointer;
  transition: all var(--dur-fast) var(--ease-mechanical);
  display: inline-flex;
  align-items: center;
  gap: var(--u2);
}

.si-filter-btn:hover {
  color: var(--text-secondary);
}

.si-filter-active {
  color: var(--accent);
  border-bottom-color: var(--accent);
}

.si-filter-count {
  font-size: var(--fs-2xs);
  color: var(--accent);
  background: var(--accent-muted);
  padding: 0 var(--u1);
  border-radius: var(--r-xs);
}

.si-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
  gap: var(--u4);
}

.si-card {
  display: flex;
  flex-direction: column;
  gap: var(--u3);
  padding: var(--u5);
  border-radius: var(--r-md);
  cursor: pointer;
  position: relative;
  overflow: hidden;
  transition: border-color var(--dur-fast) var(--ease-mechanical),
              transform var(--dur-fast) var(--ease-mechanical);
}

.si-card-stripe {
  position: absolute;
  inset: 0;
  background: repeating-linear-gradient(
    45deg,
    transparent,
    transparent 8px,
    rgba(41, 121, 255, 0.04) 8px,
    rgba(41, 121, 255, 0.04) 9px
  );
  opacity: 0;
  transition: opacity var(--dur-normal) var(--ease-mechanical);
  pointer-events: none;
}

.si-card:hover {
  border-color: var(--accent);
  transform: translateY(-1px);
}

.si-card:hover .si-card-stripe {
  opacity: 1;
}

.si-card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--u2);
}

.si-card-name {
  font-size: var(--fs-md);
  font-weight: 600;
  color: var(--text-primary);
  letter-spacing: -0.01em;
}

.si-card-diff {
  font-size: var(--fs-3xs);
  font-family: var(--font-mono);
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  padding: 2px 8px;
  border-radius: var(--r-xs);
  flex-shrink: 0;
}

.si-card-diff.diff-beginner {
  background: var(--fall-bg);
  color: var(--fall);
}

.si-card-diff.diff-intermediate {
  background: var(--warn-bg);
  color: var(--warn);
}

.si-card-diff.diff-advanced {
  background: var(--rise-bg);
  color: var(--rise);
}

.si-card-desc {
  font-size: var(--fs-sm);
  color: var(--text-secondary);
  line-height: 1.6;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
  flex: 1;
}

.si-card-foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--u2);
}

.si-card-tags {
  display: flex;
  gap: var(--u2);
}

.si-card-tag {
  font-size: var(--fs-3xs);
  font-family: var(--font-mono);
  text-transform: uppercase;
  letter-spacing: 0.08em;
  padding: 1px 6px;
  background: var(--bg-raised);
  border-radius: var(--r-xs);
  color: var(--text-tertiary);
}

.si-card-go {
  font-family: var(--font-mono);
  font-size: var(--fs-2xs);
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--accent);
  text-decoration: none;
  padding: var(--u1) var(--u3);
  border: 1px solid var(--border-accent);
  border-radius: var(--r-md);
  transition: all var(--dur-fast) var(--ease-mechanical);
}

.si-card-go:hover {
  background: var(--accent-muted);
  border-color: var(--accent);
  text-decoration: none;
}

.si-overlay {
  position: fixed;
  inset: 0;
  background: rgba(5, 5, 7, 0.8);
  z-index: 1000;
  display: flex;
  align-items: center;
  justify-content: center;
  backdrop-filter: blur(6px);
}

.si-modal {
  width: 680px;
  max-width: 95vw;
  max-height: 85vh;
  overflow-y: auto;
  position: relative;
}

.si-modal-close {
  position: absolute;
  top: var(--u4);
  right: var(--u4);
  background: none;
  border: none;
  color: var(--text-tertiary);
  cursor: pointer;
  padding: var(--u1);
  z-index: 1;
  transition: color var(--dur-fast) var(--ease-mechanical);
}

.si-modal-close:hover {
  color: var(--text-primary);
}

.si-modal-head {
  display: flex;
  align-items: center;
  gap: var(--u4);
  padding: var(--u6);
  border-bottom: 1px solid var(--border-hair);
  position: sticky;
  top: 0;
  background: var(--bg-surface);
  z-index: 2;
}

.si-modal-name {
  font-size: var(--fs-xl);
  font-weight: 700;
  color: var(--text-primary);
  letter-spacing: -0.02em;
}

.si-modal-body {
  padding: var(--u6);
  display: flex;
  flex-direction: column;
  gap: var(--u4);
}

.si-modal-text {
  font-size: var(--fs-sm);
  color: var(--text-secondary);
  line-height: 1.7;
}

.si-params {
  display: flex;
  flex-direction: column;
  gap: var(--u3);
}

.si-param {
  background: var(--bg-plate);
  padding: var(--u4);
  border-radius: var(--r-md);
  border-left: 2px solid var(--accent);
}

.si-param-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 2px;
}

.si-param-name {
  font-size: var(--fs-sm);
  font-weight: 500;
  color: var(--text-primary);
}

.si-param-range {
  font-size: var(--fs-xs);
  color: var(--text-muted);
}

.si-param-step {
  color: var(--text-tertiary);
}

.si-param-desc {
  font-size: var(--fs-xs);
  color: var(--text-tertiary);
  line-height: 1.5;
}

.si-modal-action {
  padding-top: var(--u4);
  border-top: 1px solid var(--border-hair);
}

@media (max-width: 768px) {
  .si-grid {
    grid-template-columns: 1fr;
  }

  .si-header-row {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
