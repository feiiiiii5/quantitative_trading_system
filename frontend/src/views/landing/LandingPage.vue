<template>
  <div class="landing">
    <section class="hero">
      <div class="hero-bg">
        <div class="hero-grid" />
        <div class="hero-scanline" />
        <div class="hero-radial" />
      </div>
      <div class="hero-content anim-el" style="--delay: 0s">
        <div class="hero-badge">
          <span class="badge-dot" />
          <span class="badge-text">INDUSTRIAL-GRADE QUANT PLATFORM</span>
        </div>
        <h1 class="hero-title terminal-glow">QUANTCORE</h1>
        <p class="hero-subtitle">
          <span class="subtitle-line">DATA-DRIVEN DECISIONS</span>
          <span class="subtitle-sep">/</span>
          <span class="subtitle-line accent">AI-EMPOWERED TRADING</span>
        </p>
        <p class="hero-tagline">
          Multi-factor models, machine learning & real-time analytics — a full-stack quantitative toolkit for A-share markets
        </p>
        <div class="hero-actions">
          <router-link to="/dashboard" class="btn-primary">
            <span class="btn-prompt">&gt;</span> ENTER SYSTEM
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M5 12h14M12 5l7 7-7 7"/></svg>
          </router-link>
          <a href="#features" class="btn-secondary" @click.prevent="scrollToFeatures">
            LEARN MORE
          </a>
        </div>
      </div>
      <div class="hero-stats anim-el" style="--delay: 0.2s">
        <div class="stat-item">
          <span class="stat-value mono">{{ animatedStats.strategies }}</span>
          <span class="stat-label">STRATEGIES</span>
        </div>
        <div class="stat-divider" />
        <div class="stat-item">
          <span class="stat-value mono">{{ animatedStats.stocks }}<span class="stat-suffix">+</span></span>
          <span class="stat-label">A-SHARES</span>
        </div>
        <div class="stat-divider" />
        <div class="stat-item">
          <span class="stat-value mono">LIVE</span>
          <span class="stat-label">MARKET DATA</span>
        </div>
        <div class="stat-divider" />
        <div class="stat-item">
          <span class="stat-value mono">AI</span>
          <span class="stat-label">ANALYTICS</span>
        </div>
      </div>
    </section>

    <section id="features" class="features" ref="featuresRef">
      <div class="section-header anim-el">
        <span class="section-eyebrow">&gt; CORE CAPABILITIES</span>
        <h2 class="section-title">FROM DATA INGESTION TO STRATEGY EXECUTION</h2>
        <p class="section-sub">Full-stack quantitative tools covering the entire investment research pipeline</p>
      </div>
      <div class="feat-grid">
        <div
          v-for="(feat, i) in features"
          :key="i"
          class="feat-card anim-el"
          :style="{ '--delay': 0.08 * i + 's', '--feat-color': feat.color }"
        >
          <div class="feat-stripe" />
          <div class="feat-header">
            <div class="feat-icon-wrap">
              <svg v-if="feat.svg === 'chart'" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M3 3v18h18"/><path d="M7 16l4-8 4 4 6-10"/></svg>
              <svg v-else-if="feat.svg === 'filter'" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M22 3H2l8 9.46V19l4 2v-8.54L22 3z"/></svg>
              <svg v-else-if="feat.svg === 'layers'" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M12 2L2 7l10 5 10-5-10-5z"/><path d="M2 17l10 5 10-5"/><path d="M2 12l10 5 10-5"/></svg>
              <svg v-else-if="feat.svg === 'dollar'" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M12 2v20M17 5H9.5a3.5 3.5 0 000 7h5a3.5 3.5 0 010 7H6"/></svg>
            </div>
            <h3 class="feat-title">{{ feat.title }}</h3>
          </div>
          <p class="feat-desc">{{ feat.desc }}</p>
          <router-link :to="feat.link" class="feat-link">
            EXPLORE
            <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M5 12h14M12 5l7 7-7 7"/></svg>
          </router-link>
        </div>
      </div>
    </section>

    <section class="showcase">
      <div class="showcase-inner anim-el">
        <div class="showcase-content">
          <span class="section-eyebrow">&gt; TECH ARCHITECTURE</span>
          <h2 class="showcase-title">PERFORMANCE-BORN<br/>QUANT ENGINE</h2>
          <p class="showcase-desc">
            High-performance quant engine built on Python with MPS-accelerated training,
            built-in risk control and adaptive strategies — seamless from backtest to live trading.
          </p>
          <div class="showcase-features">
            <div class="sf-item" v-for="item in techFeatures" :key="item.label">
              <div class="sf-icon">
                <svg v-if="item.svg === 'bolt'" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>
                <svg v-else-if="item.svg === 'gear'" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 010 2.83 2 2 0 01-2.83 0l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-4 0v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83-2.83l.06-.06A1.65 1.65 0 004.68 15a1.65 1.65 0 00-1.51-1H3a2 2 0 010-4h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 012.83-2.83l.06.06A1.65 1.65 0 009 4.68a1.65 1.65 0 001-1.51V3a2 2 0 014 0v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 2.83l-.06.06A1.65 1.65 0 0019.4 9a1.65 1.65 0 001.51 1H21a2 2 0 010 4h-.09a1.65 1.65 0 00-1.51 1z"/></svg>
                <svg v-else-if="item.svg === 'shield'" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>
                <svg v-else-if="item.svg === 'chip'" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="4" y="4" width="16" height="16" rx="2"/><rect x="9" y="9" width="6" height="6"/><path d="M9 1v3M15 1v3M9 20v3M15 20v3M20 9h3M20 14h3M1 9h3M1 14h3"/></svg>
              </div>
              <div class="sf-text">
                <span class="sf-label">{{ item.label }}</span>
                <span class="sf-desc">{{ item.desc }}</span>
              </div>
            </div>
          </div>
        </div>
        <div class="showcase-visual">
          <div class="code-block">
            <div class="code-header">
              <span class="code-dot" style="background:#ff5f57" />
              <span class="code-dot" style="background:#febc2e" />
              <span class="code-dot" style="background:#28c840" />
              <span class="code-filename">strategy.py</span>
            </div>
            <pre class="code-content"><code><span class="code-kw">from</span> quantcore <span class="code-kw">import</span> Strategy, Signal

<span class="code-kw">class</span> <span class="code-cls">MomentumStrategy</span>(Strategy):
    <span class="code-kw">def</span> <span class="code-fn">generate_signal</span>(self, data):
        score = self.ml_scorer.predict(data)
        <span class="code-kw">if</span> score > <span class="code-num">0.8</span>:
            <span class="code-kw">return</span> Signal.BUY
        <span class="code-kw">elif</span> score < <span class="code-num">0.2</span>:
            <span class="code-kw">return</span> Signal.SELL
        <span class="code-kw">return</span> Signal.HOLD</code></pre>
          </div>
        </div>
      </div>
    </section>

    <section class="cta-section anim-el">
      <div class="cta-inner">
        <div class="cta-glow" />
        <h2 class="cta-title terminal-glow">INITIALIZE QUANT PIPELINE</h2>
        <p class="cta-desc">Zero installation — full functionality in your browser</p>
        <router-link to="/dashboard" class="btn-primary">
          <span class="btn-prompt">&gt;</span> LAUNCH NOW
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M5 12h14M12 5l7 7-7 7"/></svg>
        </router-link>
      </div>
    </section>

    <footer class="landing-footer">
      <div class="footer-inner">
        <div class="footer-brand">
          <span class="brand-glyph">&#9672;</span>
          <span class="brand-name">QuantCore</span>
        </div>
        <span class="footer-copy">&copy; 2025 QuantCore · Industrial-Grade Quantitative Trading System</span>
      </div>
    </footer>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, onUnmounted } from 'vue'

const featuresRef = ref<HTMLElement>()

const animatedStats = reactive({ strategies: 0, stocks: 0 })

const features = [
  {
    title: 'LIVE QUOTES',
    desc: 'Full A-share market coverage — 5000+ stocks with real-time K-lines, tick data & multi-dimensional technical indicators',
    svg: 'chart',
    color: '#2979ff', link: '/market',
  },
  {
    title: 'SMART SCREENER',
    desc: 'Multi-dimensional filtering across fundamentals, technicals & capital flow — precision targeting of investment opportunities',
    svg: 'filter',
    color: '#e040fb', link: '/screener',
  },
  {
    title: 'STRATEGY BACKTEST',
    desc: '12 quantitative strategies with one-click backtesting, custom parameters & AI-recommended optimal strategies',
    svg: 'layers',
    color: '#00e676', link: '/strategy',
  },
  {
    title: 'CAPITAL FLOW',
    desc: 'Track institutional capital movement, northbound flows & real-time sector-level money flow monitoring',
    svg: 'dollar',
    color: '#ffd600', link: '/moneyflow',
  },
]

const techFeatures = [
  {
    label: 'MPS ACCEL',
    desc: 'Apple Silicon native acceleration',
    svg: 'bolt',
  },
  {
    label: 'ADAPTIVE',
    desc: 'Auto-switch by market regime',
    svg: 'gear',
  },
  {
    label: 'RISK CTRL',
    desc: 'Real-time risk monitoring & alerts',
    svg: 'shield',
  },
  {
    label: 'MEM SAFE',
    desc: 'Dynamic memory management guard',
    svg: 'chip',
  },
]

const ANIMATION_DURATION_MS = 1_500
const COUNTER_DELAY_MS = 600
const TARGET_STRATEGIES = 12
const TARGET_STOCKS = 5_000

function animateCounters() {
  const startTime = performance.now()
  function tick(now: number) {
    const elapsed = now - startTime
    const progress = Math.min(elapsed / ANIMATION_DURATION_MS, 1)
    const eased = 1 - Math.pow(1 - progress, 3)
    animatedStats.strategies = Math.round(TARGET_STRATEGIES * eased)
    animatedStats.stocks = Math.round(TARGET_STOCKS * eased)
    if (progress < 1) requestAnimationFrame(tick)
  }
  requestAnimationFrame(tick)
}

function scrollToFeatures() {
  document.getElementById('features')?.scrollIntoView({ behavior: 'smooth' })
}

let scrollObserver: IntersectionObserver | null = null

function initScrollAnimations() {
  scrollObserver = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add('visible')
        }
      })
    },
    { threshold: 0.1 },
  )
  document.querySelectorAll('.anim-el').forEach((el) => scrollObserver!.observe(el))
}

let counterTimer: ReturnType<typeof setTimeout> | null = null

onMounted(() => {
  initScrollAnimations()
  counterTimer = setTimeout(animateCounters, COUNTER_DELAY_MS)
})

onUnmounted(() => {
  if (scrollObserver) scrollObserver.disconnect()
  if (counterTimer) clearTimeout(counterTimer)
})
</script>

<style scoped>
.landing {
  position: relative;
  overflow-x: hidden;
  background: linear-gradient(170deg, #050507 0%, #0d0d1a 100%);
  color: var(--text-primary);
}

.anim-el {
  opacity: 0;
  transform: translateY(20px);
  transition: opacity var(--dur-slow) var(--ease-out-expo),
              transform var(--dur-slow) var(--ease-out-expo);
  transition-delay: var(--delay, 0s);
}
.anim-el.visible {
  opacity: 1;
  transform: translateY(0);
}

.hero {
  position: relative;
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 64px 24px 32px;
  overflow: hidden;
}

.hero-bg {
  position: absolute;
  inset: 0;
  z-index: 0;
  pointer-events: none;
}

.hero-grid {
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(rgba(41, 121, 255, 0.025) 1px, transparent 1px),
    linear-gradient(90deg, rgba(41, 121, 255, 0.025) 1px, transparent 1px);
  background-size: 48px 48px;
}

.hero-scanline {
  position: absolute;
  inset: 0;
  background: repeating-linear-gradient(
    0deg,
    transparent,
    transparent 2px,
    rgba(255, 255, 255, 0.006) 2px,
    rgba(255, 255, 255, 0.006) 4px
  );
}

.hero-radial {
  position: absolute;
  inset: 0;
  background: radial-gradient(
    ellipse 80% 50% at 50% 30%,
    rgba(41, 121, 255, 0.04) 0%,
    transparent 70%
  );
}

.hero-content {
  position: relative;
  z-index: 1;
  max-width: 720px;
  text-align: center;
}

.hero-badge {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 6px 16px;
  border-radius: 4px;
  background: rgba(41, 121, 255, 0.06);
  border: 1px solid rgba(41, 121, 255, 0.15);
  margin-bottom: 32px;
}

.badge-dot {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: var(--fall);
  animation: statusPulse 2s ease-in-out infinite;
}

.badge-text {
  font-family: var(--font-mono);
  font-size: 10px;
  font-weight: 500;
  color: var(--accent);
  letter-spacing: 0.15em;
}

.hero-title {
  font-family: var(--font-mono);
  font-size: 56px;
  font-weight: 700;
  letter-spacing: -0.04em;
  line-height: 1;
  color: var(--text-primary);
  margin-bottom: 16px;
}

.hero-subtitle {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  margin-bottom: 20px;
  font-family: var(--font-mono);
  font-size: 14px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.subtitle-line {
  color: var(--text-secondary);
}

.subtitle-line.accent {
  color: var(--fall);
  text-shadow: 0 0 8px rgba(0, 230, 118, 0.3);
}

.subtitle-sep {
  color: var(--text-muted);
  font-weight: 300;
}

.hero-tagline {
  font-family: var(--font-mono);
  font-size: 12px;
  color: var(--text-tertiary);
  line-height: 1.7;
  max-width: 520px;
  margin: 0 auto 32px;
  letter-spacing: 0.04em;
}

.hero-actions {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 16px;
}

.btn-primary {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 12px 28px;
  border-radius: 4px;
  background: var(--accent);
  color: #ffffff;
  font-family: var(--font-mono);
  font-size: 12px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  text-decoration: none;
  transition: filter var(--dur-fast) var(--ease-mechanical),
              box-shadow var(--dur-fast) var(--ease-mechanical);
}

.btn-primary:hover {
  text-decoration: none;
  filter: brightness(1.15);
  box-shadow: 0 0 20px rgba(41, 121, 255, 0.25);
}

.btn-primary:active {
  transform: scale(0.98);
}

.btn-prompt {
  font-weight: 700;
  opacity: 0.7;
}

.btn-secondary {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 12px 24px;
  border-radius: 4px;
  background: transparent;
  color: var(--text-secondary);
  font-family: var(--font-mono);
  font-size: 12px;
  font-weight: 500;
  text-decoration: none;
  border: 1px solid var(--border-mid);
  text-transform: uppercase;
  letter-spacing: 0.08em;
  transition: border-color var(--dur-fast) var(--ease-mechanical),
              color var(--dur-fast) var(--ease-mechanical);
}

.btn-secondary:hover {
  text-decoration: none;
  border-color: var(--accent);
  color: var(--accent);
}

.hero-stats {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 32px;
  margin-top: 64px;
  padding-top: 32px;
  border-top: 1px solid var(--border-hair);
}

.stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}

.stat-value {
  font-family: var(--font-mono);
  font-variant-numeric: tabular-nums;
  font-size: 24px;
  font-weight: 700;
  color: var(--text-primary);
  letter-spacing: -0.02em;
}

.stat-suffix {
  font-family: var(--font-mono);
  font-size: 16px;
  font-weight: 600;
  color: var(--fall);
}

.stat-label {
  font-family: var(--font-mono);
  font-size: 9px;
  color: var(--text-tertiary);
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.stat-divider {
  width: 1px;
  height: 32px;
  background: var(--border-mid);
}

.features {
  position: relative;
  z-index: 1;
  padding: 64px 24px;
  max-width: 1200px;
  margin: 0 auto;
}

.section-header {
  text-align: center;
  margin-bottom: 48px;
}

.section-eyebrow {
  display: inline-block;
  font-family: var(--font-mono);
  font-size: 10px;
  font-weight: 500;
  color: var(--accent);
  letter-spacing: 0.15em;
  text-transform: uppercase;
  margin-bottom: 12px;
}

.section-title {
  font-family: var(--font-mono);
  font-size: 20px;
  font-weight: 700;
  color: var(--text-primary);
  letter-spacing: -0.02em;
  margin-bottom: 8px;
}

.section-sub {
  font-family: var(--font-mono);
  font-size: 12px;
  color: var(--text-tertiary);
  letter-spacing: 0.04em;
}

.feat-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
}

.feat-card {
  background: rgba(8, 8, 16, 0.6);
  border: 1px solid var(--border-mid);
  border-radius: 4px;
  padding: 24px 20px;
  position: relative;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  gap: 12px;
  transition: border-color var(--dur-fast) var(--ease-mechanical);
}

.feat-stripe {
  position: absolute;
  inset: 0;
  background-image: repeating-linear-gradient(
    45deg,
    transparent,
    transparent 4px,
    rgba(255, 255, 255, 0.015) 4px,
    rgba(255, 255, 255, 0.015) 5px
  );
  pointer-events: none;
  opacity: 0;
  transition: opacity var(--dur-fast) var(--ease-mechanical);
}

.feat-card:hover {
  border-color: var(--feat-color);
}

.feat-card:hover .feat-stripe {
  opacity: 1;
}

.feat-header {
  display: flex;
  align-items: center;
  gap: 12px;
}

.feat-icon-wrap {
  width: 40px;
  height: 40px;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: color-mix(in srgb, var(--feat-color) 8%, transparent);
  color: var(--feat-color);
  border: 1px solid color-mix(in srgb, var(--feat-color) 15%, transparent);
  flex-shrink: 0;
}

.feat-title {
  font-family: var(--font-mono);
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: var(--text-secondary);
}

.feat-desc {
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--text-tertiary);
  line-height: 1.6;
}

.feat-link {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-family: var(--font-mono);
  font-size: 10px;
  color: var(--accent);
  font-weight: 500;
  text-decoration: none;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  margin-top: auto;
  transition: gap var(--dur-fast) var(--ease-mechanical);
}

.feat-link:hover {
  text-decoration: none;
  gap: 8px;
}

.showcase {
  position: relative;
  z-index: 1;
  padding: 64px 24px;
}

.showcase-inner {
  max-width: 1200px;
  margin: 0 auto;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 48px;
  align-items: center;
}

.showcase-content {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.showcase-title {
  font-family: var(--font-mono);
  font-size: 24px;
  font-weight: 700;
  letter-spacing: -0.03em;
  line-height: 1.2;
  color: var(--text-primary);
}

.showcase-desc {
  font-family: var(--font-mono);
  font-size: 12px;
  color: var(--text-tertiary);
  line-height: 1.7;
}

.showcase-features {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.sf-item {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 12px;
  background: rgba(8, 8, 16, 0.4);
  border: 1px solid var(--border-hair);
  border-radius: 4px;
  border-left: 2px solid var(--accent);
}

.sf-icon {
  width: 28px;
  height: 28px;
  border-radius: 4px;
  background: var(--accent-muted);
  color: var(--accent);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.sf-text {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.sf-label {
  font-family: var(--font-mono);
  font-size: 10px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--text-secondary);
}

.sf-desc {
  font-family: var(--font-mono);
  font-size: 10px;
  color: var(--text-tertiary);
}

.showcase-visual {
  display: flex;
  justify-content: center;
}

.code-block {
  width: 100%;
  max-width: 460px;
  background: rgba(5, 5, 7, 0.8);
  border: 1px solid var(--border-mid);
  border-radius: 4px;
  overflow: hidden;
  position: relative;
}

.code-block::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 1px;
  background: linear-gradient(90deg, transparent, var(--accent), transparent);
  opacity: 0.3;
}

.code-header {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 12px 16px;
  border-bottom: 1px solid var(--border-hair);
  background: rgba(5, 5, 7, 0.6);
}

.code-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
}

.code-filename {
  margin-left: 8px;
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--text-muted);
}

.code-content {
  padding: 16px;
  font-family: var(--font-mono);
  font-size: 12px;
  line-height: 1.7;
  color: var(--text-muted);
  overflow-x: auto;
}

.code-kw { color: var(--fall); }
.code-cls { color: var(--accent); }
.code-fn { color: var(--accent); }
.code-num { color: var(--warn); }

.cta-section {
  position: relative;
  z-index: 1;
  padding: 64px 24px;
}

.cta-inner {
  max-width: 640px;
  margin: 0 auto;
  text-align: center;
  padding: 48px 32px;
  background: rgba(8, 8, 16, 0.6);
  border: 1px solid var(--border-mid);
  border-radius: 4px;
  position: relative;
  overflow: hidden;
}

.cta-glow {
  position: absolute;
  top: -1px;
  left: 20%;
  right: 20%;
  height: 1px;
  background: linear-gradient(90deg, transparent, var(--accent), transparent);
  opacity: 0.4;
}

.cta-title {
  font-family: var(--font-mono);
  font-size: 20px;
  font-weight: 700;
  color: var(--text-primary);
  letter-spacing: -0.02em;
  margin-bottom: 12px;
  position: relative;
}

.cta-desc {
  font-family: var(--font-mono);
  font-size: 12px;
  color: var(--text-tertiary);
  margin-bottom: 24px;
  position: relative;
}

.cta-section .btn-primary {
  position: relative;
}

.landing-footer {
  position: relative;
  z-index: 1;
  border-top: 1px solid var(--border-hair);
  padding: 20px 24px;
}

.footer-inner {
  max-width: 1200px;
  margin: 0 auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.footer-brand {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
}

.brand-glyph {
  color: var(--accent);
  font-size: 16px;
}

.brand-name {
  font-family: var(--font-mono);
  letter-spacing: -0.02em;
  color: var(--accent);
  text-shadow: 0 0 12px rgba(41, 121, 255, 0.3);
}

.footer-copy {
  font-family: var(--font-mono);
  font-size: 10px;
  color: var(--text-tertiary);
  letter-spacing: 0.04em;
}

@media (max-width: 1024px) {
  .feat-grid {
    grid-template-columns: repeat(2, 1fr);
  }
  .showcase-inner {
    grid-template-columns: 1fr;
    gap: 32px;
  }
  .showcase-visual {
    order: -1;
  }
  .showcase-features {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .hero-title {
    font-size: 36px;
  }
  .hero-subtitle {
    flex-direction: column;
    gap: 4px;
  }
  .subtitle-sep {
    display: none;
  }
  .hero-tagline {
    font-size: 11px;
  }
  .feat-grid {
    grid-template-columns: 1fr;
  }
  .hero-stats {
    gap: 20px;
    flex-wrap: wrap;
  }
  .stat-divider {
    display: none;
  }
  .hero-actions {
    flex-direction: column;
  }
  .code-block {
    max-width: 100%;
  }
  .showcase-features {
    grid-template-columns: 1fr;
  }
}
</style>
