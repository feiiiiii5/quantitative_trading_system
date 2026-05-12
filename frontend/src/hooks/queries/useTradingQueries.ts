import { useQuery } from '@tanstack/react-query';
import { apiGet } from '@/api/client';

export const tradingKeys = {
  all: ['trading'] as const,
  account: () => [...tradingKeys.all, 'account'] as const,
  history: () => [...tradingKeys.all, 'history'] as const,
  analytics: () => [...tradingKeys.all, 'analytics'] as const,
  dailyPnl: () => [...tradingKeys.all, 'daily-pnl'] as const,
};

export function useTradingAccount() {
  return useQuery({
    queryKey: tradingKeys.account(),
    queryFn: () => apiGet<{
      cash: number;
      total_value: number;
      daily_pnl: number;
      positions: Array<{ symbol: string; shares: number; avg_cost: number; current_price: number }>;
    }>('/trading/account'),
    staleTime: 10_000,
  });
}

export function useTradingHistory() {
  return useQuery({
    queryKey: tradingKeys.history(),
    queryFn: () => apiGet<{
      trades: Array<{
        id: string; symbol: string; name: string; action: string;
        shares: number; price: number; amount: number; timestamp: string;
      }>;
      total: number;
    }>('/trading/history'),
    staleTime: 15_000,
  });
}

export function useTradingAnalytics() {
  return useQuery({
    queryKey: tradingKeys.analytics(),
    queryFn: () => apiGet<Record<string, unknown>>('/trading/analytics'),
    staleTime: 60_000,
  });
}
