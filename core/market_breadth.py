import logging

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class MarketBreadthAnalyzer:
    """市场宽度分析器，衡量市场参与度和健康度"""

    def __init__(self):
        pass

    def compute_advance_decline(
        self,
        price_changes: dict[str, float],
    ) -> dict:
        """计算涨跌家数和涨跌比率

        Args:
            price_changes: {symbol: daily_change_pct} 字典

        Returns:
            涨跌统计和市场宽度指标
        """
        if not price_changes:
            return {"error": "无数据"}

        changes = np.array(list(price_changes.values()))
        n = len(changes)

        advancing = int(np.sum(changes > 0))
        declining = int(np.sum(changes < 0))
        unchanged = int(np.sum(changes == 0))

        # 涨跌比率
        ad_ratio = advancing / declining if declining > 0 else (999.0 if advancing > 0 else 0.0)

        # 涨跌差异
        ad_spread = advancing - declining
        ad_spread / n * 100 if n > 0 else 0

        # 市场宽度评分（0-100）
        breadth_score = (advancing / n) * 100 if n > 0 else 50

        # 宽度状态
        if breadth_score > 70:
            regime = "broad_advance"
        elif breadth_score > 55:
            regime = "moderate_advance"
        elif breadth_score > 45:
            regime = "neutral"
        elif breadth_score > 30:
            regime = "moderate_decline"
        else:
            regime = "broad_decline"

        # 涨幅分布统计
        positive_changes = changes[changes > 0]
        negative_changes = changes[changes < 0]

        avg_advance = float(np.mean(positive_changes)) if len(positive_changes) > 0 else 0
        avg_decline = float(np.mean(negative_changes)) if len(negative_changes) > 0 else 0

        # 涨跌力度比（上涨平均涨幅/下跌平均跌幅）
        thrust_ratio = abs(avg_advance / avg_decline) if abs(avg_decline) > 1e-8 else (999.0 if avg_advance > 0 else 0.0)

        # 涨停/跌停统计（假设±10%为涨跌停）
        limit_up = int(np.sum(changes >= 9.5))
        limit_down = int(np.sum(changes <= -9.5))

        return {
            "total_stocks": n,
            "advancing": advancing,
            "declining": declining,
            "unchanged": unchanged,
            "advance_decline_ratio": round(ad_ratio, 2),
            "advance_decline_spread": ad_spread,
            "breadth_score": round(breadth_score, 2),
            "regime": regime,
            "avg_advance_pct": round(avg_advance, 4),
            "avg_decline_pct": round(avg_decline, 4),
            "thrust_ratio": round(thrust_ratio, 2),
            "limit_up": limit_up,
            "limit_down": limit_down,
        }

    def compute_mcclellan_oscillator(
        self,
        advance_decline_history: list[dict],
    ) -> dict:
        """计算麦克莱伦振荡器

        Args:
            advance_decline_history: 历史涨跌差值列表 [{"date": "...", "spread": N}, ...]

        Returns:
            McClellan振荡器值和信号
        """
        if len(advance_decline_history) < 20:
            return {"error": f"数据不足: 需要20+，实际{len(advance_decline_history)}"}

        spreads = np.array([h["spread"] for h in advance_decline_history])
        dates = [h.get("date", "") for h in advance_decline_history]

        # 19日和39日指数移动平均
        ema_19 = self._ema(spreads, 19)
        ema_39 = self._ema(spreads, 39)

        # 振荡器 = 短期EMA - 长期EMA
        oscillator = ema_19[-1] - ema_39[-1]

        # 信号判断
        if len(ema_19) > 2 and len(ema_39) > 2:
            prev_osc = ema_19[-2] - ema_39[-2]
            if oscillator > 0 and prev_osc <= 0:
                signal = "bullish_crossover"
            elif oscillator < 0 and prev_osc >= 0:
                signal = "bearish_crossover"
            elif oscillator > 50:
                signal = "overbought"
            elif oscillator < -50:
                signal = "oversold"
            else:
                signal = "neutral"
        else:
            signal = "neutral"

        # 降采样历史
        max_points = 200
        osc_history = (ema_19 - ema_39).tolist()
        if len(osc_history) > max_points:
            step = len(osc_history) / max_points
            indices = [int(i * step) for i in range(max_points)]
            if indices[-1] != len(osc_history) - 1:
                indices.append(len(osc_history) - 1)
            osc_history = [osc_history[i] for i in indices]
            out_dates = [dates[i] if i < len(dates) else "" for i in indices]
        else:
            out_dates = dates[-len(osc_history):]

        return {
            "current": round(float(oscillator), 2),
            "signal": signal,
            "ema_19": round(float(ema_19[-1]), 2),
            "ema_39": round(float(ema_39[-1]), 2),
            "history": [
                {"date": d, "value": round(v, 2)}
                for d, v in zip(out_dates, osc_history, strict=False)
            ],
        }

    def compute_percent_above_ma(
        self,
        price_data: dict[str, pd.Series],
        ma_period: int = 50,
    ) -> dict:
        """计算站上均线的股票占比

        Args:
            price_data: {symbol: price_series} 字典
            ma_period: 均线周期

        Returns:
            站上均线占比和市场宽度信号
        """
        if not price_data:
            return {"error": "无数据"}

        above_count = 0
        total = 0
        details = []

        for symbol, prices in price_data.items():
            if len(prices) < ma_period:
                continue
            total += 1
            current = float(prices.iloc[-1])
            ma = float(prices.iloc[-ma_period:].mean())
            is_above = current > ma
            if is_above:
                above_count += 1
            details.append({
                "symbol": symbol,
                "price": round(current, 2),
                "ma": round(ma, 2),
                "above_ma": is_above,
                "pct_from_ma": round((current / ma - 1) * 100, 2) if ma > 0 else 0,
            })

        if total == 0:
            return {"error": "有效数据不足"}

        pct_above = above_count / total * 100

        # 宽度信号
        if pct_above > 80:
            signal = "overbought"
        elif pct_above > 60:
            signal = "bullish"
        elif pct_above > 40:
            signal = "neutral"
        elif pct_above > 20:
            signal = "bearish"
        else:
            signal = "oversold"

        return {
            "total_stocks": total,
            "above_ma": above_count,
            "below_ma": total - above_count,
            "pct_above_ma": round(pct_above, 2),
            "ma_period": ma_period,
            "signal": signal,
            "details": details[:50],  # 限制返回数量
        }

    @staticmethod
    def _ema(data: np.ndarray, period: int) -> np.ndarray:
        """计算指数移动平均"""
        multiplier = 2.0 / (period + 1)
        result = np.zeros_like(data, dtype=float)
        result[0] = data[0]
        for i in range(1, len(data)):
            result[i] = data[i] * multiplier + result[i - 1] * (1 - multiplier)
        return result


_analyzer: MarketBreadthAnalyzer | None = None


def get_market_breadth_analyzer() -> MarketBreadthAnalyzer:
    global _analyzer
    if _analyzer is None:
        _analyzer = MarketBreadthAnalyzer()
    return _analyzer
