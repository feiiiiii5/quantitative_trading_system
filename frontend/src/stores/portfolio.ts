import { defineStore } from 'pinia'
import { ref } from 'vue'
import { api } from '@/api'
import type { AccountInfo, PortfolioRisk, PortfolioEquity } from '@/types'

export const usePortfolioStore = defineStore('portfolio', () => {
  const account = ref<AccountInfo | null>(null)
  const riskAnalysis = ref<PortfolioRisk | null>(null)
  const equityCurve = ref<PortfolioEquity | null>(null)
  const loading = ref(false)

  async function fetchAccount() {
    try {
      account.value = await api.trading.account()
    } catch (e) {
      console.error('Fetch account error:', e)
    }
  }

  async function fetchRiskAnalysis(symbols: string[]) {
    try {
      riskAnalysis.value = await api.portfolio.riskAnalysis(symbols)
    } catch (e) {
      console.error('Fetch risk analysis error:', e)
    }
  }

  async function fetchEquityCurve(symbols: string[]) {
    try {
      equityCurve.value = await api.portfolio.equity(symbols)
    } catch (e) {
      console.error('Fetch equity curve error:', e)
    }
  }

  return { account, riskAnalysis, equityCurve, loading, fetchAccount, fetchRiskAnalysis, fetchEquityCurve }
})
