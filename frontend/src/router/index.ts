import { createRouter, createWebHistory } from 'vue-router'

const Dashboard = () => import('../views/Dashboard.vue')
const Market = () => import('../views/Market.vue')
const StrategyIntro = () => import('../views/StrategyIntro.vue')
const Strategy = () => import('../views/Strategy.vue')
const Portfolio = () => import('../views/Portfolio.vue')
const Watchlist = () => import('../views/Watchlist.vue')
const StockDetail = () => import('../views/StockDetail.vue')

const routes = [
  { path: '/', name: 'Dashboard', component: Dashboard },
  { path: '/market', name: 'Market', component: Market },
  { path: '/strategy-intro', name: 'StrategyIntro', component: StrategyIntro },
  { path: '/strategy', name: 'Strategy', component: Strategy },
  { path: '/portfolio', name: 'Portfolio', component: Portfolio },
  { path: '/watchlist', name: 'Watchlist', component: Watchlist },
  { path: '/stock/:code', name: 'StockDetail', component: StockDetail },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
