<template>
  <div class="strategy">
    <aside class="sidebar">
      <div class="logo">
        <svg width="32" height="32" viewBox="0 0 32 32" fill="none">
          <path d="M4 24L12 12L20 20L28 4" stroke="url(#logo-gradient)" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>
          <defs>
            <linearGradient id="logo-gradient" x1="4" y1="24" x2="28" y2="4">
              <stop stop-color="#00d4aa"/>
              <stop offset="1" stop-color="#0ea5e9"/>
            </linearGradient>
          </defs>
        </svg>
        <span class="logo-text">Quant</span>
      </div>
      <nav class="nav">
        <router-link
          v-for="item in navItems"
          :key="item.path"
          :to="item.path"
          class="nav-item"
          :class="{ active: $route.path === item.path }"
        >
          <component :is="iconMap[item.icon]" :size="20" />
          <span class="nav-label">{{ item.label }}</span>
        </router-link>
      </nav>
    </aside>

    <main class="main">
      <header class="header">
        <h1 class="page-title">策略管理</h1>
        <button class="create-btn" @click="showCreate = true">
          <IconPlus :size="16" />
          <span>新建策略</span>
        </button>
      </header>

      <div class="content">
        <div class="strategy-grid">
          <div v-for="s in strategies" :key="s.name" class="strategy-card">
            <div class="card-header">
              <div class="strategy-icon" :class="s.risk_level">
                <component :is="s.icon === 'IconFire' ? IconFire : IconBarChart" :size="24" />
              </div>
              <div class="strategy-actions">
                <button class="action-btn" @click="editStrategy(s)"><IconEdit :size="16" /></button>
                <button class="action-btn" @click="deleteStrategy(s)"><IconDelete :size="16" /></button>
              </div>
            </div>
            <h3 class="strategy-name">{{ s.name }}</h3>
            <p class="strategy-desc">{{ s.description }}</p>
            <div class="strategy-tags">
              <span class="tag" :class="s.risk_level">{{ s.risk_level === 'low' ? '低风险' : s.risk_level === 'medium' ? '中风险' : '高风险' }}</span>
              <span class="tag">{{ s.market }}</span>
            </div>
            <div class="strategy-metrics">
              <div class="metric">
                <span class="metric-label">年化收益</span>
                <span class="metric-value" :class="s.annual_return >= 0 ? 'text-green' : 'text-red'">{{ s.annual_return }}%</span>
              </div>
              <div class="metric">
                <span class="metric-label">最大回撤</span>
                <span class="metric-value text-red">{{ s.max_drawdown }}%</span>
              </div>
              <div class="metric">
                <span class="metric-label">夏普比率</span>
                <span class="metric-value">{{ s.sharpe }}</span>
              </div>
            </div>
            <div class="card-footer">
              <button class="run-btn" @click="runStrategy(s)">运行回测</button>
            </div>
          </div>
        </div>
      </div>
    </main>

    <!-- Create Modal -->
    <div v-if="showCreate" class="modal-overlay" @click="showCreate = false">
      <div class="modal" @click.stop>
        <div class="modal-header">
          <h3>新建策略</h3>
          <button class="close-btn" @click="showCreate = false"><IconClose :size="16" /></button>
        </div>
        <div class="modal-body">
          <div class="form-group">
            <label>策略名称</label>
            <input v-model="newStrategy.name" type="text" class="form-input" placeholder="输入策略名称" />
          </div>
          <div class="form-group">
            <label>策略描述</label>
            <textarea v-model="newStrategy.description" class="form-input" rows="3" placeholder="输入策略描述"></textarea>
          </div>
          <div class="form-row">
            <div class="form-group">
              <label>风险等级</label>
              <select v-model="newStrategy.risk_level" class="form-input">
                <option value="low">低风险</option>
                <option value="medium">中风险</option>
                <option value="high">高风险</option>
              </select>
            </div>
            <div class="form-group">
              <label>市场</label>
              <select v-model="newStrategy.market" class="form-input">
                <option value="A股">A股</option>
                <option value="港股">港股</option>
                <option value="美股">美股</option>
              </select>
            </div>
          </div>
          <div class="form-group">
            <label>策略代码</label>
            <textarea v-model="newStrategy.code" class="form-input code-editor" rows="10" placeholder="输入Python策略代码"></textarea>
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn-secondary" @click="showCreate = false">取消</button>
          <button class="btn-primary" @click="createStrategy">创建</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { IconHome, IconBarChart, IconThunderbolt, IconDashboard, IconPlus, IconEdit, IconDelete, IconClose, IconFire } from '@arco-design/web-vue/es/icon'

const router = useRouter()
const showCreate = ref(false)
const newStrategy = ref({ name: '', description: '', risk_level: 'medium', market: 'A股', code: '' })

const navItems = [
  { path: '/dashboard', icon: 'IconHome', label: '首页' },
  { path: '/backtest', icon: 'IconBarChart', label: '回测' },
  { path: '/strategy', icon: 'IconThunderbolt', label: '策略' },
  { path: '/portfolio', icon: 'IconDashboard', label: '组合' },
]

const iconMap: Record<string, any> = { IconHome, IconBarChart, IconThunderbolt, IconDashboard }

const strategies = ref([
  { name: '双均线交叉', description: '基于短期和长期移动平均线的交叉信号', risk_level: 'medium', market: 'A股', annual_return: 15.2, max_drawdown: -12.5, sharpe: 1.35, icon: 'IconFire' },
  { name: 'MACD动量', description: '利用MACD指标判断趋势动量', risk_level: 'medium', market: 'A股', annual_return: 18.7, max_drawdown: -15.3, sharpe: 1.28, icon: 'IconBarChart' },
  { name: '布林带突破', description: '基于布林带上下轨的突破策略', risk_level: 'high', market: 'A股', annual_return: 22.1, max_drawdown: -20.8, sharpe: 1.15, icon: 'IconFire' },
  { name: '均值回归', description: '价格偏离均值后的回归策略', risk_level: 'low', market: 'A股', annual_return: 8.5, max_drawdown: -6.2, sharpe: 1.52, icon: 'IconBarChart' },
])

function createStrategy() {
  strategies.value.push({
    ...newStrategy.value,
    annual_return: 0,
    max_drawdown: 0,
    sharpe: 0,
    icon: 'IconFire'
  })
  showCreate.value = false
  newStrategy.value = { name: '', description: '', risk_level: 'medium', market: 'A股', code: '' }
}

function editStrategy(s: any) {
  console.log('编辑策略', s)
}

function deleteStrategy(s: any) {
  strategies.value = strategies.value.filter(item => item.name !== s.name)
}

function runStrategy(s: any) {
  router.push('/backtest')
}
</script>

<style scoped>
.strategy {
  display: flex;
  height: 100vh;
  background: var(--bg-primary);
}

.sidebar {
  width: 200px;
  background: var(--bg-secondary);
  border-right: 1px solid var(--border-color);
  display: flex;
  flex-direction: column;
  padding: 20px 0;
}

.logo {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 0 20px 30px;
}

.logo-text {
  font-size: 20px;
  font-weight: 700;
  background: linear-gradient(135deg, var(--accent-primary), var(--accent-secondary));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.nav {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 0 12px;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  border-radius: var(--radius-md);
  color: var(--text-secondary);
  text-decoration: none;
  transition: all 0.2s;
  font-size: 14px;
}

.nav-item:hover {
  background: var(--bg-tertiary);
  color: var(--text-primary);
}

.nav-item.active {
  background: linear-gradient(135deg, rgba(0, 212, 170, 0.15), rgba(14, 165, 233, 0.15));
  color: var(--accent-primary);
  border: 1px solid rgba(0, 212, 170, 0.2);
}

.main {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.header {
  height: 64px;
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--border-color);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
}

.page-title {
  font-size: 20px;
  font-weight: 600;
  color: var(--text-primary);
}

.create-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 20px;
  background: linear-gradient(135deg, var(--accent-primary), var(--accent-secondary));
  border: none;
  border-radius: var(--radius-sm);
  color: white;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.create-btn:hover {
  opacity: 0.9;
  transform: translateY(-1px);
}

.content {
  flex: 1;
  padding: 24px;
  overflow-y: auto;
}

.strategy-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(360px, 1fr));
  gap: 20px;
}

.strategy-card {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  padding: 24px;
  transition: all 0.2s;
}

.strategy-card:hover {
  border-color: var(--bg-hover);
  transform: translateY(-2px);
  box-shadow: var(--shadow-md);
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.strategy-icon {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
}

.strategy-icon.low {
  background: linear-gradient(135deg, #00d4aa, #0ea5e9);
}

.strategy-icon.medium {
  background: linear-gradient(135deg, #f59e0b, #ef4444);
}

.strategy-icon.high {
  background: linear-gradient(135deg, #ef4444, #dc2626);
}

.strategy-actions {
  display: flex;
  gap: 8px;
}

.action-btn {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg-tertiary);
  border: none;
  border-radius: var(--radius-sm);
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.2s;
}

.action-btn:hover {
  background: var(--bg-hover);
  color: var(--text-primary);
}

.strategy-name {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 8px;
}

.strategy-desc {
  font-size: 13px;
  color: var(--text-secondary);
  margin-bottom: 16px;
  line-height: 1.5;
}

.strategy-tags {
  display: flex;
  gap: 8px;
  margin-bottom: 16px;
}

.tag {
  padding: 4px 10px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;
  background: var(--bg-tertiary);
  color: var(--text-secondary);
}

.tag.low {
  background: rgba(0, 212, 170, 0.15);
  color: var(--accent-primary);
}

.tag.medium {
  background: rgba(245, 158, 11, 0.15);
  color: var(--accent-warning);
}

.tag.high {
  background: rgba(239, 68, 68, 0.15);
  color: var(--accent-danger);
}

.strategy-metrics {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  padding: 16px 0;
  border-top: 1px solid var(--border-color);
  border-bottom: 1px solid var(--border-color);
  margin-bottom: 16px;
}

.metric {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.metric-label {
  font-size: 12px;
  color: var(--text-muted);
}

.metric-value {
  font-size: 16px;
  font-weight: 600;
  font-family: 'JetBrains Mono', monospace;
}

.card-footer {
  display: flex;
  justify-content: flex-end;
}

.run-btn {
  padding: 8px 20px;
  background: var(--accent-primary);
  border: none;
  border-radius: var(--radius-sm);
  color: white;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.run-btn:hover {
  opacity: 0.9;
}

.text-green {
  color: var(--accent-primary);
}

.text-red {
  color: var(--accent-danger);
}

/* Modal */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  backdrop-filter: blur(4px);
}

.modal {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  width: 560px;
  max-height: 80vh;
  overflow-y: auto;
  box-shadow: var(--shadow-lg);
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 24px;
  border-bottom: 1px solid var(--border-color);
}

.modal-header h3 {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
}

.close-btn {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: none;
  color: var(--text-secondary);
  cursor: pointer;
  border-radius: var(--radius-sm);
}

.close-btn:hover {
  background: var(--bg-tertiary);
  color: var(--text-primary);
}

.modal-body {
  padding: 24px;
}

.form-group {
  margin-bottom: 20px;
}

.form-group label {
  display: block;
  font-size: 13px;
  color: var(--text-secondary);
  margin-bottom: 8px;
}

.form-input {
  width: 100%;
  height: 40px;
  background: var(--bg-tertiary);
  border: 1px solid transparent;
  border-radius: var(--radius-sm);
  padding: 0 12px;
  color: var(--text-primary);
  font-size: 14px;
  transition: all 0.2s;
}

.form-input:focus {
  outline: none;
  border-color: var(--accent-primary);
}

textarea.form-input {
  height: auto;
  padding: 12px;
  resize: vertical;
}

.code-editor {
  font-family: 'JetBrains Mono', monospace;
  font-size: 13px;
  line-height: 1.6;
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 16px 24px;
  border-top: 1px solid var(--border-color);
}

.btn-secondary {
  padding: 10px 20px;
  background: var(--bg-tertiary);
  border: none;
  border-radius: var(--radius-sm);
  color: var(--text-secondary);
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-secondary:hover {
  background: var(--bg-hover);
  color: var(--text-primary);
}

.btn-primary {
  padding: 10px 20px;
  background: linear-gradient(135deg, var(--accent-primary), var(--accent-secondary));
  border: none;
  border-radius: var(--radius-sm);
  color: white;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-primary:hover {
  opacity: 0.9;
}

@media (max-width: 768px) {
  .sidebar {
    width: 64px;
  }
  .logo-text, .nav-label {
    display: none;
  }
  .nav-item {
    justify-content: center;
    padding: 12px;
  }
  .strategy-grid {
    grid-template-columns: 1fr;
  }
}
</style>
