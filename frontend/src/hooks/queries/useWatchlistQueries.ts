import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiGet, apiPost } from '@/api/client';

export const watchlistKeys = {
  all: ['watchlist'] as const,
  list: () => [...watchlistKeys.all, 'list'] as const,
  screener: () => [...watchlistKeys.all, 'screener'] as const,
};

interface WatchlistData {
  symbols: string[];
  quotes: Record<string, unknown>;
}

export function useWatchlist() {
  return useQuery({
    queryKey: watchlistKeys.list(),
    queryFn: () => apiGet<WatchlistData>('/watchlist'),
    staleTime: 30_000,
  });
}

export function useWatchlistScreener() {
  return useQuery({
    queryKey: watchlistKeys.screener(),
    queryFn: () => apiGet<Record<string, unknown>>('/screener/presets'),
    staleTime: 60_000,
  });
}

export function useAddToWatchlist() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (symbol: string) => apiPost('/watchlist/add', { symbol }),
    onMutate: async (symbol) => {
      await qc.cancelQueries({ queryKey: watchlistKeys.list() });
      const prev = qc.getQueryData<WatchlistData>(watchlistKeys.list());
      if (prev) {
        qc.setQueryData<WatchlistData>(watchlistKeys.list(), {
          symbols: [...prev.symbols, symbol],
          quotes: prev.quotes,
        });
      }
      return { prev };
    },
    onError: (_err, _symbol, context) => {
      if (context?.prev) {
        qc.setQueryData(watchlistKeys.list(), context.prev);
      }
    },
    onSettled: () => {
      qc.invalidateQueries({ queryKey: watchlistKeys.all });
    },
  });
}

export function useRemoveFromWatchlist() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (symbol: string) => apiPost('/watchlist/remove', { symbol }),
    onMutate: async (symbol) => {
      await qc.cancelQueries({ queryKey: watchlistKeys.list() });
      const prev = qc.getQueryData<WatchlistData>(watchlistKeys.list());
      if (prev) {
        qc.setQueryData<WatchlistData>(watchlistKeys.list(), {
          symbols: prev.symbols.filter(s => s !== symbol),
          quotes: prev.quotes,
        });
      }
      return { prev };
    },
    onError: (_err, _symbol, context) => {
      if (context?.prev) {
        qc.setQueryData(watchlistKeys.list(), context.prev);
      }
    },
    onSettled: () => {
      qc.invalidateQueries({ queryKey: watchlistKeys.all });
    },
  });
}
