<template>
  <div class="stock-detail">
    <div class="page-header">
      <button class="back-btn" @click="$router.back()">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M15 19l-7-7 7-7"/></svg>
      </button>
      <div class="header-info">
        <h1 class="page-title">{{ stockInfo.symbol }}</h1>
        <span class="stock-name">{{ stockInfo.name }}</span>
        <span class="stock-market" v-if="stockInfo.market">{{ stockInfo.market }}</span>
      </div>
      <div class="header-actions">
        <button class="action-btn" @click="toggleWatchlist" :class="{ active: isInWatchlist }">
          <svg width="16" height="16" viewBox="0 0 24 24" :fill="isInWatchlist ? 'var(--accent-yellow)' : 'none'" :stroke="isInWatchlist ? 'var(--accent-yellow)' : 'currentColor'" stroke-width="2"><path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/></svg>
        </button>
      </div>
    </div>

    <div class="price-bar" :class="{ up: stockInfo.change_pct >= 0, down: stockInfo.change_pct < 0 }">
      <div class="price-main">
        <span class="price">{{ (stockInfo.price || 0).toFixed(2) }}</span>
        <span class="price-pct">{{ stockInfo.change_pct >= 0 ? '+' : '' }}{{ (stockInfo.change_pct || 0).toFixed(2) }}%</span>
        <span class="price-change">{{ stockInfo.change >= 0 ? '+' : '' }}{{ (stockInfo.change || 0).toFixed(2) }}</span>
      </div>
      <div class="price-meta">
        <span>开 {{ (stockInfo.open || 0).toFixed(2) }}</span>
        <span>高 {{ (stockInfo.high || 0).toFixed(2) }}</span>
        <span>低 {{ (stockInfo.low || 0).toFixed(2) }}</span>
        <span>昨收 {{ (stockInfo.prev_close || 0).toFixed(2) }}</span>
        <span>量 {{ fmtVol(stockInfo.volume) }}</span>
        <span>额 {{ fmtVol(stockInfo.amount || 0) }}</span>
        <span>换手 {{ (stockInfo.turnover_rate || 0).toFixed(2) }}%</span>
        <span>振幅 {{ (stockInfo.amplitude || 0).toFixed(2) }}%</span>
      </div>
    </div>

    <div class="tab-bar">
      <button v-for="t in tabs" :key="t.key" class="tab-btn" :class="{ active: activeTab === t.key }" @click="activeTab = t.key">{{ t.label }}</button>
    </div>

    <div class="tab-content">
      <div v-show="activeTab === 'kline'" class="kline-section">
        <div class="kline-toolbar">
          <div class="toolbar-left">
            <button v-for="p in periodOptions" :key="p.value" class="tool-btn" :class="{ active: klinePeriod === p.value }" @click="changePeriod(p.value)">{{ p.label }}</button>
            <span class="tool-divider"></span>
            <button v-for="a in adjustOptions" :key="a.value" class="tool-btn" :class="{ active: klineAdjust === a.value }" @click="changeAdjust(a.value)">{{ a.label }}</button>
          </div>
          <div class="toolbar-right">
            <button v-for="ov in overlayOptions" :key="ov.key" class="tool-btn" :class="{ active: overlays[ov.key] }" @click="toggleOverlay(ov.key)">{{ ov.label }}</button>
            <span class="tool-divider"></span>
            <select v-model="subIndicator" class="tool-select" @change="renderKline">
              <option value="macd">MACD</option>
              <option value="kdj">KDJ</option>
              <option value="rsi">RSI</option>
            </select>
          </div>
        </div>
        <div ref="klineChartRef" class="kline-chart"></div>
      </div>

      <div v-show="activeTab === 'indicators'" class="indicators-section">
        <div v-if="indicatorsData" class="indicator-panels">
          <div class="ind-panel" v-if="indicatorsData.trend">
            <h3 class="ind-title">趋势类</h3>
            <div class="ind-grid">
              <div class="ind-item"><span class="ind-label">MA5</span><span class="ind-value">{{ fmtInd(indicatorsData.trend.ma5) }}</span></div>
              <div class="ind-item"><span class="ind-label">MA10</span><span class="ind-value">{{ fmtInd(indicatorsData.trend.ma10) }}</span></div>
              <div class="ind-item"><span class="ind-label">MA20</span><span class="ind-value">{{ fmtInd(indicatorsData.trend.ma20) }}</span></div>
              <div class="ind-item"><span class="ind-label">MA60</span><span class="ind-value">{{ fmtInd(indicatorsData.trend.ma60) }}</span></div>
              <div class="ind-item"><span class="ind-label">MACD信号</span><span class="ind-value" :class="indicatorsData.trend.macd_signal">{{ indicatorsData.trend.macd_signal || '-' }}</span></div>
              <div class="ind-item"><span class="ind-label">SuperTrend</span><span class="ind-value" :class="indicatorsData.trend.supertrend_dir">{{ indicatorsData.trend.supertrend_dir || '-' }}</span></div>
            </div>
          </div>
          <div class="ind-panel" v-if="indicatorsData.oscillator">
            <h3 class="ind-title">震荡类</h3>
            <div class="ind-grid">
              <div class="ind-item"><span class="ind-label">RSI(6)</span><span class="ind-value">{{ fmtInd(indicatorsData.oscillator.rsi6) }}</span></div>
              <div class="ind-item"><span class="ind-label">RSI(12)</span><span class="ind-value">{{ fmtInd(indicatorsData.oscillator.rsi12) }}</span></div>
              <div class="ind-item"><span class="ind-label">RSI(24)</span><span class="ind-value">{{ fmtInd(indicatorsData.oscillator.rsi24) }}</span></div>
              <div class="ind-item"><span class="ind-label">K</span><span class="ind-value">{{ fmtInd(indicatorsData.oscillator.k) }}</span></div>
              <div class="ind-item"><span class="ind-label">D</span><span class="ind-value">{{ fmtInd(indicatorsData.oscillator.d) }}</span></div>
              <div class="ind-item"><span class="ind-label">J</span><span class="ind-value">{{ fmtInd(indicatorsData.oscillator.j) }}</span></div>
            </div>
          </div>
          <div class="ind-panel" v-if="indicatorsData.volume_ind">
            <h3 class="ind-title">成交量</h3>
            <div class="ind-grid">
              <div class="ind-item"><span class="ind-label">OBV趋势</span><span class="ind-value">{{ indicatorsData.volume_ind.obv_trend || '-' }}</span></div>
              <div class="ind-item"><span class="ind-label">CMF</span><span class="ind-value">{{ fmtInd(indicatorsData.volume_ind.cmf) }}</span></div>
              <div class="ind-item"><span class="ind-label">量比</span><span class="ind-value">{{ fmtInd(indicatorsData.volume_ind.volume_ratio) }}</span></div>
            </div>
          </div>
          <div class="ind-panel" v-if="indicatorsData.volatility">
            <h3 class="ind-title">波动率</h3>
            <div class="ind-grid">
              <div class="ind-item"><span class="ind-label">ATR</span><span class="ind-value">{{ fmtInd(indicatorsData.volatility.atr) }}</span></div>
              <div class="ind-item"><span class="ind-label">BOLL宽度</span><span class="ind-value">{{ fmtInd(indicatorsData.volatility.boll_width) }}</span></div>
              <div class="ind-item"><span class="ind-label">历史波动率</span><span class="ind-value">{{ fmtInd(indicatorsData.volatility.hist_vol) }}</span></div>
            </div>
          </div>
          <div class="ind-panel composite-panel" v-if="analysis">
            <h3 class="ind-title">综合评分</h3>
            <div ref="radarChartRef" class="radar-chart"></div>
          </div>
        </div>
        <div v-else class="empty-state-small">加载中...</div>
      </div>

      <div v-show="activeTab === 'analysis'" class="analysis-section">
        <div v-if="analysis" class="analysis-grid">
          <div class="analysis-card">
            <h3>趋势分析</h3>
            <div class="analysis-item"><span class="label">方向</span><span class="value" :class="analysis.trend?.direction">{{ trendLabel }}</span></div>
            <div class="analysis-item"><span class="label">强度</span><span class="value">{{ (analysis.trend?.strength || 0).toFixed(1) }}</span></div>
            <div class="analysis-item" v-if="analysis.trend?.key_levels"><span class="label">支撑位</span><span class="value">{{ (analysis.trend.key_levels.support || []).slice(0, 3).map((s: any) => typeof s === 'number' ? s.toFixed(2) : s).join(', ') }}</span></div>
            <div class="analysis-item" v-if="analysis.trend?.key_levels"><span class="label">阻力位</span><span class="value">{{ (analysis.trend.key_levels.resistance || []).slice(0, 3).map((s: any) => typeof s === 'number' ? s.toFixed(2) : s).join(', ') }}</span></div>
          </div>
          <div class="analysis-card">
            <h3>动量指标</h3>
            <div class="analysis-item"><span class="label">RSI信号</span><span class="value" :class="analysis.momentum?.rsi_signal">{{ analysis.momentum?.rsi_signal || '-' }}</span></div>
            <div class="analysis-item"><span class="label">MACD信号</span><span class="value" :class="analysis.momentum?.macd_signal">{{ analysis.momentum?.macd_signal || '-' }}</span></div>
            <div class="analysis-item"><span class="label">KDJ信号</span><span class="value" :class="analysis.momentum?.kdj_signal">{{ analysis.momentum?.kdj_signal || '-' }}</span></div>
            <div class="analysis-item"><span class="label">综合动量</span><span class="value">{{ (analysis.momentum?.composite_momentum || 0).toFixed(4) }}</span></div>
          </div>
          <div class="analysis-card">
            <h3>量价分析</h3>
            <div class="analysis-item"><span class="label">量能趋势</span><span class="value">{{ analysis.volume?.trend || '-' }}</span></div>
            <div class="analysis-item"><span class="label">5日量比</span><span class="value">{{ (analysis.volume?.volume_ratio_5d || 0).toFixed(2) }}</span></div>
          </div>
          <div class="analysis-card composite-card">
            <h3>综合评分</h3>
            <div class="composite-score">
              <span class="score-value" :class="analysis.signal === 'bullish' ? 'up' : analysis.signal === 'bearish' ? 'down' : ''">{{ (analysis.composite_score || 0).toFixed(1) }}</span>
              <span class="score-signal">{{ analysis.signal || 'neutral' }}</span>
              <span class="score-conf">置信度 {{ (analysis.signal_confidence || 0).toFixed(0) }}%</span>
            </div>
          </div>
        </div>
        <div v-else class="empty-state-small">加载中...</div>
      </div>

      <div v-show="activeTab === 'prediction'" class="prediction-section">
        <div v-if="prediction" class="pred-grid">
          <div v-for="(pred, key) in prediction.predictions || {}" :key="key" class="pred-card" :class="pred.direction">
            <span class="pred-label">{{ key.toUpperCase() }}</span>
            <span class="pred-price">{{ pred.price }}</span>
            <span class="pred-range">{{ pred.lower }} - {{ pred.upper }}</span>
            <span class="pred-conf">置信度 {{ (pred.confidence * 100).toFixed(0) }}%</span>
          </div>
          <div class="pred-summary">
            <span class="pred-signal" :class="prediction.composite_signal">{{ prediction.composite_signal }}</span>
            <span class="pred-vol">年化波动率: {{ ((prediction.volatility_annual || 0) * 100).toFixed(1) }}%</span>
          </div>
        </div>
        <div v-else class="empty-state-small">加载中...</div>
      </div>

      <div v-show="activeTab === 'ai_summary'" class="ai-summary-section">
        <div v-if="aiSummaryLoading" class="skeleton" style="height:200px;border-radius:12px"></div>
        <div v-else-if="aiSummary" class="ai-summary-card">
          <div class="ai-overall" :class="aiSummary.overall === '偏多' ? 'bullish' : aiSummary.overall === '偏空' ? 'bearish' : 'neutral'">
            <span class="overall-label">综合判断</span>
            <span class="overall-value">{{ aiSummary.overall }}</span>
          </div>
          <div class="ai-points">
            <div v-for="(point, idx) in aiSummary.points" :key="idx" class="ai-point" :class="pointClass(point)">
              <span class="point-dot"></span>
              <span class="point-text">{{ point }}</span>
            </div>
          </div>
          <div v-if="aiSummary.price_change" class="ai-changes">
            <div class="change-item"><span class="change-label">5日</span><span class="change-value" :class="aiSummary.price_change['5d'] >= 0 ? 'up' : 'down'">{{ aiSummary.price_change['5d'] >= 0 ? '+' : '' }}{{ aiSummary.price_change['5d'] }}%</span></div>
            <div class="change-item"><span class="change-label">20日</span><span class="change-value" :class="aiSummary.price_change['20d'] >= 0 ? 'up' : 'down'">{{ aiSummary.price_change['20d'] >= 0 ? '+' : '' }}{{ aiSummary.price_change['20d'] }}%</span></div>
            <div class="change-item"><span class="change-label">60日</span><span class="change-value" :class="aiSummary.price_change['60d'] >= 0 ? 'up' : 'down'">{{ aiSummary.price_change['60d'] >= 0 ? '+' : '' }}{{ aiSummary.price_change['60d'] }}%</span></div>
          </div>
        </div>
        <div v-else class="empty-state"><p>暂无AI分析数据</p></div>
      </div>

      <div v-show="activeTab === 'fundamentals'" class="fundamentals-section">
        <div v-if="fundamentalsData" class="fund-grid">
          <div class="fund-card">
            <h3>估值指标</h3>
            <div class="fund-item" v-if="fundamentalsData.pe_ttm"><span class="label">PE(TTM)</span><span class="value">{{ fundamentalsData.pe_ttm?.toFixed(2) || '-' }}</span></div>
            <div class="fund-item" v-if="fundamentalsData.pb"><span class="label">PB</span><span class="value">{{ fundamentalsData.pb?.toFixed(2) || '-' }}</span></div>
            <div class="fund-item" v-if="fundamentalsData.ps_ttm"><span class="label">PS(TTM)</span><span class="value">{{ fundamentalsData.ps_ttm?.toFixed(2) || '-' }}</span></div>
            <div class="fund-item" v-if="fundamentalsData.dv_ratio"><span class="label">股息率</span><span class="value">{{ (fundamentalsData.dv_ratio || 0).toFixed(2) }}%</span></div>
          </div>
          <div class="fund-card">
            <h3>财务指标</h3>
            <div class="fund-item" v-if="fundamentalsData.total_market_cap"><span class="label">总市值</span><span class="value">{{ fmtVol(fundamentalsData.total_market_cap) }}</span></div>
            <div class="fund-item" v-if="fundamentalsData.circulating_market_cap"><span class="label">流通市值</span><span class="value">{{ fmtVol(fundamentalsData.circulating_market_cap) }}</span></div>
            <div class="fund-item" v-if="fundamentalsData.roe"><span class="label">ROE</span><span class="value">{{ (fundamentalsData.roe || 0).toFixed(2) }}%</span></div>
            <div class="fund-item" v-if="fundamentalsData.gross_profit_margin"><span class="label">毛利率</span><span class="value">{{ (fundamentalsData.gross_profit_margin || 0).toFixed(2) }}%</span></div>
            <div class="fund-item" v-if="fundamentalsData.net_profit_margin"><span class="label">净利率</span><span class="value">{{ (fundamentalsData.net_profit_margin || 0).toFixed(2) }}%</span></div>
          </div>
          <div class="fund-card" v-if="fundamentalsData.revenue_growth || fundamentalsData.profit_growth">
            <h3>成长性</h3>
            <div class="fund-item" v-if="fundamentalsData.revenue_growth"><span class="label">营收增速</span><span class="value" :class="fundamentalsData.revenue_growth >= 0 ? 'up' : 'down'">{{ (fundamentalsData.revenue_growth || 0).toFixed(2) }}%</span></div>
            <div class="fund-item" v-if="fundamentalsData.profit_growth"><span class="label">利润增速</span><span class="value" :class="fundamentalsData.profit_growth >= 0 ? 'up' : 'down'">{{ (fundamentalsData.profit_growth || 0).toFixed(2) }}%</span></div>
          </div>
        </div>
        <div v-else class="empty-state-small">加载中...</div>
      </div>

      <div v-show="activeTab === 'correlation'" class="correlation-section">
        <div v-if="correlationData" class="corr-grid">
          <div class="corr-card">
            <h3>与基准相关性</h3>
            <div class="corr-item"><span class="label">Beta</span><span class="value">{{ (correlationData.beta || 0).toFixed(4) }}</span></div>
            <div class="corr-item"><span class="label">Alpha</span><span class="value" :class="correlationData.alpha >= 0 ? 'up' : 'down'">{{ (correlationData.alpha || 0).toFixed(4) }}</span></div>
            <div class="corr-item"><span class="label">相对强度</span><span class="value" :class="correlationData.relative_strength >= 0 ? 'up' : 'down'">{{ ((correlationData.relative_strength || 0) * 100).toFixed(2) }}%</span></div>
            <div class="corr-item"><span class="label">稳定性评分</span><span class="value">{{ (correlationData.stability_score || 0).toFixed(2) }}</span></div>
          </div>
          <div class="corr-chart-card" v-if="correlationData.rolling_correlation?.length">
            <h3>滚动相关性(60日)</h3>
            <BaseChart :option="correlationChartOption" height="220px" />
          </div>
        </div>
        <div v-else class="empty-state-small">加载中...</div>
      </div>

      <div v-show="activeTab === 'factors'" class="factors-section">
        <div v-if="factorData" class="factor-grid">
          <div class="factor-score-card">
            <h3>综合因子评分</h3>
            <div class="factor-composite">
              <span class="composite-value" :class="factorData.composite_score > 0 ? 'up' : factorData.composite_score < 0 ? 'down' : ''">{{ (factorData.composite_score || 0).toFixed(4) }}</span>
            </div>
          </div>
          <div v-for="(f, name) in factorData.factors || {}" :key="name" class="factor-card" :class="f.direction">
            <div class="factor-name">{{ factorLabel(name) }}</div>
            <div class="factor-value">{{ (f.value || 0).toFixed(4) }}</div>
            <div class="factor-bar-wrap">
              <div class="factor-bar" :style="{ width: (f.percentile * 100).toFixed(1) + '%', background: f.direction === 'bullish' ? 'var(--accent-red)' : f.direction === 'bearish' ? 'var(--accent-green)' : 'var(--text-tertiary)' }"></div>
            </div>
            <div class="factor-meta">
              <span class="factor-pct">百分位 {{ (f.percentile * 100).toFixed(1) }}%</span>
              <span class="factor-dir" :class="f.direction">{{ f.direction === 'bullish' ? '看多' : f.direction === 'bearish' ? '看空' : '中性' }}</span>
            </div>
          </div>
        </div>
        <div v-else class="empty-state-small">加载中...</div>
      </div>

      <div v-show="activeTab === 'backtest'" class="quick-backtest-section">
        <div class="qb-config">
          <div class="qb-row">
            <label>策略</label>
            <select v-model="qbStrategy" class="form-input">
              <option value="adaptive">自适应引擎</option>
              <option value="dual_ma">双均线</option>
              <option value="macd">MACD</option>
              <option value="bollinger_breakout">布林突破</option>
              <option value="ichimoku">一目均衡</option>
            </select>
          </div>
          <div class="qb-row">
            <label>时间</label>
            <div class="qb-quick-btns">
              <button v-for="q in qbQuickRanges" :key="q.value" class="qb-btn" :class="{ active: qbRange === q.value }" @click="qbRange = q.value">{{ q.label }}</button>
            </div>
          </div>
          <button class="btn-run-qb" @click="runQuickBacktest" :disabled="qbRunning">{{ qbRunning ? '运行中...' : '快速回测' }}</button>
        </div>
        <div v-if="qbResult" class="qb-result">
          <div class="qb-metrics">
            <MetricCard label="总收益" :value="pct(qbResult.total_return)" :positive="qbResult.total_return >= 0 ? 'up' : 'down'" />
            <MetricCard label="最大回撤" :value="pct(qbResult.max_drawdown)" positive="down" />
            <MetricCard label="夏普" :value="(qbResult.sharpe_ratio || 0).toFixed(2)" positive="neutral" />
            <MetricCard label="胜率" :value="pct(qbResult.win_rate)" positive="neutral" />
          </div>
          <div v-if="qbResult.equity_curve" class="qb-chart">
            <BaseChart :option="qbEquityOption" height="200px" />
          </div>
        </div>
      </div>

      <div v-show="activeTab === 'trade'" class="trade-section">
        <div class="trade-form">
          <div class="form-row">
            <label>价格</label>
            <input v-model.number="orderPrice" type="number" :placeholder="(stockInfo.price || 0).toFixed(2)" class="form-input" />
          </div>
          <div class="form-row">
            <label>数量(股)</label>
            <input v-model.number="orderShares" type="number" placeholder="100" class="form-input" step="100" />
          </div>
          <div class="trade-estimate">
            <span>预估金额: ¥{{ ((orderPrice || stockInfo.price || 0) * (orderShares || 100)).toLocaleString() }}</span>
            <span>手续费: ¥{{ ((orderPrice || stockInfo.price || 0) * (orderShares || 100) * 0.0003).toFixed(2) }}</span>
          </div>
          <div class="form-row" v-if="t1Restricted">
            <div class="t1-warning">T+1限制：今日买入的股票不能当日卖出</div>
          </div>
          <div class="form-row collapse-panel">
            <button class="collapse-toggle" @click="showAdvancedTrade = !showAdvancedTrade">
              止损/止盈 {{ showAdvancedTrade ? '▲' : '▼' }}
            </button>
            <div v-if="showAdvancedTrade" class="collapse-content">
              <div class="form-row">
                <label>止损价</label>
                <input v-model.number="stopLoss" type="number" placeholder="0" class="form-input" />
              </div>
              <div class="form-row">
                <label>止盈价</label>
                <input v-model.number="takeProfit" type="number" placeholder="0" class="form-input" />
              </div>
            </div>
          </div>
          <div class="trade-btns">
            <button class="btn-buy" @click="submitOrder('buy')">买入</button>
            <button class="btn-sell" @click="submitOrder('sell')" :disabled="t1Restricted">卖出</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'
import { useRoute } from 'vue-router'
import { api } from '../api'
import echarts from '../lib/echarts'
import { MetricCard, BaseChart } from '../components'

const route = useRoute()
const stockInfo = ref<any>({})
const analysis = ref<any>(null)
const prediction = ref<any>(null)
const aiSummary = ref<any>(null)
const aiSummaryLoading = ref(false)
const fundamentalsData = ref<any>(null)
const correlationData = ref<any>(null)
const factorData = ref<any>(null)
const indicatorsData = ref<any>(null)
const isInWatchlist = ref(false)
const t1Restricted = ref(false)
const showAdvancedTrade = ref(false)
const stopLoss = ref(0)
const takeProfit = ref(0)

function pointClass(point: string): string {
  if (/强势|上涨|向好|买入/.test(point)) return 'bullish'
  if (/承压|下跌|风险|卖出/.test(point)) return 'bearish'
  return 'neutral'
}

function factorLabel(name: string): string {
  const map: Record<string, string> = {
    momentum_quality: '动量质量',
    efficiency_ratio: '效率比率',
    relative_volume: '相对成交量',
    money_flow_index: '资金流量指数',
    volume_price_trend: '量价趋势',
  }
  return map[name] || name
}

const correlationChartOption = computed(() => {
  if (!correlationData.value?.rolling_correlation?.length) return {}
  const rc = correlationData.value.rolling_correlation
  const dates = rc.map((d: any) => (d.date || '').slice(5))
  const values = rc.map((d: any) => d.value)
  return {
    backgroundColor: 'transparent', animation: false,
    tooltip: { trigger: 'axis', formatter: (p: any) => p[0] ? `${p[0].axisValue}<br/>相关性: ${p[0].value.toFixed(4)}` : '' },
    grid: { left: 50, right: 20, top: 10, bottom: 30 },
    xAxis: { type: 'category', data: dates, axisLabel: { color: '#888', fontSize: 9 } },
    yAxis: { type: 'value', min: -1, max: 1, axisLabel: { color: '#888', fontSize: 9 }, splitLine: { lineStyle: { color: 'rgba(255,255,255,0.04)' } } },
    series: [{ type: 'line', data: values, showSymbol: false, lineStyle: { width: 1.5, color: '#4d9fff' }, areaStyle: { color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: 'rgba(77,159,255,0.15)' }, { offset: 1, color: 'rgba(77,159,255,0)' }] } } }],
  }
})

const orderPrice = ref(0)
const orderShares = ref(100)
const activeTab = ref('kline')
const klinePeriod = ref('1y')
const klineAdjust = ref('qfq')
const subIndicator = ref('macd')
const klineChartRef = ref<HTMLElement | null>(null)
const radarChartRef = ref<HTMLElement | null>(null)
let chartInstance: any = null
let radarChart: any = null
let klineData: any[] = []

const overlays = ref({ ma: true, boll: false, vwap: false })

const tabs = [
  { key: 'kline', label: 'K线图' },
  { key: 'indicators', label: '技术指标' },
  { key: 'analysis', label: '深度分析' },
  { key: 'fundamentals', label: '基本面' },
  { key: 'correlation', label: '相关性' },
  { key: 'factors', label: '因子分析' },
  { key: 'prediction', label: 'AI预测' },
  { key: 'ai_summary', label: 'AI摘要' },
  { key: 'backtest', label: '快速回测' },
  { key: 'trade', label: '交易' },
]

const periodOptions = [
  { value: '3m', label: '3月' },
  { value: '6m', label: '6月' },
  { value: '1y', label: '1年' },
  { value: '3y', label: '3年' },
  { value: '5y', label: '5年' },
]
const adjustOptions = [
  { value: '', label: '不复权' },
  { value: 'qfq', label: '前复权' },
  { value: 'hfq', label: '后复权' },
]
const overlayOptions = [
  { key: 'ma', label: 'MA' },
  { key: 'boll', label: 'BOLL' },
  { key: 'vwap', label: 'VWAP' },
]

const qbStrategy = ref('adaptive')
const qbRange = ref('1y')
const qbRunning = ref(false)
const qbResult = ref<any>(null)
const qbQuickRanges = [
  { value: '1m', label: '1月' },
  { value: '3m', label: '3月' },
  { value: '6m', label: '6月' },
  { value: '1y', label: '1年' },
  { value: '3y', label: '3年' },
]

const trendLabel = computed(() => {
  const d = analysis.value?.trend?.direction
  if (d === 'up') return '上涨'
  if (d === 'down') return '下跌'
  return '震荡'
})

function fmtVol(v: number): string {
  if (!v) return '-'
  if (v >= 1e8) return (v / 1e8).toFixed(1) + '亿'
  if (v >= 1e4) return (v / 1e4).toFixed(1) + '万'
  return String(Math.round(v))
}

function fmtInd(v: any): string {
  if (v === undefined || v === null) return '-'
  return typeof v === 'number' ? v.toFixed(2) : String(v)
}

function pct(v: number): string {
  if (v === undefined || v === null) return '0.00%'
  return (v >= 0 ? '+' : '') + (v * 100).toFixed(2) + '%'
}

function changePeriod(p: string) {
  klinePeriod.value = p
  loadKline()
}

function changeAdjust(a: string) {
  klineAdjust.value = a
  loadKline()
}

function toggleOverlay(key: string) {
  overlays.value[key] = !overlays.value[key]
  renderKline()
}

async function toggleWatchlist() {
  const symbol = route.params.code as string
  if (isInWatchlist.value) {
    await api.removeFromWatchlist(symbol)
    isInWatchlist.value = false
  } else {
    await api.addToWatchlist(symbol)
    isInWatchlist.value = true
  }
}

async function loadStockData() {
  const symbol = route.params.code as string
  const info = await api.getRealtime(symbol)
  if (info) stockInfo.value = info
  orderPrice.value = stockInfo.value.price || 0
}

async function loadKline() {
  const symbol = route.params.code as string
  const ktype = klinePeriod.value === '3m' || klinePeriod.value === '6m' || klinePeriod.value === '1y' ? 'daily' : 'daily'
  const data = await api.getHistory(symbol, klinePeriod.value, ktype, klineAdjust.value)
  if (!data || !data.length) return
  klineData = data
  renderKline()
}

function calcMA(data: any[], period: number): (number | null)[] {
  const result: (number | null)[] = []
  for (let i = 0; i < data.length; i++) {
    if (i < period - 1) { result.push(null); continue }
    let sum = 0
    for (let j = 0; j < period; j++) sum += data[i - j].close
    result.push(+(sum / period).toFixed(2))
  }
  return result
}

function calcBOLL(data: any[], period: number = 20, mult: number = 2): { mid: (number|null)[], upper: (number|null)[], lower: (number|null)[] } {
  const mid = calcMA(data, period)
  const upper: (number|null)[] = []
  const lower: (number|null)[] = []
  for (let i = 0; i < data.length; i++) {
    if (mid[i] === null) { upper.push(null); lower.push(null); continue }
    let sumSq = 0
    for (let j = 0; j < period; j++) sumSq += Math.pow(data[i - j].close - (mid[i] as number), 2)
    const std = Math.sqrt(sumSq / period)
    upper.push(+((mid[i] as number) + mult * std).toFixed(2))
    lower.push(+((mid[i] as number) - mult * std).toFixed(2))
  }
  return { mid, upper, lower }
}

function calcVWAP(data: any[]): (number | null)[] {
  const result: (number | null)[] = []
  let cumVP = 0, cumV = 0
  for (let i = 0; i < data.length; i++) {
    const tp = (data[i].high + data[i].low + data[i].close) / 3
    const v = data[i].volume || 1
    cumVP += tp * v
    cumV += v
    result.push(+(cumVP / cumV).toFixed(2))
  }
  return result
}

function calcMACD(data: any[]): { dif: number[], dea: number[], hist: number[] } {
  const close = data.map(d => d.close)
  const ema12: number[] = [close[0]]
  const ema26: number[] = [close[0]]
  const dif: number[] = []
  const dea: number[] = [0]
  const hist: number[] = [0]
  for (let i = 1; i < close.length; i++) {
    ema12.push(ema12[i-1] * 11/13 + close[i] * 2/13)
    ema26.push(ema26[i-1] * 25/27 + close[i] * 2/27)
    dif.push(+(ema12[i] - ema26[i]).toFixed(4))
    dea.push(+(dea[i-1] * 8/10 + dif[dif.length-1] * 2/10).toFixed(4))
    hist.push(+(2 * (dif[dif.length-1] - dea[dea.length-1])).toFixed(4))
  }
  if (dif.length === 0) return { dif: [0], dea: [0], hist: [0] }
  dif.unshift(0)
  return { dif, dea, hist }
}

function calcKDJ(data: any[], n = 9, m1 = 3, m2 = 3): { k: number[], d: number[], j: number[] } {
  const close = data.map(d => d.close)
  const high = data.map(d => d.high)
  const low = data.map(d => d.low)
  const kArr: number[] = [50]
  const dArr: number[] = [50]
  const jArr: number[] = [50]
  for (let i = 1; i < close.length; i++) {
    const start = Math.max(0, i - n + 1)
    let hn = high[i], ln = low[i]
    for (let j = start; j < i; j++) {
      if (high[j] > hn) hn = high[j]
      if (low[j] < ln) ln = low[j]
    }
    const rsv = hn - ln > 0 ? (close[i] - ln) / (hn - ln) * 100 : 50
    const k = (m1 - 1) / m1 * kArr[i - 1] + rsv / m1
    const d = (m2 - 1) / m2 * dArr[i - 1] + k / m2
    const j = 3 * k - 2 * d
    kArr.push(+k.toFixed(2))
    dArr.push(+d.toFixed(2))
    jArr.push(+j.toFixed(2))
  }
  return { k: kArr, d: dArr, j: jArr }
}

function calcRSI(data: any[], periods = [6, 12, 24]): { rsi6: number[], rsi12: number[], rsi24: number[] } {
  const close = data.map(d => d.close)
  const result: Record<number, number[]> = {}
  for (const p of periods) {
    const arr: number[] = [50]
    let avgGain = 0, avgLoss = 0
    for (let i = 1; i < close.length; i++) {
      const change = close[i] - close[i - 1]
      const gain = change > 0 ? change : 0
      const loss = change < 0 ? -change : 0
      if (i <= p) {
        avgGain += gain
        avgLoss += loss
        if (i === p) {
          avgGain /= p
          avgLoss /= p
          const rsi = avgLoss > 0 ? 100 - 100 / (1 + avgGain / avgLoss) : 100
          arr.push(+rsi.toFixed(2))
        } else {
          arr.push(50)
        }
      } else {
        avgGain = (avgGain * (p - 1) + gain) / p
        avgLoss = (avgLoss * (p - 1) + loss) / p
        const rsi = avgLoss > 0 ? 100 - 100 / (1 + avgGain / avgLoss) : 100
        arr.push(+rsi.toFixed(2))
      }
    }
    result[p] = arr
  }
  return { rsi6: result[6] || [], rsi12: result[12] || [], rsi24: result[24] || [] }
}

function renderKline() {
  if (!klineChartRef.value || !klineData.length) return
  if (!chartInstance) {
    chartInstance = echarts.init(klineChartRef.value, undefined, { renderer: 'canvas' })
  }
  const data = klineData
  const dates = data.map((d: any) => (d.date || '').slice(0, 10))
  const ohlc = data.map((d: any) => [d.open, d.close, d.low, d.high])
  const volumes = data.map((d: any) => d.volume || 0)
  const changes = data.map((d: any) => d.close >= d.open ? 1 : -1)

  const series: any[] = [
    {
      name: 'K线', type: 'candlestick', data: ohlc, xAxisIndex: 0, yAxisIndex: 0,
      itemStyle: { color: '#f43f5e', color0: '#34d399', borderColor: '#f43f5e', borderColor0: '#34d399' },
    },
    {
      name: '成交量', type: 'bar', data: volumes.map((v: number, i: number) => ({
        value: v,
        itemStyle: { color: changes[i] > 0 ? 'rgba(244,63,94,0.5)' : 'rgba(52,211,153,0.5)' },
      })), xAxisIndex: 1, yAxisIndex: 1,
    },
  ]

  if (overlays.value.ma) {
    const ma5 = calcMA(data, 5)
    const ma10 = calcMA(data, 10)
    const ma20 = calcMA(data, 20)
    const ma60 = calcMA(data, 60)
    series.push(
      { name: 'MA5', type: 'line', data: ma5, xAxisIndex: 0, yAxisIndex: 0, smooth: true, showSymbol: false, lineStyle: { width: 1, color: '#fbbf24' } },
      { name: 'MA10', type: 'line', data: ma10, xAxisIndex: 0, yAxisIndex: 0, smooth: true, showSymbol: false, lineStyle: { width: 1, color: '#4d9fff' } },
      { name: 'MA20', type: 'line', data: ma20, xAxisIndex: 0, yAxisIndex: 0, smooth: true, showSymbol: false, lineStyle: { width: 1, color: '#a78bfa' } },
      { name: 'MA60', type: 'line', data: ma60, xAxisIndex: 0, yAxisIndex: 0, smooth: true, showSymbol: false, lineStyle: { width: 1, color: '#fb923c' } },
    )
  }

  if (overlays.value.boll) {
    const boll = calcBOLL(data)
    series.push(
      { name: 'BOLL上', type: 'line', data: boll.upper, xAxisIndex: 0, yAxisIndex: 0, smooth: true, showSymbol: false, lineStyle: { width: 1, color: 'rgba(167,139,250,0.6)', type: 'dashed' } },
      { name: 'BOLL中', type: 'line', data: boll.mid, xAxisIndex: 0, yAxisIndex: 0, smooth: true, showSymbol: false, lineStyle: { width: 1, color: 'rgba(167,139,250,0.8)' } },
      { name: 'BOLL下', type: 'line', data: boll.lower, xAxisIndex: 0, yAxisIndex: 0, smooth: true, showSymbol: false, lineStyle: { width: 1, color: 'rgba(167,139,250,0.6)', type: 'dashed' } },
    )
  }

  if (overlays.value.vwap) {
    const vwap = calcVWAP(data)
    series.push({ name: 'VWAP', type: 'line', data: vwap, xAxisIndex: 0, yAxisIndex: 0, smooth: true, showSymbol: false, lineStyle: { width: 1.5, color: '#22d3ee' } })
  }

  const gridConfig = [
    { left: 60, right: 20, top: 30, height: '50%' },
    { left: 60, right: 20, top: '68%', height: '10%' },
  ]
  const xAxisConfig: any[] = [
    { type: 'category', data: dates, gridIndex: 0, axisLine: { lineStyle: { color: '#333' } }, axisLabel: { color: '#888', fontSize: 10 }, splitLine: { show: false }, boundaryGap: true },
    { type: 'category', data: dates, gridIndex: 1, axisLabel: { show: false }, splitLine: { show: false }, boundaryGap: true },
  ]
  const yAxisConfig: any[] = [
    { type: 'value', gridIndex: 0, scale: true, axisLine: { lineStyle: { color: '#333' } }, axisLabel: { color: '#888', fontSize: 10, formatter: (v: number) => v.toFixed(2) }, splitLine: { lineStyle: { color: 'rgba(255,255,255,0.04)' } } },
    { type: 'value', gridIndex: 1, scale: true, axisLabel: { show: false }, splitLine: { show: false } },
  ]

  if (subIndicator.value === 'macd') {
    const macd = calcMACD(data)
    gridConfig.push({ left: 60, right: 20, top: '82%', height: '12%' })
    xAxisConfig.push({ type: 'category', data: dates, gridIndex: 2, axisLabel: { show: false }, splitLine: { show: false } })
    yAxisConfig.push({ type: 'value', gridIndex: 2, scale: true, axisLabel: { show: false }, splitLine: { show: false } })
    series.push(
      { name: 'DIF', type: 'line', data: macd.dif, xAxisIndex: 2, yAxisIndex: 2, showSymbol: false, lineStyle: { width: 1, color: '#fbbf24' } },
      { name: 'DEA', type: 'line', data: macd.dea, xAxisIndex: 2, yAxisIndex: 2, showSymbol: false, lineStyle: { width: 1, color: '#4d9fff' } },
      { name: 'MACD柱', type: 'bar', data: macd.hist.map((v: number) => ({ value: v, itemStyle: { color: v >= 0 ? 'rgba(244,63,94,0.6)' : 'rgba(52,211,153,0.6)' } })), xAxisIndex: 2, yAxisIndex: 2 },
    )
  } else if (subIndicator.value === 'kdj') {
    const kdj = calcKDJ(data)
    gridConfig.push({ left: 60, right: 20, top: '82%', height: '12%' })
    xAxisConfig.push({ type: 'category', data: dates, gridIndex: 2, axisLabel: { show: false }, splitLine: { show: false } })
    yAxisConfig.push({ type: 'value', gridIndex: 2, min: 0, max: 100, axisLabel: { show: false }, splitLine: { show: false } })
    series.push(
      { name: 'K', type: 'line', data: kdj.k, xAxisIndex: 2, yAxisIndex: 2, showSymbol: false, lineStyle: { width: 1, color: '#fbbf24' } },
      { name: 'D', type: 'line', data: kdj.d, xAxisIndex: 2, yAxisIndex: 2, showSymbol: false, lineStyle: { width: 1, color: '#4d9fff' } },
      { name: 'J', type: 'line', data: kdj.j, xAxisIndex: 2, yAxisIndex: 2, showSymbol: false, lineStyle: { width: 1, color: '#f43f5e' } },
    )
  } else if (subIndicator.value === 'rsi') {
    const rsi = calcRSI(data)
    gridConfig.push({ left: 60, right: 20, top: '82%', height: '12%' })
    xAxisConfig.push({ type: 'category', data: dates, gridIndex: 2, axisLabel: { show: false }, splitLine: { show: false } })
    yAxisConfig.push({ type: 'value', gridIndex: 2, min: 0, max: 100, axisLabel: { show: false }, splitLine: { show: false } })
    series.push(
      { name: 'RSI6', type: 'line', data: rsi.rsi6, xAxisIndex: 2, yAxisIndex: 2, showSymbol: false, lineStyle: { width: 1, color: '#f43f5e' } },
      { name: 'RSI12', type: 'line', data: rsi.rsi12, xAxisIndex: 2, yAxisIndex: 2, showSymbol: false, lineStyle: { width: 1, color: '#fbbf24' } },
      { name: 'RSI24', type: 'line', data: rsi.rsi24, xAxisIndex: 2, yAxisIndex: 2, showSymbol: false, lineStyle: { width: 1, color: '#4d9fff' } },
    )
  }

  const option: any = {
    backgroundColor: 'transparent',
    animation: false,
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'cross' },
      formatter: (params: any) => {
        if (!params || !params.length) return ''
        const idx = params[0].dataIndex
        const d = data[idx]
        if (!d) return ''
        let html = `<b>${dates[idx]}</b><br/>`
        html += `开 ${d.open?.toFixed(2)} 收 ${d.close?.toFixed(2)}<br/>`
        html += `高 ${d.high?.toFixed(2)} 低 ${d.low?.toFixed(2)}<br/>`
        html += `量 ${fmtVol(d.volume)} 额 ${fmtVol(d.amount || 0)}<br/>`
        if (d.change_pct !== undefined) html += `涨跌幅 ${d.change_pct?.toFixed(2)}%`
        return html
      },
    },
    legend: { data: series.filter(s => s.type === 'line').map(s => s.name), top: 0, textStyle: { color: '#888', fontSize: 10 }, itemWidth: 14, itemHeight: 8 },
    grid: gridConfig,
    xAxis: xAxisConfig,
    yAxis: yAxisConfig,
    dataZoom: [
      { type: 'inside', xAxisIndex: xAxisConfig.map((_, i) => i), start: 70, end: 100 },
      { show: true, xAxisIndex: xAxisConfig.map((_, i) => i), type: 'slider', height: 16, bottom: 0, borderColor: 'transparent', backgroundColor: 'rgba(255,255,255,0.02)', fillerColor: 'rgba(77,159,255,0.15)', handleStyle: { color: '#4d9fff' }, textStyle: { color: '#888', fontSize: 10 } },
    ],
    series,
  }
  chartInstance.setOption(option, true)
}

async function loadAnalysis() {
  const symbol = route.params.code as string
  const [aData, iData] = await Promise.allSettled([
    api.getDeepAnalysis(symbol, '1y'),
    api.getIndicators(symbol, '1y'),
  ])
  if (aData.status === 'fulfilled' && aData.value) analysis.value = aData.value
  if (iData.status === 'fulfilled' && iData.value) {
    const raw = iData.value
    indicatorsData.value = {
      trend: {
        ma5: raw.ma?.ma5, ma10: raw.ma?.ma10, ma20: raw.ma?.ma20, ma60: raw.ma?.ma60,
        macd_signal: raw.macd?.signal, supertrend_dir: raw.supertrend?.direction,
      },
      oscillator: {
        rsi6: raw.rsi?.rsi6, rsi12: raw.rsi?.rsi12, rsi24: raw.rsi?.rsi24,
        k: raw.kdj?.k, d: raw.kdj?.d, j: raw.kdj?.j,
      },
      volume_ind: { obv_trend: raw.obv?.trend, cmf: raw.cmf, volume_ratio: raw.volume_ratio },
      volatility: { atr: raw.atr, boll_width: raw.bollinger?.width, hist_vol: raw.historical_volatility },
    }
  }
}

async function loadPrediction() {
  const symbol = route.params.code as string
  const data = await api.getPrediction(symbol, '1y')
  if (data) prediction.value = data
}

async function loadAiSummary() {
  const symbol = route.params.code as string
  aiSummaryLoading.value = true
  try {
    const data = await api.getAiSummary(symbol, '1y')
    if (data) aiSummary.value = data
  } catch (e) {
    console.error('Load AI summary error:', e)
  } finally {
    aiSummaryLoading.value = false
  }
}

async function loadFundamentals() {
  const symbol = route.params.code as string
  try {
    const data = await api.getFundamentals(symbol)
    if (data) fundamentalsData.value = data
  } catch (e) {}
}

async function loadCorrelation() {
  const symbol = route.params.code as string
  try {
    const data = await api.getCorrelation(symbol)
    if (data) correlationData.value = data
  } catch (e) {}
}

async function loadFactorAnalysis() {
  const symbol = route.params.code as string
  try {
    const data = await api.getFactorAnalysis(symbol)
    if (data) factorData.value = data
  } catch (e) {}
}

function renderRadarChart() {
  if (!radarChartRef.value || !analysis.value) return
  if (!radarChart) {
    radarChart = echarts.init(radarChartRef.value, undefined, { renderer: 'canvas' })
  }
  const a = analysis.value
  radarChart.setOption({
    animation: false,
    radar: {
      indicator: [
        { name: '趋势', max: 100 }, { name: '动量', max: 100 },
        { name: '成交量', max: 100 }, { name: '波动', max: 100 },
        { name: '支撑阻力', max: 100 }, { name: '形态', max: 100 },
      ],
      shape: 'polygon',
      splitNumber: 4,
      axisName: { color: '#888', fontSize: 10 },
      splitLine: { lineStyle: { color: 'rgba(255,255,255,0.06)' } },
      splitArea: { areaStyle: { color: ['rgba(255,255,255,0.02)', 'rgba(255,255,255,0.04)'] } },
    },
    series: [{
      type: 'radar',
      data: [{
        value: [
          a.trend?.strength || 50,
          Math.abs((a.momentum?.composite_momentum || 0)) * 100,
          a.volume?.volume_ratio_5d ? Math.min(a.volume.volume_ratio_5d * 30, 100) : 50,
          50,
          50,
          50,
        ],
        areaStyle: { color: 'rgba(77,159,255,0.2)' },
        lineStyle: { color: '#4d9fff', width: 2 },
        itemStyle: { color: '#4d9fff' },
      }],
    }],
  }, true)
}

async function runQuickBacktest() {
  const symbol = route.params.code as string
  qbRunning.value = true
  try {
    const rangeMap: Record<string, { start: string, end: string }> = {
      '1m': { start: '2024-12-01', end: '2025-04-29' },
      '3m': { start: '2025-01-01', end: '2025-04-29' },
      '6m': { start: '2024-10-01', end: '2025-04-29' },
      '1y': { start: '2024-04-29', end: '2025-04-29' },
      '3y': { start: '2022-04-29', end: '2025-04-29' },
    }
    const r = rangeMap[qbRange.value] || rangeMap['1y']
    const data = await api.runBacktest(symbol, qbStrategy.value, r.start, r.end, 1000000)
    if (data) qbResult.value = data
  } catch (e) {
    console.error('Quick backtest error:', e)
  } finally {
    qbRunning.value = false
  }
}

const qbEquityOption = computed(() => {
  if (!qbResult.value?.equity_curve) return {}
  const eq = qbResult.value.equity_curve
  const dates = eq.map((d: any) => (d.date || '').slice(0, 10))
  const values = eq.map((d: any) => d.value)
  return {
    backgroundColor: 'transparent', animation: false,
    tooltip: { trigger: 'axis' },
    grid: { left: 50, right: 10, top: 10, bottom: 24 },
    xAxis: { type: 'category', data: dates, axisLabel: { color: '#888', fontSize: 9 } },
    yAxis: { type: 'value', scale: true, axisLabel: { color: '#888', fontSize: 9 }, splitLine: { lineStyle: { color: 'rgba(255,255,255,0.04)' } } },
    series: [{ type: 'line', data: values, showSymbol: false, lineStyle: { width: 1.5, color: '#4d9fff' }, areaStyle: { color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: 'rgba(77,159,255,0.15)' }, { offset: 1, color: 'rgba(77,159,255,0)' }] } } }],
  }
})

function submitOrder(type: string) {
  if (!orderPrice.value || !orderShares.value) return
  const symbol = route.params.code as string
  const opts: any = { name: stockInfo.value.name, market: stockInfo.value.market }
  if (stopLoss.value) opts.stopLoss = stopLoss.value
  if (takeProfit.value) opts.takeProfit = takeProfit.value
  if (type === 'buy') {
    api.buy(symbol, orderPrice.value, orderShares.value, opts)
  } else {
    api.sell(symbol, orderPrice.value, orderShares.value)
  }
}

let updateTimer: any = null

onMounted(async () => {
  await loadStockData()
  await nextTick()
  loadKline()
  loadAnalysis()
  loadPrediction()
  loadAiSummary()
  loadFundamentals()
  loadCorrelation()
  loadFactorAnalysis()
  updateTimer = setInterval(loadStockData, 10000)
})

onUnmounted(() => {
  if (updateTimer) clearInterval(updateTimer)
  if (chartInstance) { chartInstance.dispose(); chartInstance = null }
  if (radarChart) { radarChart.dispose(); radarChart = null }
})

watch(activeTab, (tab) => {
  if (tab === 'kline') {
    nextTick(() => { if (chartInstance) chartInstance!.resize() })
  }
  if (tab === 'indicators') {
    nextTick(() => renderRadarChart())
  }
})

window.addEventListener('resize', () => {
  chartInstance?.resize()
  radarChart?.resize()
})
</script>

<style scoped>
.stock-detail { padding: 20px; max-width: 1200px; margin: 0 auto; }
.page-header { display: flex; align-items: center; gap: 12px; margin-bottom: 12px; }
.back-btn { background: var(--bg-secondary); border: 1px solid var(--border-color); border-radius: var(--radius-sm); padding: 6px 8px; cursor: pointer; color: var(--text-secondary); }
.page-title { font-size: 20px; font-weight: 700; color: var(--text-primary); }
.stock-name { font-size: 14px; color: var(--text-secondary); margin-left: 8px; }
.stock-market { font-size: 11px; color: var(--accent-cyan); background: rgba(77,159,255,0.1); padding: 2px 8px; border-radius: 10px; margin-left: 8px; }
.header-actions { margin-left: auto; }
.action-btn { background: transparent; border: 1px solid var(--border-color); border-radius: var(--radius-sm); padding: 6px 8px; cursor: pointer; color: var(--text-secondary); transition: all 0.15s; }
.action-btn:hover { background: rgba(255,255,255,0.05); }
.action-btn.active { border-color: var(--accent-yellow); }

.price-bar { display: flex; justify-content: space-between; align-items: center; padding: 12px 16px; background: var(--bg-secondary); border: 1px solid var(--border-color); border-radius: var(--radius-md); margin-bottom: 12px; }
.price-bar.up { border-left: 3px solid var(--accent-red); }
.price-bar.down { border-left: 3px solid var(--accent-green); }
.price-main { display: flex; align-items: baseline; gap: 10px; }
.price { font-size: 28px; font-weight: 700; font-family: var(--font-mono); }
.price-bar.up .price, .price-bar.up .price-pct, .price-bar.up .price-change { color: var(--accent-red); }
.price-bar.down .price, .price-bar.down .price-pct, .price-bar.down .price-change { color: var(--accent-green); }
.price-pct { font-size: 16px; font-weight: 600; font-family: var(--font-mono); }
.price-change { font-size: 13px; font-family: var(--font-mono); }
.price-meta { display: flex; gap: 14px; font-size: 11px; color: var(--text-secondary); font-family: var(--font-mono); flex-wrap: wrap; }

.tab-bar { display: flex; gap: 2px; margin-bottom: 12px; background: var(--bg-secondary); border-radius: var(--radius-md); padding: 3px; overflow-x: auto; }
.tab-btn { padding: 7px 12px; border: none; background: transparent; color: var(--text-secondary); font-size: 12px; font-weight: 500; border-radius: var(--radius-sm); cursor: pointer; transition: all 0.15s; white-space: nowrap; }
.tab-btn.active { background: rgba(77,159,255,0.15); color: var(--accent-cyan); }

.kline-section { background: var(--bg-secondary); border: 1px solid var(--border-color); border-radius: var(--radius-lg); padding: 12px; }
.kline-toolbar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; flex-wrap: wrap; gap: 6px; }
.toolbar-left, .toolbar-right { display: flex; gap: 4px; align-items: center; }
.tool-btn { padding: 3px 8px; border: 1px solid transparent; border-radius: 3px; background: transparent; color: var(--text-secondary); font-size: 11px; cursor: pointer; transition: all 0.15s; }
.tool-btn:hover { color: var(--text-primary); background: rgba(255,255,255,0.05); }
.tool-btn.active { background: rgba(77,159,255,0.15); color: var(--accent-cyan); border-color: rgba(77,159,255,0.3); }
.tool-divider { width: 1px; height: 14px; background: var(--border-color); margin: 0 4px; }
.tool-select { background: var(--bg-primary); border: 1px solid var(--border-color); color: var(--text-primary); padding: 3px 6px; border-radius: 3px; font-size: 11px; }
.kline-chart { width: 100%; height: 500px; }

.indicators-section { padding: 0; }
.indicator-panels { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.ind-panel { background: var(--bg-secondary); border: 1px solid var(--border-color); border-radius: var(--radius-md); padding: 14px; }
.composite-panel { grid-column: span 2; }
.ind-title { font-size: 12px; font-weight: 600; color: var(--accent-cyan); margin-bottom: 10px; }
.ind-grid { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 6px; }
.ind-item { display: flex; justify-content: space-between; padding: 4px 6px; background: rgba(255,255,255,0.02); border-radius: 3px; }
.ind-label { font-size: 11px; color: var(--text-secondary); }
.ind-value { font-size: 11px; font-family: var(--font-mono); color: var(--text-primary); }
.radar-chart { width: 100%; height: 220px; }

.analysis-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.analysis-card { background: var(--bg-secondary); border: 1px solid var(--border-color); border-radius: var(--radius-md); padding: 14px; }
.analysis-card h3 { font-size: 13px; font-weight: 600; color: var(--accent-cyan); margin-bottom: 10px; }
.analysis-item { display: flex; justify-content: space-between; padding: 6px 0; border-bottom: 1px solid rgba(255,255,255,0.03); }
.analysis-item .label { font-size: 12px; color: var(--text-secondary); }
.analysis-item .value { font-size: 12px; font-family: var(--font-mono); color: var(--text-primary); }
.analysis-item .value.up { color: var(--accent-red); }
.analysis-item .value.down { color: var(--accent-green); }
.composite-card { grid-column: span 2; }
.composite-score { display: flex; align-items: center; gap: 16px; }
.score-value { font-size: 32px; font-weight: 700; font-family: var(--font-mono); }
.score-value.up { color: var(--accent-red); }
.score-value.down { color: var(--accent-green); }
.score-signal { font-size: 14px; color: var(--text-secondary); text-transform: uppercase; }
.score-conf { font-size: 12px; color: var(--text-tertiary); }

.pred-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; }
.pred-card { background: var(--bg-secondary); border: 1px solid var(--border-color); border-radius: var(--radius-md); padding: 14px; display: flex; flex-direction: column; gap: 4px; }
.pred-card.up { border-top: 3px solid var(--accent-red); }
.pred-card.down { border-top: 3px solid var(--accent-green); }
.pred-label { font-size: 12px; color: var(--text-secondary); font-weight: 600; }
.pred-price { font-size: 20px; font-weight: 700; font-family: var(--font-mono); color: var(--text-primary); }
.pred-range { font-size: 11px; color: var(--text-tertiary); font-family: var(--font-mono); }
.pred-conf { font-size: 11px; color: var(--accent-cyan); }
.pred-summary { grid-column: span 3; display: flex; justify-content: center; gap: 24px; padding: 12px; background: var(--bg-secondary); border: 1px solid var(--border-color); border-radius: var(--radius-md); }
.pred-signal { font-size: 14px; font-weight: 600; text-transform: uppercase; }
.pred-signal.bullish { color: var(--accent-red); }
.pred-signal.bearish { color: var(--accent-green); }
.pred-signal.neutral { color: var(--text-secondary); }
.pred-vol { font-size: 12px; color: var(--text-tertiary); }

.ai-summary-section { padding: 16px 0; }
.ai-summary-card { background: var(--bg-secondary); border: 1px solid var(--border-color); border-radius: var(--radius-lg); padding: 20px; }
.ai-overall { display: flex; align-items: center; gap: 12px; padding: 12px 16px; border-radius: var(--radius-md); margin-bottom: 16px; }
.ai-overall.bullish { background: rgba(244,63,94,0.1); border-left: 3px solid var(--accent-red); }
.ai-overall.bearish { background: rgba(52,211,153,0.1); border-left: 3px solid var(--accent-green); }
.ai-overall.neutral { background: rgba(255,255,255,0.04); border-left: 3px solid var(--text-tertiary); }
.overall-label { font-size: 12px; color: var(--text-secondary); }
.overall-value { font-size: 18px; font-weight: 700; }
.ai-overall.bullish .overall-value { color: var(--accent-red); }
.ai-overall.bearish .overall-value { color: var(--accent-green); }
.ai-overall.neutral .overall-value { color: var(--text-primary); }
.ai-points { display: flex; flex-direction: column; gap: 10px; margin-bottom: 16px; }
.ai-point { display: flex; align-items: flex-start; gap: 8px; font-size: 13px; }
.point-dot { width: 6px; height: 6px; border-radius: 50%; margin-top: 6px; flex-shrink: 0; }
.ai-point.bullish .point-dot { background: var(--accent-red); }
.ai-point.bearish .point-dot { background: var(--accent-green); }
.ai-point.neutral .point-dot { background: var(--text-tertiary); }
.point-text { color: var(--text-primary); line-height: 1.5; }
.ai-changes { display: flex; gap: 16px; padding-top: 12px; border-top: 1px solid var(--border-color); }
.change-item { display: flex; flex-direction: column; gap: 2px; }
.change-label { font-size: 11px; color: var(--text-tertiary); }
.change-value { font-size: 14px; font-family: var(--font-mono); font-weight: 600; }
.change-value.up { color: var(--accent-red); }
.change-value.down { color: var(--accent-green); }
.empty-state { text-align: center; padding: 40px; color: var(--text-tertiary); }

.quick-backtest-section { display: flex; flex-direction: column; gap: 16px; }
.qb-config { background: var(--bg-secondary); border: 1px solid var(--border-color); border-radius: var(--radius-lg); padding: 16px; }
.qb-row { margin-bottom: 10px; }
.qb-row label { display: block; font-size: 11px; color: var(--text-secondary); margin-bottom: 4px; }
.qb-quick-btns { display: flex; gap: 4px; }
.qb-btn { padding: 4px 10px; border: 1px solid var(--border-color); border-radius: 3px; background: transparent; color: var(--text-secondary); font-size: 11px; cursor: pointer; }
.qb-btn.active { background: rgba(77,159,255,0.15); color: var(--accent-cyan); border-color: rgba(77,159,255,0.3); }
.btn-run-qb { padding: 8px; border: none; border-radius: var(--radius-sm); background: linear-gradient(135deg, #4d9fff, #a78bfa); color: white; font-size: 13px; font-weight: 600; cursor: pointer; }
.btn-run-qb:disabled { opacity: 0.5; cursor: not-allowed; }
.qb-metrics { display: flex; gap: 8px; flex-wrap: wrap; }
.qb-chart { background: var(--bg-secondary); border: 1px solid var(--border-color); border-radius: var(--radius-lg); padding: 12px; }

.trade-section { max-width: 400px; }
.trade-form { background: var(--bg-secondary); border: 1px solid var(--border-color); border-radius: var(--radius-lg); padding: 16px; }
.form-row { margin-bottom: 12px; }
.form-row label { display: block; font-size: 11px; color: var(--text-secondary); margin-bottom: 4px; }
.form-input { width: 100%; padding: 8px 12px; background: var(--bg-primary); border: 1px solid var(--border-color); border-radius: var(--radius-sm); color: var(--text-primary); font-family: var(--font-mono); font-size: 13px; }
.form-input:focus { outline: none; border-color: var(--accent-cyan); }
.trade-estimate { display: flex; justify-content: space-between; font-size: 11px; color: var(--text-tertiary); margin-bottom: 10px; padding: 6px 8px; background: rgba(255,255,255,0.02); border-radius: var(--radius-sm); }
.t1-warning { background: rgba(251,146,60,0.1); color: var(--accent-orange); font-size: 11px; padding: 6px 10px; border-radius: var(--radius-sm); }
.collapse-toggle { background: none; border: none; color: var(--text-secondary); font-size: 11px; cursor: pointer; padding: 4px 0; }
.collapse-content { margin-top: 8px; }
.trade-btns { display: flex; gap: 12px; margin-top: 12px; }
.btn-buy, .btn-sell { flex: 1; padding: 10px; border: none; border-radius: var(--radius-sm); font-size: 14px; font-weight: 600; cursor: pointer; }
.btn-buy { background: var(--accent-red); color: white; }
.btn-sell { background: var(--accent-green); color: white; }
.btn-sell:disabled { opacity: 0.4; cursor: not-allowed; }

.empty-state-small { text-align: center; padding: 40px; color: var(--text-tertiary); font-size: 13px; }
.skeleton { background: linear-gradient(90deg, rgba(255,255,255,0.04) 25%, rgba(255,255,255,0.08) 50%, rgba(255,255,255,0.04) 75%); background-size: 200% 100%; animation: shimmer 1.5s infinite; }
@keyframes shimmer { 0% { background-position: 200% 0; } 100% { background-position: -200% 0; } }

.fund-grid { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 12px; }
.fund-card { background: var(--bg-secondary); border: 1px solid var(--border-color); border-radius: var(--radius-md); padding: 14px; }
.fund-card h3 { font-size: 13px; font-weight: 600; color: var(--accent-cyan); margin-bottom: 10px; }
.fund-item { display: flex; justify-content: space-between; padding: 5px 0; border-bottom: 1px solid rgba(255,255,255,0.03); }
.fund-item .label { font-size: 12px; color: var(--text-secondary); }
.fund-item .value { font-size: 12px; font-family: var(--font-mono); color: var(--text-primary); font-weight: 600; }
.fund-item .value.up { color: var(--accent-red); }
.fund-item .value.down { color: var(--accent-green); }

.corr-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.corr-card { background: var(--bg-secondary); border: 1px solid var(--border-color); border-radius: var(--radius-md); padding: 14px; }
.corr-card h3 { font-size: 13px; font-weight: 600; color: var(--accent-cyan); margin-bottom: 10px; }
.corr-item { display: flex; justify-content: space-between; padding: 6px 0; border-bottom: 1px solid rgba(255,255,255,0.03); }
.corr-item .label { font-size: 12px; color: var(--text-secondary); }
.corr-item .value { font-size: 12px; font-family: var(--font-mono); color: var(--text-primary); font-weight: 600; }
.corr-item .value.up { color: var(--accent-red); }
.corr-item .value.down { color: var(--accent-green); }
.corr-chart-card { background: var(--bg-secondary); border: 1px solid var(--border-color); border-radius: var(--radius-md); padding: 14px; }
.corr-chart-card h3 { font-size: 13px; font-weight: 600; color: var(--accent-cyan); margin-bottom: 10px; }

.factor-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.factor-score-card { grid-column: span 2; background: var(--bg-secondary); border: 1px solid var(--border-color); border-radius: var(--radius-md); padding: 14px; text-align: center; }
.factor-score-card h3 { font-size: 13px; font-weight: 600; color: var(--accent-cyan); margin-bottom: 10px; }
.factor-composite { padding: 10px 0; }
.composite-value { font-size: 36px; font-weight: 700; font-family: var(--font-mono); }
.composite-value.up { color: var(--accent-red); }
.composite-value.down { color: var(--accent-green); }
.factor-card { background: var(--bg-secondary); border: 1px solid var(--border-color); border-radius: var(--radius-md); padding: 14px; }
.factor-card.bullish { border-left: 3px solid var(--accent-red); }
.factor-card.bearish { border-left: 3px solid var(--accent-green); }
.factor-name { font-size: 12px; font-weight: 600; color: var(--text-primary); margin-bottom: 6px; }
.factor-value { font-size: 18px; font-weight: 700; font-family: var(--font-mono); color: var(--text-primary); margin-bottom: 8px; }
.factor-bar-wrap { height: 6px; background: rgba(255,255,255,0.05); border-radius: 3px; overflow: hidden; margin-bottom: 6px; }
.factor-bar { height: 100%; border-radius: 3px; transition: width 0.3s; }
.factor-meta { display: flex; justify-content: space-between; }
.factor-pct { font-size: 10px; color: var(--text-tertiary); }
.factor-dir { font-size: 10px; font-weight: 600; }
.factor-dir.bullish { color: var(--accent-red); }
.factor-dir.bearish { color: var(--accent-green); }

@media (max-width: 768px) {
  .stock-detail { padding: 10px; }
  .analysis-grid { grid-template-columns: 1fr; }
  .composite-card { grid-column: span 1; }
  .pred-grid { grid-template-columns: 1fr; }
  .pred-summary { grid-column: span 1; }
  .indicator-panels { grid-template-columns: 1fr; }
  .composite-panel { grid-column: span 1; }
  .kline-chart { height: 350px; }
  .price-bar { flex-direction: column; gap: 8px; align-items: flex-start; }
  .price-meta { gap: 8px; }
}
</style>
