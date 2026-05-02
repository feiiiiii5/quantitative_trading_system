import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      redirect: '/dashboard',
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
      path: '/portfolio',
      name: 'Portfolio',
      component: () => import('@/views/portfolio/PortfolioPage.vue'),
    },
    {
      path: '/watchlist',
      name: 'Watchlist',
      component: () => import('@/views/watchlist/WatchlistPage.vue'),
    },
  ],
})

export default router
