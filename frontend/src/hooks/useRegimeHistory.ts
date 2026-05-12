import { useState, useEffect } from 'react';
import { apiGet } from '@/api/client';

export interface RegimePeriod {
  start: string;
  end: string;
  regime: 'BULL' | 'BEAR' | 'CHOP' | 'VOLATILE';
}

export function useRegimeHistory(symbol: string, start: string, end: string) {
  const [regimeHistory, setRegimeHistory] = useState<RegimePeriod[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    apiGet<{
      current_regime?: string;
      regime_probabilities?: Record<string, number>;
      duration?: { current_state_days?: number; avg_duration?: number };
      timestamp?: string;
    }>('/market/regime', { symbol })
      .then(data => {
        if (cancelled) return;
        if (data?.current_regime) {
          const regime = data.current_regime as RegimePeriod['regime'];
          const durationDays = data.duration?.current_state_days ?? 0;
          const endDate = data.timestamp ?? end;
          const startDate = durationDays > 0
            ? new Date(new Date(endDate).getTime() - durationDays * 86400000).toISOString().slice(0, 10)
            : start;
          setRegimeHistory([{ start: startDate, end: endDate.slice(0, 10), regime }]);
        } else {
          setRegimeHistory([]);
        }
      })
      .catch(() => { if (!cancelled) setRegimeHistory([]); })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => { cancelled = true; };
  }, [symbol, start, end]);

  return { regimeHistory, loading };
}
