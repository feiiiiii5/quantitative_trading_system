import { useState, useCallback, memo } from 'react';
import { useNavigate } from 'react-router-dom';
import { useWatchlistStore } from '@/stores/watchlist';
import { useMarketStore } from '@/stores/market';
import { formatPrice, formatPercent, priceColor } from '@/utils/format';
import { Sparkline } from '@/components/charts/Sparkline';

export const DraggableWatchlist = memo(function DraggableWatchlist() {
  const symbols = useWatchlistStore(s => s.symbols);
  const reorder = useWatchlistStore(s => s.reorder);
  const stocks = useMarketStore(s => s.stocks);
  const navigate = useNavigate();
  const [dragIdx, setDragIdx] = useState<number | null>(null);
  const [overIdx, setOverIdx] = useState<number | null>(null);

  const handleDrop = useCallback((targetIdx: number) => {
    if (dragIdx === null || dragIdx === targetIdx) return;
    const next = [...symbols];
    const [moved] = next.splice(dragIdx, 1);
    next.splice(targetIdx, 0, moved!);
    reorder(next);
    setDragIdx(null);
    setOverIdx(null);
  }, [dragIdx, symbols, reorder]);

  const stockMap = new Map(stocks.map(s => [s.symbol, s]));

  return (
    <div style={{ display: 'flex', flexDirection: 'column' }}>
      {symbols.map((symbol, i) => {
        const stock = stockMap.get(symbol);
        const pct = stock?.change_pct ?? 0;
        return (
          <div
            key={symbol}
            draggable
            onDragStart={() => setDragIdx(i)}
            onDragOver={(e) => { e.preventDefault(); setOverIdx(i); }}
            onDrop={() => handleDrop(i)}
            onDragEnd={() => { setDragIdx(null); setOverIdx(null); }}
            onClick={() => navigate(`/stock/${symbol}`)}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 8,
              padding: '6px 12px',
              cursor: 'grab',
              opacity: dragIdx === i ? 0.4 : 1,
              borderTop: overIdx === i && dragIdx !== i
                ? '2px solid var(--accent)' : '2px solid transparent',
              transition: 'opacity 150ms, border-color 100ms',
              fontFamily: 'var(--font-mono)',
              fontSize: 12,
            }}
          >
            <span style={{ color: 'var(--accent)', width: 64, flexShrink: 0 }}>{symbol}</span>
            <span style={{ flex: 1, color: 'var(--label-secondary)', fontFamily: 'var(--font-sans)', fontSize: 11, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {stock?.name ?? '—'}
            </span>
            {stock && (
              <Sparkline
                data={[]}
                width={40}
                height={14}
                color={priceColor(pct)}
              />
            )}
            <span style={{ color: priceColor(pct), fontVariantNumeric: 'tabular-nums', width: 64, textAlign: 'right' }}>
              {stock ? formatPrice(stock.price) : '—'}
            </span>
            <span style={{ color: priceColor(pct), fontVariantNumeric: 'tabular-nums', width: 60, textAlign: 'right' }}>
              {stock ? formatPercent(pct) : ''}
            </span>
          </div>
        );
      })}
      {symbols.length === 0 && (
        <div style={{ padding: '24px 0', textAlign: 'center', color: 'var(--label-quaternary)', fontFamily: 'var(--font-mono)', fontSize: 11 }}>
          NO WATCHLIST
        </div>
      )}
    </div>
  );
});
