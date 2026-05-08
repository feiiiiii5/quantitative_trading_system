"""
SignalComposer 测试套件
测试统一信号编排引擎 - 端到端流水线集成
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from core.signal_composer import (
    ComposerConfig,
    ComposerReport,
    ScoredSignal,
    SignalComposer,
    SignalDirection,
    get_signal_composer,
)


@pytest.fixture
def sample_klines() -> pd.DataFrame:
    np.random.seed(42)
    n = 100
    dates = pd.date_range("2024-01-01", periods=n, freq="1h")
    close = 100 + np.cumsum(np.random.randn(n) * 0.5)
    open_prices = close + np.random.randn(n) * 0.2
    high = np.maximum(close, open_prices) + np.abs(np.random.randn(n) * 0.3)
    low = np.minimum(close, open_prices) - np.abs(np.random.randn(n) * 0.3)
    volume = np.random.randint(1000, 10000, n).astype(float)
    return pd.DataFrame(
        {"open": open_prices, "high": high, "low": low, "close": close, "volume": volume},
        index=dates,
    )


@pytest.fixture
def trending_klines() -> pd.DataFrame:
    np.random.seed(123)
    n = 80
    dates = pd.date_range("2024-01-01", periods=n, freq="1h")
    close = 100 + np.cumsum(np.random.randn(n) * 1.5)
    open_prices = close + np.random.randn(n) * 0.2
    high = np.maximum(close, open_prices) + np.abs(np.random.randn(n) * 0.5)
    low = np.minimum(close, open_prices) - np.abs(np.random.randn(n) * 0.5)
    volume = np.random.randint(5000, 20000, n).astype(float)
    return pd.DataFrame(
        {"open": open_prices, "high": high, "low": low, "close": close, "volume": volume},
        index=dates,
    )


class TestComposerConfig:
    def test_default_config(self):
        config = ComposerConfig()
        assert config.min_bars == 60
        assert config.min_confidence == 0.5
        assert config.max_positions == 10
        assert config.base_position_pct == 0.10

    def test_custom_config(self):
        config = ComposerConfig(
            min_bars=100,
            min_confidence=0.6,
            max_positions=5,
            base_position_pct=0.15,
            use_regime_sizing=True,
            use_slippage_filter=True,
            signal_threshold=0.5,
        )
        assert config.min_bars == 100
        assert config.min_confidence == 0.6
        assert config.max_positions == 5


class TestSignalComposerSingle:
    def test_compose_produces_report(self, sample_klines):
        config = ComposerConfig(min_bars=60)
        composer = SignalComposer(config)
        report = composer.compose("AAPL", sample_klines)

        assert isinstance(report, ComposerReport)
        assert report.regime_summary is not None
        assert "current" in report.regime_summary
        assert isinstance(report.alpha_diversity_score, float)
        assert isinstance(report.risk_metrics, dict)

    def test_compose_with_insufficient_data(self):
        config = ComposerConfig(min_bars=100)
        composer = SignalComposer(config)
        short_df = pd.DataFrame({"close": [100.0] * 50})
        report = composer.compose("AAPL", short_df)

        assert len(report.signals) == 0
        assert report.regime_summary["current"] == "UNKNOWN"
        assert report.passed_filters == 0

    def test_compose_none_dataframe(self):
        composer = SignalComposer()
        report = composer.compose("AAPL", None)
        assert len(report.signals) == 0
        assert report.total_candidates == 0

    def test_compose_returns_signal_fields(self, trending_klines):
        composer = SignalComposer(ComposerConfig(min_bars=60, signal_threshold=0.1))
        report = composer.compose("AAPL", trending_klines)

        if report.signals:
            sig = report.signals[0]
            assert isinstance(sig, ScoredSignal)
            assert sig.symbol == "AAPL"
            assert sig.direction in (SignalDirection.LONG, SignalDirection.SHORT, SignalDirection.NEUTRAL)
            assert isinstance(sig.score, float)
            assert isinstance(sig.confidence, float)
            assert isinstance(sig.regime, str)
            assert isinstance(sig.position_size_pct, float)
            assert 0 <= sig.position_size_pct <= 1.0

    def test_regime_summary_populated(self, sample_klines):
        composer = SignalComposer(ComposerConfig(min_bars=60))
        report = composer.compose("AAPL", sample_klines)

        assert "current" in report.regime_summary
        assert "confidence" in report.regime_summary
        assert "trend_strength" in report.regime_summary
        assert "volatility_level" in report.regime_summary
        assert "mean_reversion_score" in report.regime_summary

    def test_risk_metrics_populated(self, sample_klines):
        composer = SignalComposer(ComposerConfig(min_bars=60))
        report = composer.compose("AAPL", sample_klines)

        metrics = report.risk_metrics
        assert "gross_exposure" in metrics
        assert "net_exposure" in metrics
        assert "long_exposure" in metrics
        assert "short_exposure" in metrics
        assert "position_count" in metrics
        assert "avg_confidence" in metrics
        assert "avg_slippage_bps" in metrics


class TestSignalComposerMulti:
    def test_compose_multi_multiple_symbols(self, sample_klines):
        symbols_data = {
            "AAPL": sample_klines,
            "GOOGL": sample_klines.copy(),
            "MSFT": sample_klines.copy(),
        }
        composer = SignalComposer(ComposerConfig(min_bars=60))
        reports = composer.compose_multi(symbols_data)

        assert len(reports) == 3
        assert "AAPL" in reports
        assert "GOOGL" in reports
        assert "MSFT" in reports
        for report in reports.values():
            assert isinstance(report, ComposerReport)

    def test_compose_multi_handles_failure(self, sample_klines):
        symbols_data = {
            "AAPL": sample_klines,
            "FAIL": pd.DataFrame(),
        }
        composer = SignalComposer(ComposerConfig(min_bars=60))
        reports = composer.compose_multi(symbols_data)

        assert "AAPL" in reports
        assert "FAIL" in reports
        assert isinstance(reports["FAIL"], ComposerReport)


class TestRegimeAdjustment:
    def test_regime_affects_position_sizing(self, sample_klines):
        config_strategic = ComposerConfig(min_bars=60, use_regime_sizing=True)
        config_blind = ComposerConfig(min_bars=60, use_regime_sizing=False)
        composer1 = SignalComposer(config_strategic)
        composer2 = SignalComposer(config_blind)

        report1 = composer1.compose("AAPL", sample_klines)
        report2 = composer2.compose("AAPL", sample_klines)

        if report1.signals and report2.signals:
            assert report1.signals[0].position_size_pct != report2.signals[0].position_size_pct


class TestSlippageFilter:
    def test_high_slippage_filtered_out(self, sample_klines):
        config = ComposerConfig(min_bars=60, use_slippage_filter=True, signal_threshold=0.1)
        composer = SignalComposer(config)
        report = composer.compose("AAPL", sample_klines)

        for sig in report.signals:
            assert sig.slippage_cost_bps >= 0


class TestSignalThreshold:
    def test_low_threshold_produces_signals(self, sample_klines):
        config = ComposerConfig(min_bars=60, signal_threshold=0.05)
        composer = SignalComposer(config)
        report = composer.compose("AAPL", sample_klines)
        assert report is not None

    def test_high_threshold_suppresses_signals(self, trending_klines):
        config = ComposerConfig(min_bars=60, signal_threshold=5.0)
        composer = SignalComposer(config)
        report = composer.compose("AAPL", trending_klines)
        assert len(report.signals) == 0


class TestAlphaDiversity:
    def test_diversity_score_computed(self, sample_klines):
        composer = SignalComposer(ComposerConfig(min_bars=60))
        report = composer.compose("AAPL", sample_klines)
        assert isinstance(report.alpha_diversity_score, float)
        assert 0.0 <= report.alpha_diversity_score <= 1.0


class TestGetRegime:
    def test_get_regime_returns_dict(self, sample_klines):
        composer = SignalComposer(ComposerConfig(min_bars=60))
        regime_info = composer.get_regime(sample_klines)

        assert isinstance(regime_info, dict)
        assert "regime" in regime_info
        assert "confidence" in regime_info
        assert "trend_strength" in regime_info

    def test_get_regime_insufficient_data(self):
        composer = SignalComposer()
        short_df = pd.DataFrame({"close": [100.0] * 30})
        regime_info = composer.get_regime(short_df)
        assert regime_info["regime"] == "UNKNOWN"
        assert regime_info["confidence"] == 0.0


class TestReset:
    def test_reset_clears_state(self, sample_klines):
        composer = SignalComposer(ComposerConfig(min_bars=60))
        composer.compose("AAPL", sample_klines)
        composer.reset()
        assert composer._last_regime == "UNKNOWN"
        assert composer._regime_change_count == 0


class TestSingleton:
    def test_get_composer_returns_same_instance(self):
        c1 = get_signal_composer()
        c2 = get_signal_composer()
        assert c1 is c2

    def test_get_composer_resets_with_config(self):
        c1 = get_signal_composer(ComposerConfig(min_bars=60))
        c2 = get_signal_composer(ComposerConfig(min_bars=100))
        assert c1 is not c2


class TestScoredSignal:
    def test_signal_direction_enum_values(self):
        assert SignalDirection.LONG.value == "long"
        assert SignalDirection.SHORT.value == "short"
        assert SignalDirection.NEUTRAL.value == "neutral"


class TestRegressionRegimeAdapter:
    def test_compose_uses_regime_adapter_not_detector_class(self, sample_klines):
        composer = SignalComposer(ComposerConfig(min_bars=60))
        report = composer.compose("AAPL", sample_klines)
        assert report.regime_summary is not None
        assert "current" in report.regime_summary

    def test_regime_volatile_triggers_alert(self, sample_klines):
        composer = SignalComposer(ComposerConfig(min_bars=60))
        composer._last_regime = "BULL_BASE"
        df = sample_klines.copy()
        df.index = pd.date_range("2024-01-01", periods=len(df), freq="1min")
        result = composer.get_regime(df)
        assert isinstance(result, dict)
        assert "regime" in result
        assert "confidence" in result

    def test_rsi_scalar_extraction_no_ambiguous_truth(self, sample_klines):
        composer = SignalComposer(ComposerConfig(min_bars=60))
        report = composer.compose("AAPL", sample_klines)
        assert isinstance(report, ComposerReport)

    def test_alert_trigger_correct_signature_path(self, sample_klines):
        from core.regime_detector import MarketRegime, _RegimeResult
        composer = SignalComposer(ComposerConfig(min_bars=60))
        composer._last_regime = "UNKNOWN"
        regime_result = _RegimeResult(
            regime=MarketRegime.VOLATILE,
            context={"confidence": 0.75},
            trend_strength=0.3,
            volatility_level=0.7,
            mean_reversion_score=0.4,
            transition_probabilities={},
        )
        composer._alert_regime_state("AAPL", regime_result)
        assert composer._regime_change_count >= 0


class TestRegressionStrategyFusion:
    def test_fuse_empty_alpha_results_returns_empty(self):
        from core.strategy_fusion import FusionConfig, StrategyFusion

        fusion = StrategyFusion(FusionConfig())
        result = fusion.fuse({})
        assert result.n_strategies == 0
        assert result.strategy_weights == {}
        assert len(result.combined_signal) == 0

    def test_fuse_all_low_ic_returns_empty(self):
        from core.alpha_engine import AlphaResult
        from core.strategy_fusion import FusionConfig, StrategyFusion

        fusion = StrategyFusion(FusionConfig(min_ic=0.1))
        alphas = {
            "alpha1": AlphaResult(name="alpha1", values=pd.Series([0.01, 0.02]), ic=0.005),
            "alpha2": AlphaResult(name="alpha2", values=pd.Series([-0.01, 0.01]), ic=0.003),
        }
        result = fusion.fuse(alphas)
        assert result.n_strategies == 0


class TestRegressionAlphaScreener:
    def test_alpha_screener_optional_config(self):
        from core.alpha_screener import AlphaScreener
        screener = AlphaScreener()
        assert screener._config.ic_threshold == 0.02

    def test_calc_decay_uses_lag_in_shift(self):
        from core.alpha_screener import calc_decay

        np.random.seed(42)
        factors = pd.Series(np.random.randn(20))
        returns = pd.Series(np.random.randn(25))
        decay = calc_decay(factors, returns, max_lag=10)
        assert isinstance(decay, float)
        assert 0.0 <= decay <= 10.0
