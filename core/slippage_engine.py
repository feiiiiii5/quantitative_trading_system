"""
滑点引擎 - 真实交易成本建模
解决回测与实盘差距的核心问题之一

滑点来源:
1. 市场冲击 - 大额订单推动价格变动
2. 流动性不足 - 盘口深度不够
3. 执行延迟 - 下单到成交的价格变动
4. 买卖价差 - bid-ask spread
"""
import logging
from dataclasses import dataclass
from enum import Enum
from typing import Literal

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class SlippageModel(Enum):
    FIXED = "fixed"
    VOLUME_BASED = "volume_based"
    VOLATILITY_ADJUSTED = "volatility_adjusted"
    KRAUS = "kraus"


@dataclass
class SlippageConfig:
    model: SlippageModel = SlippageModel.VOLUME_BASED
    fixed_bps: float = 5.0
    volume_participation_rate: float = 0.02
    volatility_multiplier: float = 1.5
    min_slippage_bps: float = 1.0
    max_slippage_bps: float = 50.0
    market_impact_coeff: float = 0.1
    spread_bps: float = 2.0


@dataclass
class SlippageResult:
    slippage_bps: float
    market_impact_bps: float
    spread_cost_bps: float
    delay_cost_bps: float
    total_cost_bps: float
    effective_price: float
    model: SlippageModel
    message: str = ""


class SlippageEngine:
    def __init__(self, config: SlippageConfig | None = None):
        self._config = config or SlippageConfig()
        self._rng = np.random.default_rng()

    def estimate(
        self,
        direction: Literal["buy", "sell"],
        price: float,
        volume: float,
        avg_volume: float,
        volatility: float = 0.02,
        spread: float = 0.0,
        delay_ms: float = 0.0,
    ) -> SlippageResult:
        model = self._config.model
        if model == SlippageModel.FIXED:
            return self._fixed_model(direction, price)
        elif model == SlippageModel.VOLUME_BASED:
            return self._volume_based_model(
                direction, price, volume, avg_volume, volatility, spread, delay_ms
            )
        elif model == SlippageModel.VOLATILITY_ADJUSTED:
            return self._volatility_model(
                direction, price, volume, avg_volume, volatility, delay_ms
            )
        elif model == SlippageModel.KRAUS:
            return self._kraus_model(
                direction, price, volume, avg_volume, volatility
            )
        return self._volume_based_model(
            direction, price, volume, avg_volume, volatility, spread, delay_ms
        )

    def _fixed_model(
        self, direction: Literal["buy", "sell"], price: float
    ) -> SlippageResult:
        slippage_bps = self._config.fixed_bps
        effective_price = (
            price * (1 + slippage_bps / 10000)
            if direction == "buy"
            else price * (1 - slippage_bps / 10000)
        )
        return SlippageResult(
            slippage_bps=slippage_bps,
            market_impact_bps=slippage_bps * 0.7,
            spread_cost_bps=slippage_bps * 0.1,
            delay_cost_bps=slippage_bps * 0.2,
            total_cost_bps=slippage_bps,
            effective_price=effective_price,
            model=SlippageModel.FIXED,
            message=f"Fixed slippage: {slippage_bps}bps",
        )

    def _volume_based_model(
        self,
        direction: Literal["buy", "sell"],
        price: float,
        volume: float,
        avg_volume: float,
        volatility: float,
        spread: float,
        delay_ms: float,
    ) -> SlippageResult:
        if avg_volume <= 0:
            avg_volume = volume * 10

        participation = min(volume / avg_volume, 1.0) if avg_volume > 0 else 0.5
        volatility_component = volatility * self._config.volatility_multiplier
        participation_component = (
            participation * self._config.volume_participation_rate * 10000
        )
        market_impact = volatility_component * participation_component

        spread_cost = max(spread, self._config.spread_bps)
        delay_cost = self._delay_cost(delay_ms, volatility)
        delay_cost = min(delay_cost, 10.0)

        total_slippage = (
            market_impact + spread_cost + delay_cost + self._config.min_slippage_bps
        )
        total_slippage = np.clip(
            total_slippage,
            self._config.min_slippage_bps,
            self._config.max_slippage_bps,
        )

        effective_price = (
            price * (1 + total_slippage / 10000)
            if direction == "buy"
            else price * (1 - total_slippage / 10000)
        )

        return SlippageResult(
            slippage_bps=round(total_slippage, 2),
            market_impact_bps=round(market_impact, 2),
            spread_cost_bps=round(spread_cost, 2),
            delay_cost_bps=round(delay_cost, 2),
            total_cost_bps=round(total_slippage, 2),
            effective_price=round(effective_price, 4),
            model=SlippageModel.VOLUME_BASED,
            message=(
                f"participation={participation:.1%}, "
                f"vol={volatility:.2%}, "
                f"impact={market_impact:.1f}bps, "
                f"spread={spread_cost:.1f}bps, "
                f"delay={delay_cost:.1f}bps"
            ),
        )

    def _volatility_model(
        self,
        direction: Literal["buy", "sell"],
        price: float,
        volume: float,
        avg_volume: float,
        volatility: float,
        delay_ms: float,
    ) -> SlippageResult:
        if avg_volume <= 0:
            avg_volume = volume * 10
        participation = min(volume / avg_volume, 1.0) if avg_volume > 0 else 0.5
        vol_adjusted_impact = (
            volatility
            * self._config.volatility_multiplier
            * participation
            * 10000
        )
        delay_cost = self._delay_cost(delay_ms, volatility)
        total = vol_adjusted_impact + delay_cost + self._config.min_slippage_bps
        total = np.clip(
            total,
            self._config.min_slippage_bps,
            self._config.max_slippage_bps,
        )
        effective_price = (
            price * (1 + total / 10000)
            if direction == "buy"
            else price * (1 - total / 10000)
        )
        return SlippageResult(
            slippage_bps=round(total, 2),
            market_impact_bps=round(vol_adjusted_impact, 2),
            spread_cost_bps=round(self._config.spread_bps, 2),
            delay_cost_bps=round(delay_cost, 2),
            total_cost_bps=round(total, 2),
            effective_price=round(effective_price, 4),
            model=SlippageModel.VOLATILITY_ADJUSTED,
            message=f"vol={volatility:.2%}, participation={participation:.1%}",
        )

    def _kraus_model(
        self,
        direction: Literal["buy", "sell"],
        price: float,
        volume: float,
        avg_volume: float,
        volatility: float,
    ) -> SlippageResult:
        if avg_volume <= 0:
            avg_volume = volume * 10
        participation = min(volume / avg_volume, 1.0) if avg_volume > 0 else 0.5
        participation_factor = np.sqrt(participation + 1e-10)
        market_impact = (
            self._config.market_impact_coeff
            * volatility
            * participation_factor
            * 10000
        )
        total = market_impact + self._config.spread_bps
        total = np.clip(
            total,
            self._config.min_slippage_bps,
            self._config.max_slippage_bps,
        )
        effective_price = (
            price * (1 + total / 10000)
            if direction == "buy"
            else price * (1 - total / 10000)
        )
        return SlippageResult(
            slippage_bps=round(total, 2),
            market_impact_bps=round(market_impact, 2),
            spread_cost_bps=round(self._config.spread_bps, 2),
            delay_cost_bps=0.0,
            total_cost_bps=round(total, 2),
            effective_price=round(effective_price, 4),
            model=SlippageModel.KRAUS,
            message=f"Kraus: sqrt(participation)={participation_factor:.2f}, impact={market_impact:.1f}bps",
        )

    def _delay_cost(self, delay_ms: float, volatility: float) -> float:
        if delay_ms <= 0:
            return 0.0
        price_move_per_ms = volatility / (4 * 60 * 60 * 1000)
        expected_move = abs(price_move_per_ms * delay_ms)
        return expected_move * 10000

    def estimate_trade_series(
        self,
        trades: list[dict],
        daily_volumes: pd.Series | None = None,
        daily_volatility: pd.Series | None = None,
    ) -> list[SlippageResult]:
        results = []
        for trade in trades:
            vol = trade.get("volume", 0)
            price = trade.get("price", 100)
            direction = trade.get("direction", "buy")
            day = trade.get("date", "")

            avg_vol = 1000000
            vol_input = daily_volumes
            if vol_input is not None and day in vol_input.index:
                avg_vol = float(vol_input.loc[day])

            vol_val = daily_volatility
            vol_rate = 0.015
            if vol_val is not None and day in vol_val.index:
                vol_rate = float(vol_val.loc[day])

            result = self.estimate(
                direction=direction,
                price=price,
                volume=vol,
                avg_volume=avg_vol,
                volatility=vol_rate,
            )
            results.append(result)
        return results

    def apply_to_backtest(
        self,
        df: pd.DataFrame,
        orders: list[dict],
        daily_volumes: pd.Series | None = None,
    ) -> pd.DataFrame:
        results = self.estimate_trade_series(
            orders,
            daily_volumes=daily_volumes,
            daily_volatility=None,
        )
        adjusted_returns = df["returns"].copy() if "returns" in df.columns else pd.Series(0, index=df.index)
        order_idx_map = {str(o.get("date", "")): i for i, o in enumerate(orders)}

        for idx in df.index:
            date_key = str(df.loc[idx, "date"])[:10] if "date" in df.columns else str(idx)
            if date_key in order_idx_map:
                i = order_idx_map[date_key]
                slippage = results[i].slippage_bps / 10000
                direction = orders[i].get("direction", "buy")
                cost = slippage if direction == "buy" else -slippage
                adjusted_returns.loc[idx] = adjusted_returns.loc[idx] - cost

        df_out = df.copy()
        df_out["returns_adjusted"] = adjusted_returns
        df_out["slippage_cost_bps"] = 0.0
        for i, order in enumerate(orders):
            date_key = str(order.get("date", ""))[:10]
            for idx in df_out.index:
                if str(df_out.loc[idx, "date"])[:10] == date_key:
                    df_out.loc[idx, "slippage_cost_bps"] = results[i].slippage_bps
                    break

        return df_out

    def get_cost_summary(
        self,
        results: list[SlippageResult],
        initial_capital: float = 1000000,
    ) -> dict:
        if not results:
            return {
                "total_slippage_bps": 0.0,
                "avg_slippage_bps": 0.0,
                "max_slippage_bps": 0.0,
                "total_cost_pct": 0.0,
                "estimated_total_cost": 0.0,
                "model_used": self._config.model.value,
            }
        total_bps = sum(r.total_cost_bps for r in results)
        avg_bps = total_bps / len(results)
        max_bps = max(r.total_cost_bps for r in results)
        total_cost_pct = total_bps / 10000
        estimated_cost = initial_capital * total_cost_pct
        return {
            "total_slippage_bps": round(total_bps, 2),
            "avg_slippage_bps": round(avg_bps, 2),
            "max_slippage_bps": round(max_bps, 2),
            "total_cost_pct": round(total_cost_pct * 100, 4),
            "estimated_total_cost": round(estimated_cost, 2),
            "model_used": self._config.model.value,
            "n_trades": len(results),
        }


_slippage_engine: SlippageEngine | None = None


def get_slippage_engine(config: SlippageConfig | None = None) -> SlippageEngine:
    global _slippage_engine
    if _slippage_engine is None or config is not None:
        _slippage_engine = SlippageEngine(config)
    return _slippage_engine
