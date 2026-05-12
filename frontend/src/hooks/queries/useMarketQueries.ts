import { useQuery, useQueries } from '@tanstack/react-query';
import { apiGet } from '@/api/client';
import type { IndexData, StockData } from '@/types';

export const marketKeys = {
  all: ['market'] as const,
  overview: () => [...marketKeys.all, 'overview'] as const,
  stocks: (market?: string) => [...marketKeys.all, 'stocks', market] as const,
  indices: () => [...marketKeys.all, 'indices'] as const,
  sectors: () => [...marketKeys.all, 'sectors'] as const,
  breadth: (symbols: string) => [...marketKeys.all, 'breadth', symbols] as const,
};

export function useMarketOverview() {
  return useQuery({
    queryKey: marketKeys.overview(),
    queryFn: () => apiGet<{
      indices: IndexData[];
      market_breadth: { up: number; down: number; flat: number };
      total_volume: number;
      turnover: number;
      sentiment: string;
    }>('/market/overview'),
    staleTime: 15_000,
  });
}

export function useMarketStocks(market: string = 'A') {
  return useQuery({
    queryKey: marketKeys.stocks(market),
    queryFn: () => apiGet<StockData[]>('/market/stocks', { market }),
    staleTime: 30_000,
  });
}

export function useMarketIndices() {
  return useQuery({
    queryKey: marketKeys.indices(),
    queryFn: () => apiGet<IndexData[]>('/market/overview'),
    select: (data) => data?.indices ?? [],
    staleTime: 15_000,
  });
}

export function useMarketSectors() {
  return useQuery({
    queryKey: marketKeys.sectors(),
    queryFn: () => apiGet<Record<string, { name: string; change_pct: number; stocks: string[] }>>('/market/heatmap'),
    staleTime: 60_000,
  });
}

export function useMarketBreadth(symbols: string) {
  return useQuery({
    queryKey: marketKeys.breadth(symbols),
    queryFn: () => apiGet<Record<string, { trend: string; ma_alignment: string }>>('/market/breadth', { symbols }),
    enabled: symbols.length > 0,
    staleTime: 60_000,
  });
}

export function useBatchMarketData() {
  return useQueries({
    queries: [
      { queryKey: marketKeys.overview(), queryFn: () => apiGet('/market/overview'), staleTime: 15_000 },
      { queryKey: marketKeys.stocks('A'), queryFn: () => apiGet('/market/stocks', { market: 'A' }), staleTime: 30_000 },
      { queryKey: marketKeys.sectors(), queryFn: () => apiGet('/market/heatmap'), staleTime: 60_000 },
    ],
  });
}
