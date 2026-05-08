"""
Strategy Pipeline - Shared indicator computation and auto-registration.

Paradigm shift from per-strategy indicator recomputation to a shared,
cached pipeline architecture. Strategies declare their indicator
dependencies and receive pre-computed values, eliminating redundant
computation across 35+ strategies.
"""
import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd

from core.strategies import (
    BaseStrategy,
    SignalType,
    TradeSignal,
    _rsi_series,
    _safe_divide,
)

logger = logging.getLogger(__name__)

_REGISTRY: dict[str, type[BaseStrategy]] = {}
_REGISTRY_ALIASES: dict[str, str] = {}


def strategy(*names: str):
    """Decorator that auto-registers a strategy class.

    Usage:
        @strategy("my_strategy", "my_strat")
        class MyStrategy(BaseStrategy):
            ...

    The first name becomes the canonical key; all others are aliases.
    """
    def decorator(cls):
        canonical = cls.__name__ if not names else names[0]
        _REGISTRY[canonical] = cls
        for alias in names[1:]:
            _REGISTRY_ALIASES[alias] = canonical
        cls._strategy_names = names if names else (cls.__name__,)
        return cls
    return decorator


def get_strategy_class(name: str) -> type[BaseStrategy] | None:
    """Look up a strategy class by name or alias."""
    cls = _REGISTRY.get(name)
    if cls is not None:
        return cls
    canonical = _REGISTRY_ALIASES.get(name)
    if canonical is not None:
        return _REGISTRY.get(canonical)
    return None


def list_registered_strategies() -> dict[str, list[str]]:
    """Return {canonical_name: [alias1, alias2, ...]} for all registered strategies."""
    result = {}
    for canonical, _cls in _REGISTRY.items():
        aliases = [a for a, c in _REGISTRY_ALIASES.items() if c == canonical]
        result[canonical] = aliases
    return result


@dataclass
class IndicatorRequest:
    """Declares which indicators a strategy needs."""
    rsi: bool = False
    rsi_period: int = 14
    macd: bool = False
    boll: bool = False
    boll_period: int = 20
    atr: bool = False
    atr_period: int = 14
    ma: bool = False
    ma_periods: tuple = (5, 10, 20, 60)
    ema: bool = False
    ema_periods: tuple = (12, 26)
    kdj: bool = False
    supertrend: bool = False
    supertrend_period: int = 10
    supertrend_mult: float = 3.0
    vwap: bool = False
    vwap_period: int = 20
    adx: bool = False
    adx_period: int = 14
    cmf: bool = False
    cmf_period: int = 20
    obv: bool = False
    volume_ratio: bool = False
    volume_ratio_period: int = 5


class SharedIndicators:
    """Computes and caches indicators once per DataFrame.

    Instead of each strategy independently computing RSI, MA, ATR etc.,
    strategies declare their needs via IndicatorRequest and receive
    pre-computed arrays. This eliminates redundant computation when
    CompositeStrategy runs 35+ strategies on the same data.
    """

    def __init__(self):
        self._cache: dict[int, dict[str, Any]] = {}
        self._cache_max = 10

    def compute(self, df: pd.DataFrame, request: IndicatorRequest) -> dict[str, Any]:
        """Compute requested indicators for the given DataFrame.

        Returns a dict of indicator name -> computed value/array.
        Results are cached by DataFrame id to avoid recomputation.
        """
        df_id = id(df)
        if df_id in self._cache:
            return self._cache[df_id]

        if len(df) < 2:
            return {}

        c = df["close"].astype(float)
        h = df["high"].astype(float) if "high" in df.columns else c
        low = df["low"].astype(float) if "low" in df.columns else c
        v = df["volume"].astype(float) if "volume" in df.columns else pd.Series(1, index=df.index)

        result: dict[str, Any] = {}

        if request.rsi:
            result["rsi"] = _rsi_series(c, request.rsi_period)

        if request.macd:
            ema12 = c.ewm(span=12, adjust=False).mean()
            ema26 = c.ewm(span=26, adjust=False).mean()
            dif = ema12 - ema26
            dea = dif.ewm(span=9, adjust=False).mean()
            hist = (dif - dea) * 2
            result["macd_dif"] = dif
            result["macd_dea"] = dea
            result["macd_hist"] = hist

        if request.boll:
            mid = c.rolling(request.boll_period).mean()
            std = c.rolling(request.boll_period).std()
            result["boll_upper"] = mid + 2 * std
            result["boll_mid"] = mid
            result["boll_lower"] = mid - 2 * std
            result["boll_std"] = std

        if request.atr:
            tr = pd.concat(
                [h - low, (h - c.shift(1)).abs(), (low - c.shift(1)).abs()],
                axis=1,
            ).max(axis=1)
            result["atr"] = tr.rolling(request.atr_period).mean()

        if request.ma:
            for p in request.ma_periods:
                result[f"ma_{p}"] = c.rolling(p).mean()

        if request.ema:
            for p in request.ema_periods:
                result[f"ema_{p}"] = c.ewm(span=p, adjust=False).mean()

        if request.kdj:
            n = 9
            hh = h.rolling(n).max()
            ll = low.rolling(n).min()
            denom = hh - ll
            rsv = np.where(denom != 0, (c - ll) / denom * 100, 50.0)
            rsv = pd.Series(rsv, index=df.index).fillna(50)
            k = rsv.ewm(alpha=1 / 3, adjust=False).mean()
            d = k.ewm(alpha=1 / 3, adjust=False).mean()
            j = 3 * k - 2 * d
            result["kdj_k"] = k
            result["kdj_d"] = d
            result["kdj_j"] = j

        if request.supertrend:
            tr = pd.concat(
                [h - low, (h - c.shift(1)).abs(), (low - c.shift(1)).abs()],
                axis=1,
            ).max(axis=1)
            atr = tr.rolling(request.supertrend_period).mean()
            hl2 = (h + low) / 2
            upper_band = (hl2 + request.supertrend_mult * atr).values.copy()
            lower_band = (hl2 - request.supertrend_mult * atr).values.copy()
            n_bars = len(df)
            direction = np.ones(n_bars, dtype=int)
            for i in range(1, n_bars):
                if not (lower_band[i] > lower_band[i - 1] or c.iloc[i - 1] < lower_band[i - 1]):
                    lower_band[i] = lower_band[i - 1]
                if not (upper_band[i] < upper_band[i - 1] or c.iloc[i - 1] > upper_band[i - 1]):
                    upper_band[i] = upper_band[i - 1]
                if direction[i - 1] == 1:
                    direction[i] = -1 if c.iloc[i] < lower_band[i] else 1
                else:
                    direction[i] = 1 if c.iloc[i] > upper_band[i] else -1
            result["supertrend_direction"] = direction

        if request.vwap:
            typical = (h + low + c) / 3
            vol_sum = v.rolling(request.vwap_period).sum().replace(0, np.nan)
            result["vwap"] = (typical * v).rolling(request.vwap_period).sum() / vol_sum

        if request.adx:
            from core.indicators import calc_adx
            from core.indicators import calc_atr as _calc_atr
            h_arr = h.values
            l_arr = low.values
            c_arr = c.values
            result["adx"] = _calc_atr(h_arr, l_arr, c_arr, request.adx_period)
            result["adx_val"] = calc_adx(h_arr, l_arr, c_arr, request.adx_period)

        if request.cmf:
            spread = h - low
            clv = np.where(spread > 0, ((c - low) - (h - c)) / spread, 0.0)
            mfv = clv * v
            result["cmf"] = _safe_divide(
                pd.Series(mfv).rolling(request.cmf_period).sum(),
                v.rolling(request.cmf_period).sum(),
                0.0,
            ).fillna(0)

        if request.obv:
            direction_arr = np.sign(np.diff(c.values, prepend=c.values[0]))
            result["obv"] = pd.Series(np.cumsum(direction_arr * v.values), index=df.index)

        if request.volume_ratio:
            avg = v.rolling(request.volume_ratio_period).mean()
            result["volume_ratio"] = v / avg.replace(0, np.nan)

        if len(self._cache) >= self._cache_max:
            oldest_key = next(iter(self._cache))
            del self._cache[oldest_key]
        self._cache[df_id] = result

        return result

    def invalidate(self, df: pd.DataFrame = None):
        """Clear cache for a specific DataFrame or all."""
        if df is not None:
            self._cache.pop(id(df), None)
        else:
            self._cache.clear()


@dataclass
class PipelineStage:
    """A single stage in the strategy pipeline."""
    name: str
    fn: Callable
    order: int = 0


@dataclass
class PipelineResult:
    """Output of a pipeline run."""
    final_signal: TradeSignal
    strategy_signals: dict[str, TradeSignal] = field(default_factory=dict)
    indicators_computed: int = 0
    strategies_run: int = 0
    stages_executed: list[str] = field(default_factory=list)


class StrategyPipeline:
    """Orchestrates strategy signal generation with shared indicators.

    Pipeline flow:
        1. Compute shared indicators once
        2. Run each strategy with pre-computed indicators
        3. Apply fusion stage (weighted voting)
        4. Apply risk filter stage
        5. Return final signal

    This replaces CompositeStrategy's simple vote counting with a
    configurable, extensible pipeline that eliminates redundant
    indicator computation.
    """

    def __init__(self, strategies: list[BaseStrategy] = None):
        self._strategies: list[BaseStrategy] = strategies or []
        self._shared = SharedIndicators()
        self._stages: list[PipelineStage] = []
        self._fusion_method: str = "weighted_vote"
        self._min_agreement: float = 0.15
        self._cache_key: tuple | None = None
        self._cache_result: PipelineResult | None = None
        self._add_default_stages()

    def _add_default_stages(self):
        self._stages = [
            PipelineStage(name="indicators", fn=self._stage_indicators, order=10),
            PipelineStage(name="signal_generation", fn=self._stage_signals, order=20),
            PipelineStage(name="fusion", fn=self._stage_fusion, order=30),
            PipelineStage(name="risk_filter", fn=self._stage_risk_filter, order=40),
        ]
        self._stages.sort(key=lambda s: s.order)

    def add_strategy(self, strategy: BaseStrategy):
        self._strategies.append(strategy)

    def remove_strategy(self, name: str):
        self._strategies = [s for s in self._strategies if s.name != name]

    def set_fusion_method(self, method: str):
        self._fusion_method = method

    def add_stage(self, name: str, fn: Callable, order: int):
        self._stages.append(PipelineStage(name=name, fn=fn, order=order))
        self._stages.sort(key=lambda s: s.order)

    def run(self, df: pd.DataFrame) -> PipelineResult:
        """Execute the full pipeline on the given DataFrame."""
        if df is None or len(df) < 2:
            return PipelineResult(
                final_signal=TradeSignal(SignalType.HOLD),
                strategy_signals={},
                indicators_computed=0,
                strategies_run=0,
            )

        if len(df) > 0:
            cache_key = (
                len(df),
                float(df["close"].iloc[-1]),
                str(df.index[-1]) if hasattr(df.index[-1], "__str__") else len(df),
                self._fusion_method,
            )
            if cache_key == self._cache_key and self._cache_result is not None:
                return self._cache_result
        else:
            cache_key = None

        context: dict[str, Any] = {
            "df": df,
            "indicators": {},
            "signals": {},
            "indicators_count": 0,
            "strategies_count": 0,
            "stages_executed": [],
        }

        for stage in self._stages:
            try:
                stage.fn(context)
                context["stages_executed"].append(stage.name)
            except Exception as e:
                logger.warning("Pipeline stage '%s' failed: %s", stage, e)

        final = context.get("final_signal", TradeSignal(SignalType.HOLD))
        result = PipelineResult(
            final_signal=final,
            strategy_signals=context.get("signals", {}),
            indicators_computed=context.get("indicators_count", 0),
            strategies_run=context.get("strategies_count", 0),
            stages_executed=context["stages_executed"],
        )

        if cache_key is not None:
            self._cache_key = cache_key
            self._cache_result = result

        return result

    def _stage_indicators(self, ctx: dict):
        """Stage 1: Compute shared indicators needed by all strategies."""
        df = ctx["df"]
        request = self._build_indicator_request()
        indicators = self._shared.compute(df, request)
        ctx["indicators"] = indicators
        ctx["indicators_count"] = len(indicators)

    def _stage_signals(self, ctx: dict):
        """Stage 2: Generate signals from each strategy."""
        df = ctx["df"]
        signals: dict[str, TradeSignal] = {}

        for s in self._strategies:
            try:
                sig = s.generate_signal(df)
                if sig and sig.signal_type != SignalType.HOLD:
                    signals[s.name] = sig
            except Exception as e:
                logger.debug("Pipeline strategy %s error: %s", s, e)

        ctx["signals"] = signals
        ctx["strategies_count"] = len(self._strategies)

    def _stage_fusion(self, ctx: dict):
        """Stage 3: Fuse strategy signals into a single signal."""
        signals = ctx.get("signals", {})
        if not signals:
            ctx["final_signal"] = TradeSignal(SignalType.HOLD)
            return

        if self._fusion_method == "weighted_vote":
            ctx["final_signal"] = self._weighted_vote(signals)
        elif self._fusion_method == "strength_weighted":
            ctx["final_signal"] = self._strength_weighted(signals)
        elif self._fusion_method == "unanimous":
            ctx["final_signal"] = self._unanimous(signals)
        else:
            ctx["final_signal"] = self._weighted_vote(signals)

    def _stage_risk_filter(self, ctx: dict):
        """Stage 4: Apply basic risk filters to the fused signal."""
        signal = ctx.get("final_signal", TradeSignal(SignalType.HOLD))
        if signal.signal_type == SignalType.HOLD:
            return

        df = ctx["df"]
        if len(df) < 20:
            return

        c = df["close"].astype(float)
        returns = c.pct_change().dropna()
        if len(returns) < 5:
            return

        recent_vol = float(returns.tail(10).std())
        if recent_vol > 0.05:
            signal.strength = round(min(signal.strength, 0.5), 2)
            signal.reason = f"{signal.reason} [高波动抑制]"

        ctx["final_signal"] = signal

    def _weighted_vote(self, signals: dict[str, TradeSignal]) -> TradeSignal:
        """Weighted voting: each strategy's strength is its vote weight."""
        buy_weight = 0.0
        sell_weight = 0.0
        buy_count = 0
        sell_count = 0

        for _name, sig in signals.items():
            if sig.signal_type == SignalType.BUY:
                buy_weight += sig.strength
                buy_count += 1
            elif sig.signal_type == SignalType.SELL:
                sell_weight += sig.strength
                sell_count += 1

        total = len(self._strategies) or 1
        if buy_count >= 2 and buy_weight > sell_weight:
            strength = round(min(0.95, buy_weight / total + 0.1), 2)
            return TradeSignal(SignalType.BUY, strength, f"{buy_count}个策略看多(加权{buy_weight:.2f})")
        if sell_count >= 2 and sell_weight > buy_weight:
            strength = round(min(0.95, sell_weight / total + 0.1), 2)
            return TradeSignal(SignalType.SELL, strength, f"{sell_count}个策略看空(加权{sell_weight:.2f})")
        return TradeSignal(SignalType.HOLD, 0.0, "多空分歧")

    def _strength_weighted(self, signals: dict[str, TradeSignal]) -> TradeSignal:
        """Strength-weighted: net strength determines direction and magnitude."""
        net = 0.0
        for sig in signals.values():
            if sig.signal_type == SignalType.BUY:
                net += sig.strength
            elif sig.signal_type == SignalType.SELL:
                net -= sig.strength

        if abs(net) < self._min_agreement:
            return TradeSignal(SignalType.HOLD, 0.0, "净强度不足")

        if net > 0:
            return TradeSignal(SignalType.BUY, round(min(0.95, net), 2), f"净多头强度{net:.2f}")
        return TradeSignal(SignalType.SELL, round(min(0.95, abs(net)), 2), f"净空头强度{abs(net):.2f}")

    def _unanimous(self, signals: dict[str, TradeSignal]) -> TradeSignal:
        """Unanimous: only signal if all strategies agree."""
        if not signals:
            return TradeSignal(SignalType.HOLD)

        types = {sig.signal_type for sig in signals.values()}
        if len(types) == 1 and SignalType.HOLD not in types:
            sig_type = types.pop()
            avg_strength = np.mean([s.strength for s in signals.values()])
            return TradeSignal(sig_type, round(avg_strength, 2), "全策略一致")
        return TradeSignal(SignalType.HOLD, 0.0, "策略不一致")

    def _build_indicator_request(self) -> IndicatorRequest:
        """Build a combined IndicatorRequest from all strategies."""
        req = IndicatorRequest()
        for s in self._strategies:
            name = s.name.lower()
            if "rsi" in name:
                req.rsi = True
            if "macd" in name:
                req.macd = True
            if "bollinger" in name or "boll" in name:
                req.boll = True
            if "atr" in name or "supertrend" in name or "turtle" in name:
                req.atr = True
            if "ma" in name or "dual" in name or "trend" in name or "momentum" in name:
                req.ma = True
            if "ema" in name or "macd" in name:
                req.ema = True
            if "kdj" in name:
                req.kdj = True
            if "supertrend" in name:
                req.supertrend = True
            if "vwap" in name:
                req.vwap = True
            if "adx" in name:
                req.adx = True
            if "cmf" in name or "chaikin" in name:
                req.cmf = True
            if "volume" in name or "flow" in name:
                req.volume_ratio = True
        return req

    @staticmethod
    def from_composite(composite) -> "StrategyPipeline":
        """Create a pipeline from an existing CompositeStrategy instance."""
        pipeline = StrategyPipeline(strategies=composite.strategies)
        return pipeline
