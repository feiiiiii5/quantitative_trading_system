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
      path: '/sector',
      name: 'Sector',
      component: () => import('@/views/sector/SectorPage.vue'),
    },
  ],
})

export default router
