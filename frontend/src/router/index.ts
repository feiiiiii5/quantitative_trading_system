import { createRouter, createWebHistory } from 'vue-router'
import StockDetail from '../views/StockDetail.vue'
import Backtest from '../views/Backtest.vue'
import Strategy from '../views/Strategy.vue'
import Portfolio from '../views/Portfolio.vue'
import Dashboard from '../views/Dashboard.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: '/stock/600519' },
    { path: '/dashboard', name: 'Dashboard', component: Dashboard },
    { path: '/stock/:symbol', name: 'StockDetail', component: StockDetail, props: true },
    { path: '/backtest', name: 'Backtest', component: Backtest },
    { path: '/strategy', name: 'Strategy', component: Strategy },
    { path: '/portfolio', name: 'Portfolio', component: Portfolio },
  ]
})

export default router
