<template>
  <div class="strategy-intro-page">
    <div class="page-header">
      <h1 class="page-title">策略介绍</h1>
    </div>

    <div class="strategy-grid">
      <div v-for="s in strategyList" :key="s.key" class="strategy-card card">
        <div class="card-accent" :style="{ background: s.gradient }"></div>
        <div class="card-body">
          <div class="card-top">
            <span class="card-icon">{{ s.icon }}</span>
            <div class="card-titles">
              <h3 class="card-name">{{ s.name }}</h3>
              <span class="card-en">{{ s.en }}</span>
            </div>
          </div>
          <p class="card-desc">{{ s.desc }}</p>
          <div class="card-params" v-if="s.params.length">
            <span class="params-label">参数</span>
            <div class="params-list">
              <span v-for="p in s.params" :key="p" class="param-tag">{{ p }}</span>
            </div>
          </div>
          <div class="card-tags">
            <span v-for="t in s.tags" :key="t.label" class="tag" :class="t.type">{{ t.label }}</span>
          </div>
          <div class="card-footer">
            <span class="footer-item">
              <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83"/></svg>
              {{ s.freq }}
            </span>
            <span class="footer-item">
              <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 12h-4l-3 9L9 3l-3 9H2"/></svg>
              {{ s.risk }}
            </span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
const strategyList = [
  {
    key: 'dual_ma', name: '双均线策略', en: 'Dual Moving Average',
    icon: '📐', gradient: 'linear-gradient(135deg, #3b82f6, #8b5cf6)',
    desc: '基于快慢两条移动平均线的交叉信号进行交易。当快线上穿慢线时买入，下穿时卖出。适合趋势明显的市场。',
    params: ['快线周期', '慢线周期'], freq: '日线', risk: '中等',
    tags: [{ label: '趋势跟踪', type: 'blue' }, { label: '经典', type: 'violet' }],
  },
  {
    key: 'macd', name: 'MACD策略', en: 'MACD Crossover',
    icon: '📊', gradient: 'linear-gradient(135deg, #f59e0b, #ef4444)',
    desc: '利用MACD指标的金叉死叉信号进行交易。DIF上穿DEA为买入信号，下穿为卖出信号。配合零轴判断多空趋势。',
    params: ['快线周期', '慢线周期', '信号线周期'], freq: '日线', risk: '中等',
    tags: [{ label: '动量', type: 'amber' }, { label: '震荡+趋势', type: 'red' }],
  },
  {
    key: 'bollinger_breakout', name: '布林带突破', en: 'Bollinger Breakout',
    icon: '📈', gradient: 'linear-gradient(135deg, #22c55e, #38bdf8)',
    desc: '价格突破布林带上轨时买入，突破下轨时卖出。结合带宽收缩判断突破方向，适合波动率变化的市场。',
    params: ['周期', '标准差倍数'], freq: '日线', risk: '较高',
    tags: [{ label: '突破', type: 'green' }, { label: '波动率', type: 'cyan' }],
  },
  {
    key: 'ichimoku', name: '一目均衡', en: 'Ichimoku Cloud',
    icon: '☁️', gradient: 'linear-gradient(135deg, #8b5cf6, #ec4899)',
    desc: '日本技术分析体系，通过转换线、基准线、云带等多维度判断趋势方向和支撑阻力。信号全面但参数较多。',
    params: ['转换线', '基准线', '先行跨度'], freq: '日线', risk: '中等',
    tags: [{ label: '综合', type: 'violet' }, { label: '多维度', type: 'rose' }],
  },
  {
    key: 'adaptive', name: '自适应引擎', en: 'Adaptive Engine',
    icon: '🧠', gradient: 'linear-gradient(135deg, #38bdf8, #a78bfa)',
    desc: '根据市场状态自动切换策略参数和交易逻辑。在趋势市中采用趋势策略，在震荡市中采用均值回归策略。',
    params: ['自适应窗口', '状态阈值'], freq: '自适应', risk: '动态',
    tags: [{ label: 'AI驱动', type: 'cyan' }, { label: '自适应', type: 'purple' }],
  },
  {
    key: 'rsi_reversal', name: 'RSI反转', en: 'RSI Reversal',
    icon: '🔄', gradient: 'linear-gradient(135deg, #f43f5e, #fb923c)',
    desc: '利用RSI超买超卖信号进行反向交易。RSI低于30时买入，高于70时卖出。适合震荡市中的均值回归交易。',
    params: ['RSI周期', '超买线', '超卖线'], freq: '日线', risk: '较低',
    tags: [{ label: '均值回归', type: 'rose' }, { label: '震荡市', type: 'orange' }],
  },
]
</script>

<style scoped>
.strategy-intro-page { padding: 14px 16px; max-width: 1200px; margin: 0 auto; }
.page-header { margin-bottom: 12px; }
.page-title { font-size: 18px; font-weight: 700; color: var(--text-primary); }

.strategy-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; }
.strategy-card {
  overflow: hidden; transition: border-color var(--transition), transform var(--transition);
  cursor: default;
}
.strategy-card:hover { border-color: rgba(56,189,248,0.15); transform: translateY(-1px); }
.card-accent { height: 3px; }
.card-body { padding: 14px; }
.card-top { display: flex; gap: 10px; align-items: center; margin-bottom: 8px; }
.card-icon { font-size: 22px; }
.card-titles { display: flex; flex-direction: column; gap: 1px; }
.card-name { font-size: 14px; font-weight: 700; color: var(--text-primary); margin: 0; }
.card-en { font-size: 9px; color: var(--text-tertiary); font-family: var(--font-mono); }
.card-desc { font-size: 11px; color: var(--text-secondary); line-height: 1.6; margin-bottom: 8px; }
.card-params { margin-bottom: 8px; }
.params-label { font-size: 9px; color: var(--text-tertiary); display: block; margin-bottom: 3px; }
.params-list { display: flex; gap: 3px; flex-wrap: wrap; }
.param-tag {
  font-size: 9px; padding: 1px 5px; border-radius: 2px;
  background: var(--bg-hover); color: var(--text-secondary); border: 1px solid var(--border-subtle);
}
.card-tags { display: flex; gap: 4px; margin-bottom: 8px; }
.tag {
  font-size: 9px; padding: 1px 6px; border-radius: 3px; font-weight: 500;
}
.tag.blue { background: var(--accent-blue-dim); color: var(--accent-blue); }
.tag.violet { background: var(--accent-violet-dim); color: var(--accent-violet); }
.tag.amber { background: var(--accent-amber-dim); color: var(--accent-amber); }
.tag.red { background: var(--accent-red-dim); color: var(--accent-red); }
.tag.green { background: var(--accent-green-dim); color: var(--accent-green); }
.tag.cyan { background: var(--accent-cyan-dim); color: var(--accent-cyan); }
.tag.rose { background: var(--accent-rose-dim); color: var(--accent-rose); }
.tag.purple { background: var(--accent-purple-dim); color: var(--accent-purple); }
.tag.orange { background: var(--accent-orange-dim); color: var(--accent-orange); }
.card-footer { display: flex; gap: 12px; padding-top: 6px; border-top: 1px solid var(--border-subtle); }
.footer-item { display: flex; align-items: center; gap: 3px; font-size: 9px; color: var(--text-tertiary); }

@media (max-width: 768px) {
  .strategy-intro-page { padding: 10px; }
  .strategy-grid { grid-template-columns: 1fr; }
}
@media (min-width: 769px) and (max-width: 1024px) {
  .strategy-grid { grid-template-columns: repeat(2, 1fr); }
}
</style>
