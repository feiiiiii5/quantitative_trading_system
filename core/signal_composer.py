"""
SignalComposer - 统一信号编排引擎 (GEN-3 Paradigm Shift)
将所有GEN-2组件编排为一条端到端流水线:
  FeatureEngineer → AlphaEngine → RegimeDetector → SignalScorer → PortfolioComposer

这个模块是将"孤立组件"转变为"统一系统"的关键跨越。
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from threading import Lock

import numpy as np
import pandas as pd

from core.alert_system import (
    AlertSeverity,
    AlertType,
    get_alert_manager,
)
from core.alpha_engine import AlphaGenerator
from core.feature_engineer import FeatureResult, get_feature_engineer
from core.paper_engine import get_paper_engine
from core.portfolio_rebalancer import get_rebalancer
from core.regime_detector import MarketRegime, RegimeAdapter
from core.slippage_engine import get_slippage_engine

logger = logging.getLogger(__name__)


class SignalDirection(Enum):
    LONG = "long"
    SHORT = "short"
    NEUTRAL = "neutral"


@dataclass
class ScoredSignal:
    symbol: str
    direction: SignalDirection
    score: float
    confidence: float
    regime: str
    regime_confidence: float
    top_factors: list[str]
    alpha_value: float
    slippage_cost_bps: float
    position_size_pct: float
    entry_reason: str
    timestamp: str


@dataclass
class ComposerConfig:
    min_bars: int = 60
    min_confidence: float = 0.5
    max_positions: int = 10
    base_position_pct: float = 0.10
    use_regime_sizing: bool = True
    use_slippage_filter: bool = True
    use_paper_validation: bool = True
    signal_threshold: float = 0.3


@dataclass
class ComposerReport:
    signals: list[ScoredSignal]
    regime_summary: dict
    alpha_diversity_score: float
    portfolio_weights: dict[str, float]
    risk_metrics: dict
    total_candidates: int
    passed_filters: int


class SignalComposer:
    def __init__(self, config: ComposerConfig | None = None):
        self._config = config or ComposerConfig()
        self._feature_eng = get_feature_engineer()
        self._alpha_gen = AlphaGenerator()
        self._regime_detector = RegimeAdapter()
        self._slippage_eng = get_slippage_engine()
        self._paper_eng = get_paper_engine()
        self._rebalancer = get_rebalancer()
        self._alert_mgr = get_alert_manager()
        self._lock = Lock()
        self._last_regime: str = "UNKNOWN"
        self._regime_change_count: int = 0

    def compose(self, symbol: str, df: pd.DataFrame) -> ComposerReport:
        with self._lock:
            return self._compose_impl(symbol, df)

    def _compose_impl(self, symbol: str, df: pd.DataFrame) -> ComposerReport:
        if df is None or len(df) < self._config.min_bars:
            return self._empty_report()

        df = df.copy()
        for col in ["open", "high", "low", "close", "volume"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        features = self._feature_eng.build_features(df)
        if features.features.empty:
            return self._empty_report()

        regime_result = self._regime_detector.detect(df)
        current_regime = regime_result.current_regime
        regime_confidence = regime_result.confidence
        self._check_regime_change(symbol, current_regime)

        alpha_signals = self._alpha_gen.compute_all_alphas(df)
        alpha_signal = self._aggregate_alpha_signals(alpha_signals)

        positions = self._score_positions(
            symbol, features, regime_result, alpha_signal
        )

        positions = self._apply_filters(positions)

        self._validate_with_paper(positions, symbol, df)

        portfolio_weights = self._compute_portfolio_weights(positions)

        report = ComposerReport(
            signals=positions,
            regime_summary={
                "current": current_regime,
                "confidence": regime_confidence,
                "trend_strength": getattr(regime_result, "trend_strength", 0.0),
                "volatility_level": getattr(regime_result, "volatility_level", 0.0),
                "mean_reversion_score": getattr(regime_result, "mean_reversion_score", 0.5),
            },
            alpha_diversity_score=self._diversity_score(alpha_signals),
            portfolio_weights=portfolio_weights,
            risk_metrics=self._compute_risk_metrics(positions, portfolio_weights),
            total_candidates=1,
            passed_filters=len(positions),
        )

        self._alert_regime_state(symbol, regime_result)
        return report

    def compose_multi(
        self, symbols_data: dict[str, pd.DataFrame]
    ) -> dict[str, ComposerReport]:
        reports = {}
        for symbol, df in symbols_data.items():
            try:
                reports[symbol] = self.compose(symbol, df)
            except Exception as e:
                logger.debug("Symbol %s composition failed: %s", symbol, e)
                reports[symbol] = self._empty_report()
        return reports

    def _score_positions(
        self,
        symbol: str,
        features: FeatureResult,
        regime_result,
        alpha_signal: float,
    ) -> list[ScoredSignal]:
        regime = regime_result.current_regime
        confidence = regime_result.confidence
        base_score = alpha_signal

        if self._config.use_regime_sizing:
            base_score = self._regime_adjust_score(
                base_score, regime, confidence, features
            )

        if abs(base_score) < self._config.signal_threshold:
            return []

        direction = (
            SignalDirection.LONG if base_score > 0 else SignalDirection.SHORT
        )
        abs_score = abs(base_score)
        confidence_score = min(abs_score, 1.0)

        slippage = self._slippage_eng.estimate(
            "buy" if direction == SignalDirection.LONG else "sell",
            100.0,
            1000,
            100000,
            0.02,
        )

        regime_factor = self._regime_to_position_factor(regime)
        position_pct = (
            self._config.base_position_pct
            * confidence_score
            * regime_factor
        )
        position_pct = min(position_pct, 0.30)

        top_factors = self._extract_top_factors(features)

        return [
            ScoredSignal(
                symbol=symbol,
                direction=direction,
                score=round(base_score, 4),
                confidence=round(confidence_score, 3),
                regime=str(regime.value) if isinstance(regime, MarketRegime) else str(regime),
                regime_confidence=round(confidence, 3),
                top_factors=top_factors[:5],
                alpha_value=round(alpha_signal, 4),
                slippage_cost_bps=round(slippage.total_cost_bps, 2),
                position_size_pct=round(position_pct, 4),
                entry_reason=f"{direction.value.upper()} signal, regime={regime}, confidence={confidence:.2f}",
                timestamp=pd.Timestamp.now().isoformat(),
            )
        ]

    def _regime_adjust_score(
        self,
        base_score: float,
        regime: MarketRegime,
        confidence: float,
        features: FeatureResult,
    ) -> float:
        factor = 1.0

        if regime == MarketRegime.VOLATILE:
            factor = 0.5
        elif regime == MarketRegime.BULL_BREAKOUT:
            factor = 1.2
        elif regime == MarketRegime.BEAR_DISTRIBUTION:
            factor = 0.8
        elif regime == MarketRegime.DISTRIBUTED_HIGH:
            factor = 0.6

        rsi_vals = features.features.filter(like="rsi_")
        if not rsi_vals.empty:
            latest_rsi = rsi_vals.iloc[-1]
            if not isinstance(latest_rsi, pd.Series):
                latest_rsi = pd.Series([latest_rsi])
            rsi_scalar = latest_rsi.dropna().iloc[-1] if not latest_rsi.dropna().empty else None
            if rsi_scalar is not None and (rsi_scalar > 80 or rsi_scalar < 20):
                factor *= 0.7

        if confidence < 0.5:
            factor *= 0.8

        return base_score * factor

    def _regime_to_position_factor(self, regime: MarketRegime) -> float:
        factors = {
            MarketRegime.BULL_BREAKOUT: 1.0,
            MarketRegime.BULL_BASE: 0.9,
            MarketRegime.BEAR_RALLY: 0.7,
            MarketRegime.DISTRIBUTED_HIGH: 0.5,
            MarketRegime.BEAR_DISTRIBUTION: 0.6,
            MarketRegime.VOLATILE: 0.4,
            MarketRegime.UNKNOWN: 0.5,
        }
        return factors.get(regime, 0.5)

    def _aggregate_alpha_signals(
        self, alpha_signals: dict[str, pd.Series]
    ) -> float:
        if not alpha_signals:
            return 0.0

        scores = []
        for _name, series in alpha_signals.items():
            if series is not None and len(series) > 0:
                recent = series.dropna().tail(5)
                if len(recent) > 0:
                    avg = float(recent.mean())
                    if np.isfinite(avg):
                        scores.append(avg)

        if not scores:
            return 0.0

        return float(np.mean(scores))

    def _extract_top_factors(
        self, features: FeatureResult
    ) -> list[str]:
        factors = []
        feat_df = features.features
        if feat_df.empty:
            return factors

        numeric_cols = feat_df.select_dtypes(include=[np.number]).columns
        for col in numeric_cols:
            vals = feat_df[col].dropna()
            if len(vals) > 0:
                latest = float(vals.iloc[-1])
                if np.isfinite(latest):
                    factors.append(f"{col}={latest:.3f}")

        factors.sort()
        return factors[:10]

    def _apply_filters(
        self, positions: list[ScoredSignal]
    ) -> list[ScoredSignal]:
        filtered = []
        for pos in positions:
            if pos.confidence < self._config.min_confidence:
                continue

            if self._config.use_slippage_filter:
                max_slippage = 50.0
                if pos.slippage_cost_bps > max_slippage:
                    continue

            filtered.append(pos)

        filtered.sort(key=lambda x: abs(x.score), reverse=True)
        return filtered[: self._config.max_positions]

    def _validate_with_paper(
        self, positions: list[ScoredSignal], symbol: str, df: pd.DataFrame
    ) -> None:
        if not positions or not self._config.use_paper_validation:
            return

        try:
            paper = get_paper_engine()
            if paper is None:
                return

            close = df["close"].iloc[-1] if len(df) > 0 else 100.0
            for pos in positions[:3]:
                order = paper.submit_order(
                    symbol,
                    "buy" if pos.direction == SignalDirection.LONG else "sell",
                    int(pos.position_size_pct * 100000 / close),
                    close,
                )
                if order.status == "rejected":
                    logger.debug(
                        f"Paper validation rejected {symbol}: {order.rejection_reason}"
                    )
        except Exception as e:
            logger.debug("Paper validation failed: %s", e)

    def _compute_portfolio_weights(
        self, positions: list[ScoredSignal]
    ) -> dict[str, float]:
        weights = {}
        if not positions:
            return weights

        total_score = sum(abs(p.score) * p.confidence for p in positions)
        if total_score < 1e-9:
            for pos in positions:
                weights[pos.symbol] = pos.position_size_pct
            return weights

        for pos in positions:
            weight = (abs(pos.score) * pos.confidence / total_score) * sum(
                p.position_size_pct for p in positions
            )
            weights[pos.symbol] = round(weight, 4)

        return weights

    def _compute_risk_metrics(
        self,
        positions: list[ScoredSignal],
        weights: dict[str, float],
    ) -> dict:
        if not positions:
            return {
                "gross_exposure": 0.0,
                "net_exposure": 0.0,
                "long_exposure": 0.0,
                "short_exposure": 0.0,
                "position_count": 0,
                "avg_confidence": 0.0,
                "avg_slippage_bps": 0.0,
            }

        long_exp = sum(
            w for p, w in weights.items()
            if any(pos.symbol == p and pos.direction == SignalDirection.LONG for pos in positions)
        )
        short_exp = sum(
            w for p, w in weights.items()
            if any(pos.symbol == p and pos.direction == SignalDirection.SHORT for pos in positions)
        )

        return {
            "gross_exposure": round(long_exp + short_exp, 4),
            "net_exposure": round(long_exp - short_exp, 4),
            "long_exposure": round(long_exp, 4),
            "short_exposure": round(short_exp, 4),
            "position_count": len(positions),
            "avg_confidence": round(
                sum(p.confidence for p in positions) / len(positions), 3
            ),
            "avg_slippage_bps": round(
                sum(p.slippage_cost_bps for p in positions) / len(positions), 2
            ),
        }

    def _diversity_score(self, alpha_signals: dict[str, pd.Series]) -> float:
        if len(alpha_signals) < 2:
            return 0.0

        series_list = []
        for _name, s in alpha_signals.items():
            if s is not None and len(s) > 5:
                recent = s.dropna().tail(10)
                if len(recent) > 2:
                    arr = recent.values.astype(float)
                    arr = arr[np.isfinite(arr)]
                    if len(arr) > 2:
                        series_list.append(arr)

        if len(series_list) < 2:
            return 0.0

        n = len(series_list)
        correlations = []
        for i in range(n):
            for j in range(i + 1, n):
                min_len = min(len(series_list[i]), len(series_list[j]))
                if min_len < 3:
                    continue
                a = series_list[i][:min_len]
                b = series_list[j][:min_len]
                cov = np.corrcoef(a, b)[0, 1]
                if np.isfinite(cov):
                    correlations.append(abs(cov))

        if not correlations:
            return 1.0

        avg_corr = np.mean(correlations)
        diversity = 1.0 - avg_corr
        return round(float(diversity), 3)

    def _check_regime_change(
        self, symbol: str, new_regime: MarketRegime
    ) -> None:
        regime_str = new_regime.value if isinstance(new_regime, MarketRegime) else str(new_regime)
        if regime_str != self._last_regime and self._last_regime != "UNKNOWN":
            self._regime_change_count += 1
            self._alert_mgr.trigger(
                AlertType.REGIME_CHANGE,
                symbol,
                {
                    "old_regime": self._last_regime,
                    "new_regime": regime_str,
                    "change_number": self._regime_change_count,
                },
                AlertSeverity.WARNING,
            )
        self._last_regime = regime_str

    def _alert_regime_state(
        self, symbol: str, regime_result
    ) -> None:
        regime = regime_result.current_regime
        confidence = regime_result.confidence

        if regime == MarketRegime.VOLATILE and confidence > 0.7:
            self._alert_mgr.trigger(
                AlertType.REGIME_CHANGE,
                AlertSeverity.WARNING,
                symbol,
                f"High volatility regime detected: {regime.value}",
                value=confidence,
                threshold=0.7,
                metadata={"regime": regime.value, "confidence": confidence},
            )
        elif regime == MarketRegime.BULL_BREAKOUT and confidence > 0.8:
            self._alert_mgr.trigger(
                AlertType.REGIME_CHANGE,
                AlertSeverity.INFO,
                symbol,
                f"Bull breakout regime: {regime.value}",
                value=confidence,
                threshold=0.8,
                metadata={"regime": regime.value, "confidence": confidence},
            )

    def _empty_report(self) -> ComposerReport:
        return ComposerReport(
            signals=[],
            regime_summary={
                "current": "UNKNOWN",
                "confidence": 0.0,
                "trend_strength": 0.0,
                "volatility_level": 0.0,
                "mean_reversion_score": 0.5,
            },
            alpha_diversity_score=0.0,
            portfolio_weights={},
            risk_metrics={
                "gross_exposure": 0.0,
                "net_exposure": 0.0,
                "long_exposure": 0.0,
                "short_exposure": 0.0,
                "position_count": 0,
                "avg_confidence": 0.0,
                "avg_slippage_bps": 0.0,
            },
            total_candidates=0,
            passed_filters=0,
        )

    def get_regime(self, df: pd.DataFrame) -> dict:
        if df is None or len(df) < self._config.min_bars:
            return {"regime": "UNKNOWN", "confidence": 0.0}
        result = self._regime_detector.detect(df)
        regime = result.current_regime
        return {
            "regime": regime.value if isinstance(regime, MarketRegime) else str(regime),
            "confidence": result.confidence,
            "trend_strength": getattr(result, "trend_strength", 0.0),
            "volatility_level": getattr(result, "volatility_level", 0.0),
            "mean_reversion_score": getattr(result, "mean_reversion_score", 0.5),
            "transition_probabilities": getattr(result, "transition_probabilities", {}),
        }

    def reset(self) -> None:
        with self._lock:
            self._last_regime = "UNKNOWN"
            self._regime_change_count = 0
            self._paper_eng.reset()


_composer: SignalComposer | None = None


def get_signal_composer(config: ComposerConfig | None = None) -> SignalComposer:
    global _composer
    if _composer is None or config is not None:
        _composer = SignalComposer(config)
    return _composer
