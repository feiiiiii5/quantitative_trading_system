import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  { path: '/', name: 'Dashboard', component: () => import('../views/Dashboard.vue'), meta: { title: '市场总览', icon: 'grid' } },
  { path: '/market', name: 'Market', component: () => import('../views/Market.vue'), meta: { title: '市场浏览', icon: 'list' } },
  { path: '/stock/:symbol', name: 'StockDetail', component: () => import('../views/StockDetail.vue'), meta: { title: '股票详情', icon: 'chart' } },
  { path: '/strategy', name: 'Strategy', component: () => import('../views/Strategy.vue'), meta: { title: '策略回测', icon: 'strategy' } },
  { path: '/portfolio', name: 'Portfolio', component: () => import('../views/Portfolio.vue'), meta: { title: '组合管理', icon: 'portfolio' } },
  { path: '/watchlist', name: 'Watchlist', component: () => import('../views/Watchlist.vue'), meta: { title: '自选股', icon: 'star' } },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to) => {
  document.title = `${to.meta.title || 'QuantCore'} - QuantCore`
})

export default router
