import { createRouter, createWebHistory } from 'vue-router'
import NProgress from 'nprogress'

const JWT_S_TO_MS = 1_000

NProgress.configure({ showSpinner: false, trickleSpeed: 200, minimum: 0.15 })

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/login',
      name: 'Login',
      component: () => import('@/views/auth/LoginPage.vue'),
      meta: { public: true },
    },
    {
      path: '/',
      name: 'Landing',
      component: () => import('@/views/landing/LandingPage.vue'),
      meta: { public: true },
    },
    {
      path: '/dashboard',
      name: 'Dashboard',
      component: () => import('@/views/dashboard/DashboardPage.vue'),
    },
    {
      path: '/market',
      name: 'Market',
      component: () => import('@/views/market/MarketPage.vue'),
    },
    {
      path: '/stock/:symbol',
      name: 'StockDetail',
      component: () => import('@/views/stock/StockDetailPage.vue'),
      props: true,
    },
    {
      path: '/strategy',
      name: 'StrategyIntro',
      component: () => import('@/views/strategy/StrategyIntroPage.vue'),
    },
    {
      path: '/strategy/run',
      name: 'StrategyRun',
      component: () => import('@/views/strategy/StrategyRunPage.vue'),
    },
    {
      path: '/strategy/dashboard',
      name: 'StrategyDashboard',
      component: () => import('@/views/strategy/StrategyDashboardPage.vue'),
    },
    {
      path: '/optimizer',
      name: 'Optimizer',
      component: () => import('@/views/optimizer/OptimizerPage.vue'),
    },
    {
      path: '/factor-lab',
      name: 'FactorLab',
      component: () => import('@/views/factor/FactorLabPage.vue'),
    },
    {
      path: '/tca',
      name: 'TCA',
      component: () => import('@/views/tca/TcaPage.vue'),
    },
    {
      path: '/ml',
      name: 'ML',
      component: () => import('@/views/ml/MlPage.vue'),
    },
    {
      path: '/portfolio',
      name: 'Portfolio',
      component: () => import('@/views/portfolio/PortfolioPage.vue'),
    },
    {
      path: '/watchlist',
      name: 'Watchlist',
      component: () => import('@/views/watchlist/WatchlistPage.vue'),
    },
    {
      path: '/news',
      name: 'News',
      component: () => import('@/views/news/NewsPage.vue'),
    },
    {
      path: '/screener',
      name: 'Screener',
      component: () => import('@/views/screener/ScreenerPage.vue'),
    },
    {
      path: '/moneyflow',
      name: 'MoneyFlow',
      component: () => import('@/views/moneyflow/MoneyFlowPage.vue'),
    },
    {
      path: '/chip',
      name: 'Chip',
      component: () => import('@/views/chip/ChipPage.vue'),
    },
    {
      path: '/chip/:symbol',
      name: 'ChipDetail',
      component: () => import('@/views/chip/ChipPage.vue'),
      props: true,
    },
    {
      path: '/alerts',
      name: 'Alerts',
      component: () => import('@/views/alerts/AlertsPage.vue'),
    },
    {
      path: '/sector',
      name: 'Sector',
      component: () => import('@/views/sector/SectorPage.vue'),
    },
    {
      path: '/:pathMatch(.*)*',
      name: 'NotFound',
      component: () => import('@/views/NotFoundPage.vue'),
      meta: { public: true },
    },
  ],
})

router.beforeEach((to) => {
  NProgress.start()
  const token = localStorage.getItem('auth_token')
  if (!to.meta?.public && !token) {
    return { name: 'Login' }
  }
  if (token && !to.meta?.public) {
    try {
      const payload = JSON.parse(atob(token.split('.')[1]))
      if (payload.exp && payload.exp * JWT_S_TO_MS < Date.now()) {
        localStorage.removeItem('auth_token')
        return { name: 'Login' }
      }
    } catch {
      localStorage.removeItem('auth_token')
      return { name: 'Login' }
    }
  }
})

router.afterEach(() => {
  NProgress.done()
})

if (typeof document.startViewTransition === 'function') {
  router.beforeEach((to, from) => {
    if (from.name === to.name) return
    return new Promise<void>((resolve) => {
      document.startViewTransition(async () => {
        resolve()
        await new Promise<void>((r) => { requestAnimationFrame(() => r()) })
      })
    })
  })
}

export default router
