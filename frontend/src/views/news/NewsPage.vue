<template>
  <div class="news-page">
    <div class="page-hero">
      <h1 class="page-title">资讯中心</h1>
      <p class="page-subtitle">实时财经新闻与市场情绪分析</p>
    </div>

    <div class="tab-bar">
      <button class="apple-tab" :class="{ active: activeTab === 'latest' }" @click="activeTab = 'latest'">最新资讯</button>
      <button class="apple-tab" :class="{ active: activeTab === 'sentiment' }" @click="activeTab = 'sentiment'; fetchSentiment()">市场情绪</button>
    </div>

    <div v-show="activeTab === 'latest'" class="news-list">
      <div v-if="loading" class="loading-state">
        <div class="loading-spinner" />
        <span>加载中...</span>
      </div>
      <div v-else-if="!newsList.length" class="empty-state">
        <div class="empty-icon">📰</div>
        <p>暂无资讯数据</p>
      </div>
      <transition-group v-else name="news-list" tag="div" class="news-cards">
        <div v-for="(item, idx) in newsList" :key="idx" class="news-card apple-card apple-card-interactive" @click="openUrl(item.url)">
          <div class="news-card-body">
            <div class="news-header">
              <span v-if="item.sentiment_label === 'bullish' || item.sentiment_label === 'slightly_bullish'" class="apple-badge apple-badge-rise">利多</span>
              <span v-else-if="item.sentiment_label === 'bearish' || item.sentiment_label === 'slightly_bearish'" class="apple-badge apple-badge-fall">利空</span>
              <span class="news-title">{{ item.title }}</span>
            </div>
            <div class="news-footer">
              <span class="news-source">{{ item.source }}</span>
              <span class="news-time">{{ formatTime(item.time) }}</span>
              <span v-if="item.related_symbols?.length" class="news-symbols">
                <span v-for="sym in item.related_symbols.slice(0, 3)" :key="sym" class="apple-badge apple-badge-accent" @click.stop="goToStock(sym)">{{ sym }}</span>
              </span>
            </div>
          </div>
        </div>
      </transition-group>
    </div>

    <div v-show="activeTab === 'sentiment'" class="sentiment-panel">
      <div v-if="!sentimentData" class="loading-state">
        <div class="loading-spinner" />
        <span>分析中...</span>
      </div>
      <template v-else>
        <div class="fg-hero apple-card">
          <div class="fg-label">恐惧贪婪指数</div>
          <div class="fg-value" :class="fgClass">{{ sentimentData.sentiment.fear_greed_index.toFixed(1) }}</div>
          <div class="fg-status">{{ sentimentData.sentiment.label }}</div>
          <div class="fg-bar-track">
            <div class="fg-bar-bg">
              <div class="fg-bar-fill" :style="{ width: sentimentData.sentiment.fear_greed_index + '%' }" />
              <div class="fg-bar-marker" :style="{ left: sentimentData.sentiment.fear_greed_index + '%' }" />
            </div>
            <div class="fg-bar-labels">
              <span>极度恐惧</span><span>恐惧</span><span>中性</span><span>贪婪</span><span>极度贪婪</span>
            </div>
          </div>
        </div>

        <div class="sentiment-metrics">
          <div class="metric-card apple-card">
            <div class="apple-metric">
              <div class="apple-metric-label">新闻情绪</div>
              <div class="apple-metric-value" :class="sentimentData.sentiment.news_sentiment > 0 ? 'text-rise' : 'text-fall'">
                {{ (sentimentData.sentiment.news_sentiment * 100).toFixed(1) }}
              </div>
            </div>
          </div>
          <div class="metric-card apple-card">
            <div class="apple-metric">
              <div class="apple-metric-label">涨跌情绪</div>
              <div class="apple-metric-value" :class="sentimentData.sentiment.volume_sentiment > 0 ? 'text-rise' : 'text-fall'">
                {{ (sentimentData.sentiment.volume_sentiment * 100).toFixed(1) }}
              </div>
            </div>
          </div>
          <div class="metric-card apple-card">
            <div class="apple-metric">
              <div class="apple-metric-label">动量情绪</div>
              <div class="apple-metric-value" :class="sentimentData.sentiment.momentum_sentiment > 0 ? 'text-rise' : 'text-fall'">
                {{ (sentimentData.sentiment.momentum_sentiment * 100).toFixed(1) }}
              </div>
            </div>
          </div>
          <div class="metric-card apple-card">
            <div class="apple-metric">
              <div class="apple-metric-label">广度情绪</div>
              <div class="apple-metric-value" :class="sentimentData.sentiment.breadth_sentiment > 0 ? 'text-rise' : 'text-fall'">
                {{ (sentimentData.sentiment.breadth_sentiment * 100).toFixed(1) }}
              </div>
            </div>
          </div>
        </div>

        <div v-if="sentimentData.summary" class="summary-card apple-card">
          <h3 class="summary-title">资讯统计</h3>
          <div class="summary-row">
            <span class="apple-badge apple-badge-rise">利多 {{ sentimentData.summary.bullish }}</span>
            <span class="apple-badge" style="background:var(--bg-elevated);color:var(--text-secondary)">中性 {{ sentimentData.summary.neutral }}</span>
            <span class="apple-badge apple-badge-fall">利空 {{ sentimentData.summary.bearish }}</span>
          </div>
          <div v-if="sentimentData.summary.hot_symbols?.length" class="hot-symbols">
            <span class="hot-label">热门标的</span>
            <div class="hot-list">
              <span v-for="s in sentimentData.summary.hot_symbols" :key="s.symbol" class="apple-badge apple-badge-accent" @click="goToStock(s.symbol)">{{ s.symbol }} ({{ s.count }})</span>
            </div>
          </div>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '@/api'
import type { NewsItem, MarketSentimentData } from '@/types'

const router = useRouter()
const activeTab = ref('latest')
const newsList = ref<NewsItem[]>([])
const sentimentData = ref<MarketSentimentData | null>(null)
const loading = ref(false)

const fgClass = computed(() => {
  if (!sentimentData.value) return ''
  const v = sentimentData.value.sentiment.fear_greed_index
  if (v >= 80) return 'extreme-greed'
  if (v >= 60) return 'greed'
  if (v >= 40) return 'neutral'
  if (v >= 20) return 'fear'
  return 'extreme-fear'
})

async function fetchNews() {
  loading.value = true
  try {
    newsList.value = await api.news.latest(50)
  } catch { newsList.value = [] }
  finally { loading.value = false }
}

async function fetchSentiment() {
  try {
    sentimentData.value = await api.news.sentiment()
  } catch { sentimentData.value = null }
}

function goToStock(symbol: string) {
  router.push(`/stock/${symbol}`)
}

function openUrl(url: string) {
  if (url) window.open(url, '_blank')
}

function formatTime(t: string | number) {
  if (!t) return ''
  const ts = typeof t === 'string' ? parseInt(t, 10) : t
  if (isNaN(ts)) return String(t)
  const d = new Date(ts * 1000)
  if (isNaN(d.getTime())) return String(t)
  const now = new Date()
  const diffMs = now.getTime() - d.getTime()
  if (diffMs < 60000) return '刚刚'
  if (diffMs < 3600000) return Math.floor(diffMs / 60000) + '分钟前'
  if (diffMs < 86400000) return Math.floor(diffMs / 3600000) + '小时前'
  const month = (d.getMonth() + 1).toString().padStart(2, '0')
  const day = d.getDate().toString().padStart(2, '0')
  const hour = d.getHours().toString().padStart(2, '0')
  const min = d.getMinutes().toString().padStart(2, '0')
  return `${month}-${day} ${hour}:${min}`
}

onMounted(fetchNews)
</script>

<style scoped>
.news-page { max-width: 960px; margin: 0 auto; }
.page-hero { margin-bottom: var(--space-6); }
.page-title { font-size: var(--text-3xl); font-weight: 700; letter-spacing: -0.03em; color: var(--text-primary); line-height: var(--leading-tight); }
.page-subtitle { font-size: var(--text-md); color: var(--text-secondary); margin-top: var(--space-2); }
.tab-bar { display: inline-flex; gap: 2px; padding: 3px; background: var(--bg-elevated); border-radius: var(--radius-sm); border: 1px solid var(--border-subtle); margin-bottom: var(--space-6); }
.news-cards { display: flex; flex-direction: column; gap: var(--space-2); }
.news-card { padding: var(--space-4) var(--space-5); }
.news-card-body { display: flex; flex-direction: column; gap: var(--space-2); }
.news-header { display: flex; align-items: flex-start; gap: var(--space-2); }
.news-title { font-size: var(--text-sm); color: var(--text-primary); line-height: 1.5; font-weight: 500; }
.news-footer { display: flex; align-items: center; gap: var(--space-3); font-size: var(--text-xs); color: var(--text-tertiary); }
.news-source { font-weight: 500; }
.news-time { }
.news-symbols { display: flex; gap: var(--space-1); }
.fg-hero { text-align: center; padding: var(--space-10) var(--space-6); margin-bottom: var(--space-4); }
.fg-label { font-size: var(--text-sm); color: var(--text-secondary); margin-bottom: var(--space-2); font-weight: 500; text-transform: uppercase; letter-spacing: 0.04em; }
.fg-value { font-size: 72px; font-weight: 700; font-family: var(--font-data); letter-spacing: -0.04em; line-height: 1; }
.fg-value.extreme-greed { color: #ff3b30; }
.fg-value.greed { color: #ff9f0a; }
.fg-value.neutral { color: var(--text-secondary); }
.fg-value.fear { color: #2997ff; }
.fg-value.extreme-fear { color: #bf5af2; }
.fg-status { font-size: var(--text-lg); color: var(--text-secondary); margin: var(--space-3) 0 var(--space-6); font-weight: 500; }
.fg-bar-track { max-width: 480px; margin: 0 auto; }
.fg-bar-bg { height: 6px; background: linear-gradient(to right, #bf5af2, #2997ff, var(--text-tertiary), #ff9f0a, #ff3b30); border-radius: 3px; position: relative; }
.fg-bar-fill { height: 100%; border-radius: 3px; opacity: 0.2; background: var(--bg-base); }
.fg-bar-marker { position: absolute; top: -5px; width: 16px; height: 16px; border-radius: 50%; background: white; border: 3px solid var(--accent); transform: translateX(-50%); box-shadow: var(--shadow-md); }
.fg-bar-labels { display: flex; justify-content: space-between; font-size: 10px; color: var(--text-tertiary); margin-top: var(--space-2); }
.sentiment-metrics { display: grid; grid-template-columns: repeat(4, 1fr); gap: var(--space-3); margin-bottom: var(--space-4); }
.metric-card { padding: var(--space-5); }
.summary-card { padding: var(--space-5); }
.summary-title { font-size: var(--text-md); font-weight: 600; color: var(--text-primary); margin-bottom: var(--space-4); }
.summary-row { display: flex; gap: var(--space-3); margin-bottom: var(--space-4); }
.hot-symbols { }
.hot-label { font-size: var(--text-xs); color: var(--text-tertiary); text-transform: uppercase; letter-spacing: 0.04em; display: block; margin-bottom: var(--space-2); }
.hot-list { display: flex; flex-wrap: wrap; gap: var(--space-2); }
.loading-state { display: flex; flex-direction: column; align-items: center; gap: var(--space-3); padding: var(--space-16); color: var(--text-tertiary); }
.loading-spinner { width: 24px; height: 24px; border: 2px solid var(--border); border-top-color: var(--accent); border-radius: 50%; animation: spin 0.8s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
.empty-state { text-align: center; padding: var(--space-16); color: var(--text-tertiary); }
.empty-icon { font-size: 40px; margin-bottom: var(--space-3); }
.news-list-enter-active { animation: fadeSlideUp var(--duration-normal) var(--ease-out); }
.news-list-leave-active { animation: fadeIn var(--duration-fast) var(--ease-out) reverse; }
</style>
