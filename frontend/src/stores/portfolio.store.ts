import { defineStore } from 'pinia'
import { api } from '../api'

export const usePortfolioStore = defineStore('portfolio', {
  state: () => ({
    account: null as any,
    positions: [] as any[],
    orders: [] as any[],
    history: [] as any[],
    loading: false,
  }),
  actions: {
    async fetchAccount() {
      this.loading = true
      try {
        const data = await api.getAccount()
        if (data) this.account = data
      } catch (e) {
        console.error('Fetch account error:', e)
      } finally {
        this.loading = false
      }
    },
    async executeBuy(symbol: string, price: number, shares: number, options: any = {}) {
      try {
        const result = await api.buy(symbol, price, shares, options)
        if (result) {
          await this.fetchAccount()
        }
        return result
      } catch (e) {
        console.error('Execute buy error:', e)
        return null
      }
    },
    async executeSell(symbol: string, price: number, shares?: number, reason = 'manual') {
      try {
        const result = await api.sell(symbol, price, shares, reason)
        if (result) {
          await this.fetchAccount()
        }
        return result
      } catch (e) {
        console.error('Execute sell error:', e)
        return null
      }
    },
    async refreshPrices() {
      if (!this.account?.positions?.length) return
      try {
        const symbols = this.account.positions.map((p: any) => p.symbol)
        const quotes = await api.getRealtimeBatch(symbols)
        if (quotes && this.account.positions) {
          this.account.positions = this.account.positions.map((p: any) => ({
            ...p,
            current_price: quotes[p.symbol]?.price || p.current_price,
            change_pct: quotes[p.symbol]?.change_pct || p.change_pct,
          }))
        }
      } catch (e) {
        console.error('Refresh prices error:', e)
      }
    },
  },
})
