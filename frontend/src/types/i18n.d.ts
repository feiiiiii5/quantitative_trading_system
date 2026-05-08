declare module 'vue-i18n' {
  export interface DefineLocaleMessage {
    common: {
      retry: string
      loading: string
      noData: string
      confirm: string
      cancel: string
      save: string
      delete: string
      edit: string
      close: string
      search: string
      export: string
      refresh: string
      more: string
      all: string
    }
    error: {
      requestFailed: string
      networkError: string
      serverError: string
      unknown: string
      componentRendering: string
      marketOverviewFailed: string
      marketStatusFailed: string
      heatmapFailed: string
      anomalyDataFailed: string
      northboundDataFailed: string
      watchlistFetchFailed: string
      watchlistAddFailed: string
      watchlistRemoveFailed: string
      alertFetchFailed: string
      accountFetchFailed: string
      riskAnalysisFailed: string
      equityCurveFailed: string
      strategyListFailed: string
      backtestRunFailed: string
      backtestCompareFailed: string
      loginFailed: string
      authCheckFailed: string
      klineFetchFailed: string
      rateLimited: string
    }
    nav: {
      dashboard: string
      market: string
      stock: string
      strategy: string
      portfolio: string
      watchlist: string
      chip: string
      moneyFlow: string
      sector: string
      news: string
      screener: string
      alerts: string
      optimizer: string
      factorLab: string
      tca: string
      ml: string
    }
    shortcut: {
      goToDashboard: string
      goToMarket: string
      goToStrategy: string
      goToPortfolio: string
      goToWatchlist: string
      focusSearch: string
      blurActive: string
    }
    anomaly: {
      volume_spike: string
      price_spike: string
      rapid_rise: string
      rapid_fall: string
      price_above: string
      price_below: string
      change_pct_above: string
      change_pct_below: string
      riskBlocked: string
    }
    pwa: {
      installTitle: string
      installButton: string
      installDismiss: string
      offlineTitle: string
    }
  }
}
