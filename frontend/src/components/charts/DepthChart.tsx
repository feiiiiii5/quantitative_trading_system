import { memo, useCallback } from 'react';
import { useCanvas } from '@/hooks/useCanvas';
import { colors } from '@/design/tokens/colors';
import type { OrderBookEntry } from '@/types';

interface DepthChartProps {
  bids: OrderBookEntry[];
  asks: OrderBookEntry[];
  height?: number;
}

export const DepthChart = memo(function DepthChart({ bids, asks, height = 120 }: DepthChartProps) {
  const draw = useCallback((ctx: CanvasRenderingContext2D, w: number, h: number) => {
    ctx.clearRect(0, 0, w, h);
    if (bids.length === 0 && asks.length === 0) return;

    const cumBids: Array<{ price: number; cum: number }> = [];
    let bidCum = 0;
    for (const b of bids) {
      bidCum += b.quantity;
      cumBids.push({ price: b.price, cum: bidCum });
    }

    const cumAsks: Array<{ price: number; cum: number }> = [];
    let askCum = 0;
    for (const a of asks) {
      askCum += a.quantity;
      cumAsks.push({ price: a.price, cum: askCum });
    }

    const minPrice = bids.length > 0 ? bids[bids.length - 1]!.price : (asks.length > 0 ? asks[0]!.price : 0);
    const maxPrice = asks.length > 0 ? asks[asks.length - 1]!.price : (bids.length > 0 ? bids[0]!.price : 0);
    const priceRange = maxPrice - minPrice || 1;
    const maxCum = Math.max(
      cumBids.length > 0 ? cumBids[cumBids.length - 1]!.cum : 0,
      cumAsks.length > 0 ? cumAsks[cumAsks.length - 1]!.cum : 0,
      1,
    );

    const toX = (price: number) => ((price - minPrice) / priceRange) * w;
    const toY = (cum: number) => h - (cum / maxCum) * h * 0.9;

    if (cumBids.length > 0) {
      ctx.beginPath();
      ctx.moveTo(toX(cumBids[0]!.price), h);
      for (const { price, cum } of cumBids) {
        ctx.lineTo(toX(price), toY(cum));
      }
      ctx.lineTo(toX(cumBids[0]!.price), h);
      ctx.closePath();
      const bidGrad = ctx.createLinearGradient(0, 0, w / 2, 0);
      bidGrad.addColorStop(0, 'rgba(0,217,160,0.30)');
      bidGrad.addColorStop(1, 'rgba(0,217,160,0.05)');
      ctx.fillStyle = bidGrad;
      ctx.fill();

      ctx.beginPath();
      for (let i = 0; i < cumBids.length; i++) {
        const x = toX(cumBids[i]!.price);
        const y = toY(cumBids[i]!.cum);
        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      }
      ctx.strokeStyle = colors.market.fall;
      ctx.lineWidth = 1.5;
      ctx.stroke();
    }

    if (cumAsks.length > 0) {
      ctx.beginPath();
      ctx.moveTo(toX(cumAsks[cumAsks.length - 1]!.price), h);
      for (const { price, cum } of cumAsks) {
        ctx.lineTo(toX(price), toY(cum));
      }
      ctx.lineTo(toX(cumAsks[cumAsks.length - 1]!.price), h);
      ctx.closePath();
      const askGrad = ctx.createLinearGradient(w / 2, 0, w, 0);
      askGrad.addColorStop(0, 'rgba(255,59,92,0.05)');
      askGrad.addColorStop(1, 'rgba(255,59,92,0.30)');
      ctx.fillStyle = askGrad;
      ctx.fill();

      ctx.beginPath();
      for (let i = 0; i < cumAsks.length; i++) {
        const x = toX(cumAsks[i]!.price);
        const y = toY(cumAsks[i]!.cum);
        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      }
      ctx.strokeStyle = colors.market.rise;
      ctx.lineWidth = 1.5;
      ctx.stroke();
    }

    if (bids.length > 0 && asks.length > 0) {
      const midPrice = (bids[0]!.price + asks[0]!.price) / 2;
      const midX = toX(midPrice);
      ctx.strokeStyle = 'rgba(10,132,255,0.6)';
      ctx.lineWidth = 1;
      ctx.setLineDash([4, 4]);
      ctx.beginPath();
      ctx.moveTo(midX, 0);
      ctx.lineTo(midX, h);
      ctx.stroke();
      ctx.setLineDash([]);

      ctx.fillStyle = 'rgba(10,132,255,0.8)';
      ctx.font = '9px monospace';
      ctx.textAlign = 'center';
      ctx.fillText(midPrice.toFixed(2), midX, 12);
    }
  }, [bids, asks]);

  const { ref } = useCanvas(draw, [bids, asks]);
  return <canvas ref={ref} style={{ width: '100%', height }} />;
});
