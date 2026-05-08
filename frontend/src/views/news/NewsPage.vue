<template>
  <div class="news-page">
    <div class="tab-bar">
      <button class="tab-btn" :class="{ active: activeTab === 'latest' }" @click="activeTab = 'latest'">LATEST NEWS</button>
      <button class="tab-btn" :class="{ active: activeTab === 'sentiment' }" @click="switchToSentiment()">MARKET SENTIMENT</button>
    </div>

    <div v-show="activeTab === 'latest'">
      <div v-if="loading" class="panel-empty">LOADING<span class="blink-cursor">_</span></div>
      <div v-else-if="!newsList.length" class="panel-empty">NO NEWS DATA</div>
      <div v-else class="news-feed">
        <div
          v-for="(item, idx) in newsList"
          :key="idx"
          class="news-row"
          @click="openUrl(item.url)"
        >
          <div class="nr-body">
            <div class="nr-top">
              <span
                v-if="item.sentiment_label === 'bullish' || item.sentiment_label === 'slightly_bullish'"
                class="sentiment-badge badge-bull"
              >BULL</span>
              <span
                v-else-if="item.sentiment_label === 'bearish' || item.sentiment_label === 'slightly_bearish'"
                class="sentiment-badge badge-bear"
              >BEAR</span>
              <span v-else class="sentiment-badge badge-neutral">NEUTRAL</span>
              <span class="nr-title">{{ item.title }}</span>
            </div>
            <div class="nr-meta">
              <span class="nr-source">{{ item.source }}</span>
              <span class="nr-time mono">{{ formatNewsTime(item.time) }}</span>
              <span v-if="item.related_symbols?.length" class="nr-symbols">
                <span
                  v-for="sym in item.related_symbols.slice(0, 3)"
                  :key="sym"
                  class="sym-tag"
                  @click.stop="goToStock(sym)"
                >{{ sym }}</span>
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div v-show="activeTab === 'sentiment'">
      <div v-if="!sentimentData" class="panel-empty">LOADING...</div>
      <template v-else>
        <div class="surface-panel">
          <div class="panel-header"><span class="panel-title">FEAR & GREED INDEX</span></div>
          <div class="fg-body">
            <div class="fg-value" :class="fgClass">
              {{ safeToFixed(sentimentData.sentiment?.fear_greed_index, 1) }}
            </div>
            <div class="fg-label">{{ sentimentData.sentiment.label }}</div>
            <div class="fg-bar-wrap">
              <div class="fg-bar-bg">
                <div class="fg-bar-fill" :style="{ width: sentimentData.sentiment.fear_greed_index + '%' }" />
                <div class="fg-bar-marker" :style="{ left: sentimentData.sentiment.fear_greed_index + '%' }" />
              </div>
              <div class="fg-bar-labels">
                <span>EXTREME FEAR</span>
                <span>FEAR</span>
                <span>NEUTRAL</span>
                <span>GREED</span>
                <span>EXTREME GREED</span>
              </div>
            </div>
          </div>
        </div>

        <div class="sentiment-strip">
          <div class="surface-panel sent-cell">
            <span class="sc-label">NEWS SENTIMENT</span>
            <span class="sc-value mono" :class="sentimentData.sentiment.news_sentiment >= 0 ? 'val-rise' : 'val-fall'">
              {{ safeToFixed((sentimentData.sentiment?.news_sentiment ?? 0) * 100, 1) }}
            </span>
          </div>
          <div class="surface-panel sent-cell">
            <span class="sc-label">VOLUME SENTIMENT</span>
            <span class="sc-value mono" :class="sentimentData.sentiment.volume_sentiment >= 0 ? 'val-rise' : 'val-fall'">
              {{ safeToFixed((sentimentData.sentiment?.volume_sentiment ?? 0) * 100, 1) }}
            </span>
          </div>
          <div class="surface-panel sent-cell">
            <span class="sc-label">MOMENTUM SENTIMENT</span>
            <span class="sc-value mono" :class="sentimentData.sentiment.momentum_sentiment >= 0 ? 'val-rise' : 'val-fall'">
              {{ safeToFixed((sentimentData.sentiment?.momentum_sentiment ?? 0) * 100, 1) }}
            </span>
          </div>
          <div class="surface-panel sent-cell">
            <span class="sc-label">BREADTH SENTIMENT</span>
            <span class="sc-value mono" :class="sentimentData.sentiment.breadth_sentiment >= 0 ? 'val-rise' : 'val-fall'">
              {{ safeToFixed((sentimentData.sentiment?.breadth_sentiment ?? 0) * 100, 1) }}
            </span>
          </div>
        </div>

        <div v-if="sentimentData.summary" class="surface-panel">
          <div class="panel-header"><span class="panel-title">NEWS STATISTICS</span></div>
          <div class="stats-body">
            <div class="stats-row">
              <span class="stat-badge badge-bull">BULLISH {{ sentimentData.summary.bullish }}</span>
              <span class="stat-badge badge-neutral">NEUTRAL {{ sentimentData.summary.neutral }}</span>
              <span class="stat-badge badge-bear">BEARISH {{ sentimentData.summary.bearish }}</span>
            </div>
            <div v-if="sentimentData.summary.hot_symbols?.length" class="hot-section">
              <div class="hot-label">HOT TARGETS</div>
              <div class="hot-list">
                <span
                  v-for="s in sentimentData.summary.hot_symbols"
                  :key="s.symbol"
                  class="hot-tag"
                  @click="goToStock(s.symbol)"
                >{{ s.symbol }} ({{ s.count }})</span>
              </div>
            </div>
          </div>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { createLogger } from '@/composables/useLogger'
import { useRequestCancel } from '@/composables/useRequestCancel'
import { useApiError } from '@/composables/useApiError'
import { api } from '@/api'
import { safeToFixed } from '@/utils/format'
import type { NewsItem, MarketSentimentData } from '@/types'

const log = createLogger('News')

const router = useRouter()
const activeTab = ref('latest')
const newsList = ref<NewsItem[]>([])
const sentimentData = ref<MarketSentimentData | null>(null)
const loading = ref(false)
const { cancelAll } = useRequestCancel()
const { handleApiError } = useApiError()

const fgClass = computed(() => {
  if (!sentimentData.value) return ''
  const v = sentimentData.value.sentiment.fear_greed_index
  if (v >= 80) return 'fg-extreme-greed'
  if (v >= 60) return 'fg-greed'
  if (v >= 40) return 'fg-neutral'
  if (v >= 20) return 'fg-fear'
  return 'fg-extreme-fear'
})

async function fetchNews() {
  loading.value = true
  try {
    newsList.value = await api.news.latest(50)
  } catch (err) {
    handleApiError(err, '获取资讯失败')
    newsList.value = []
  } finally {
    loading.value = false
  }
}

async function fetchSentiment() {
  try {
    sentimentData.value = await api.news.sentiment()
  } catch (err) {
    handleApiError(err, '获取情绪数据失败')
    sentimentData.value = null
  }
}

function switchToSentiment() {
  activeTab.value = 'sentiment'
  if (!sentimentData.value) {
    fetchSentiment()
  }
}

function goToStock(symbol: string) {
  router.push(`/stock/${symbol}`)
}

function openUrl(url: string) {
  if (url) window.open(url, '_blank')
}

const UNIX_TO_MS = 1_000
const ONE_MINUTE_MS = 60_000
const ONE_HOUR_MS = 3_600_000
const ONE_DAY_MS = 86_400_000

function formatNewsTime(t: string | number): string {
  if (!t) return ''
  const ts = typeof t === 'string' ? parseInt(t, 10) : t
  if (isNaN(ts)) return String(t)
  const d = new Date(ts * UNIX_TO_MS)
  if (isNaN(d.getTime())) return String(t)
  const now = new Date()
  const diffMs = now.getTime() - d.getTime()
  if (diffMs < ONE_MINUTE_MS) return 'JUST NOW'
  if (diffMs < ONE_HOUR_MS) return Math.floor(diffMs / ONE_MINUTE_MS) + 'MIN AGO'
  if (diffMs < ONE_DAY_MS) return Math.floor(diffMs / ONE_HOUR_MS) + 'H AGO'
  const month = (d.getMonth() + 1).toString().padStart(2, '0')
  const day = d.getDate().toString().padStart(2, '0')
  const hour = d.getHours().toString().padStart(2, '0')
  const min = d.getMinutes().toString().padStart(2, '0')
  return `${month}-${day} ${hour}:${min}`
}

onMounted(fetchNews)

onUnmounted(cancelAll)
</script>

<style scoped>
.news-page {
  max-width: 960px;
  margin: 0 auto;
  display: grid;
  gap: var(--u4);
}

.tab-bar {
  display: flex;
  gap: 0;
  border-bottom: 1px solid var(--border-hair);
  overflow-x: auto;
  white-space: nowrap;
}

.tab-btn {
  padding: var(--u2) var(--u6);
  border: none;
  background: transparent;
  color: var(--text-tertiary);
  font-size: var(--fs-sm);
  font-weight: 500;
  font-family: var(--font-mono);
  cursor: pointer;
  position: relative;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  transition: color var(--dur-fast) var(--ease-mechanical);
}

.tab-btn::after {
  content: '';
  position: absolute;
  bottom: -1px;
  left: 0;
  right: 0;
  height: 2px;
  background: var(--accent);
  transform: scaleX(0);
  will-change: transform;
  transition: transform var(--dur-fast) var(--ease-mechanical);
}

.tab-btn:hover { color: var(--text-primary); }
.tab-btn.active { color: var(--accent); }
.tab-btn.active::after { transform: scaleX(1); }

.panel-empty {
  padding: var(--u8) var(--u4);
  text-align: center;
  color: var(--text-muted);
  font-size: var(--fs-xs);
  font-family: var(--font-mono);
  text-transform: uppercase;
  letter-spacing: 0.1em;
}

.blink-cursor { animation: blink 1s step-end infinite; }

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--u3) var(--u4);
  border-bottom: 1px solid var(--border-hair);
}

.panel-title {
  font-family: var(--font-mono);
  font-size: var(--fs-xs);
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: var(--text-tertiary);
}

.news-feed { display: grid; gap: 1px; background: var(--border-hair); }

.news-row {
  background: var(--bg-surface);
  padding: var(--u3) var(--u4);
  cursor: pointer;
  transition: background var(--dur-fast) var(--ease-mechanical);
}

.news-row:hover { background: var(--bg-overlay); }

.nr-body { display: grid; gap: var(--u2); }

.nr-top {
  display: flex;
  align-items: flex-start;
  gap: var(--u2);
}

.nr-title {
  font-size: var(--fs-base);
  color: var(--text-primary);
  line-height: 1.5;
  font-weight: 500;
}

.nr-meta {
  display: flex;
  align-items: center;
  gap: var(--u3);
  font-size: var(--fs-xs);
  color: var(--text-tertiary);
}

.nr-source { font-weight: 500; }
.nr-time { font-variant-numeric: tabular-nums; }
.nr-symbols { display: flex; gap: var(--u1); }

.sentiment-badge,
.stat-badge {
  font-size: var(--fs-3xs);
  font-weight: 700;
  padding: 1px 6px;
  border-radius: var(--r-md);
  font-family: var(--font-mono);
  text-transform: uppercase;
  letter-spacing: 0.08em;
  flex-shrink: 0;
}

.badge-bull { background: var(--fall-bg); color: var(--fall); }
.badge-bear { background: var(--rise-bg); color: var(--rise); }
.badge-neutral { background: var(--bg-plate); color: var(--text-tertiary); }

.sym-tag {
  font-size: var(--fs-3xs);
  padding: 1px 5px;
  border-radius: var(--r-md);
  background: var(--accent-muted);
  color: var(--accent);
  font-family: var(--font-mono);
  font-variant-numeric: tabular-nums;
  cursor: pointer;
  transition: opacity var(--dur-fast) var(--ease-mechanical);
}

.sym-tag:hover { opacity: 0.7; }

.fg-body {
  text-align: center;
  padding: var(--u6) var(--u4);
}

.fg-value {
  font-size: var(--fs-4xl);
  font-weight: 700;
  font-family: var(--font-mono);
  font-variant-numeric: tabular-nums;
  letter-spacing: -0.04em;
  line-height: 1;
}

.fg-extreme-greed { color: var(--fall); }
.fg-greed { color: var(--teal); }
.fg-neutral { color: var(--text-secondary); }
.fg-fear { color: var(--warn); }
.fg-extreme-fear { color: var(--rise); }

.fg-label {
  font-size: var(--fs-md);
  color: var(--text-secondary);
  margin: var(--u3) 0 var(--u6);
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  font-family: var(--font-mono);
}

.fg-bar-wrap { max-width: 480px; margin: 0 auto; }

.fg-bar-bg {
  height: 6px;
  background: linear-gradient(to right, var(--rise), var(--warn), var(--text-tertiary), var(--teal), var(--fall));
  border-radius: 3px;
  position: relative;
}

.fg-bar-fill {
  height: 100%;
  border-radius: 3px;
  opacity: 0.15;
  background: var(--bg-base);
}

.fg-bar-marker {
  position: absolute;
  top: -5px;
  width: 16px;
  height: 16px;
  border-radius: 8px;
  background: var(--text-primary);
  border: 3px solid var(--accent);
  transform: translateX(-50%);
}

.fg-bar-labels {
  display: flex;
  justify-content: space-between;
  font-size: var(--fs-3xs);
  color: var(--text-muted);
  margin-top: var(--u2);
  font-family: var(--font-mono);
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.sentiment-strip {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 1px;
  background: var(--border-hair);
}

.sent-cell {
  padding: var(--u4);
  display: flex;
  flex-direction: column;
  gap: var(--u2);
}

.sc-label {
  font-size: var(--fs-3xs);
  color: var(--text-tertiary);
  font-family: var(--font-mono);
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.sc-value {
  font-size: var(--fs-xl);
  font-weight: 700;
  color: var(--text-primary);
  font-variant-numeric: tabular-nums;
}

.val-rise { color: var(--rise); }
.val-fall { color: var(--fall); }

.stats-body { padding: var(--u4); }

.stats-row { display: flex; gap: var(--u3); margin-bottom: var(--u4); }

.hot-section { margin-top: var(--u4); }

.hot-label {
  font-size: var(--fs-3xs);
  color: var(--text-tertiary);
  font-family: var(--font-mono);
  text-transform: uppercase;
  letter-spacing: 0.1em;
  margin-bottom: var(--u2);
}

.hot-list { display: flex; flex-wrap: wrap; gap: var(--u2); }

.hot-tag {
  font-size: var(--fs-3xs);
  padding: 2px 8px;
  border-radius: var(--r-md);
  background: var(--accent-muted);
  color: var(--accent);
  font-family: var(--font-mono);
  font-variant-numeric: tabular-nums;
  cursor: pointer;
  transition: opacity var(--dur-fast) var(--ease-mechanical);
}

.hot-tag:hover { opacity: 0.7; }

@media (max-width: 768px) {
  .sentiment-strip { grid-template-columns: repeat(2, 1fr); }
}
</style>
