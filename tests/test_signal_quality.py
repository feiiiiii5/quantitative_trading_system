import numpy as np
import pandas as pd

from core.signal_quality import evaluate_signal_quality
from core.strategies import BaseStrategy, SignalType, StrategyResult


class _AlwaysBuy(BaseStrategy):
    name = "always_buy"

    def generate_signals(self, df: pd.DataFrame) -> StrategyResult:
        signals = []
        for i in range(len(df)):
            signals.append({"bar_index": i, "type": SignalType.BUY, "price": df["close"].iloc[i]})
        return StrategyResult(signals=signals, strategy_name=self.name)


class _AlwaysSell(BaseStrategy):
    name = "always_sell"

    def generate_signals(self, df: pd.DataFrame) -> StrategyResult:
        signals = []
        for i in range(len(df)):
            signals.append({"bar_index": i, "type": SignalType.SELL, "price": df["close"].iloc[i]})
        return StrategyResult(signals=signals, strategy_name=self.name)


class _NoSignal(BaseStrategy):
    name = "no_signal"

    def generate_signals(self, df: pd.DataFrame) -> StrategyResult:
        return StrategyResult(signals=[], strategy_name=self.name)


def _make_df(n: int = 100, trend: str = "up") -> pd.DataFrame:
    dates = pd.date_range("2024-01-01", periods=n, freq="B")
    if trend == "up":
        close = np.cumsum(np.random.default_rng(42).normal(0.1, 1, n)) + 100
    elif trend == "down":
        close = np.cumsum(np.random.default_rng(42).normal(-0.1, 1, n)) + 100
    else:
        close = np.cumsum(np.random.default_rng(42).normal(0, 1, n)) + 100
    return pd.DataFrame({
        "date": dates,
        "open": close - 0.5,
        "high": close + 1,
        "low": close - 1,
        "close": close,
        "volume": np.random.default_rng(42).integers(1000, 10000, n),
    })


class TestSignalQuality:
    def test_empty_df(self):
        report = evaluate_signal_quality(_AlwaysBuy(), pd.DataFrame(), "TEST")
        assert report.total_signals == 0

    def test_none_df(self):
        report = evaluate_signal_quality(_AlwaysBuy(), None, "TEST")
        assert report.total_signals == 0

    def test_short_df(self):
        report = evaluate_signal_quality(_AlwaysBuy(), _make_df(5), "TEST")
        assert report.total_signals == 0

    def test_no_signal_strategy(self):
        report = evaluate_signal_quality(_NoSignal(), _make_df(100), "TEST")
        assert report.total_signals == 0
        assert report.precision == 0

    def test_always_buy_uptrend(self):
        df = _make_df(100, trend="up")
        report = evaluate_signal_quality(_AlwaysBuy(), df, "TEST")
        assert report.buy_signals > 0
        assert report.buy_precision > 0
        assert report.total_signals > 0

    def test_always_sell_downtrend(self):
        df = _make_df(100, trend="down")
        report = evaluate_signal_quality(_AlwaysSell(), df, "TEST")
        assert report.sell_signals > 0
        assert report.sell_precision > 0

    def test_report_to_dict(self):
        df = _make_df(100, trend="up")
        report = evaluate_signal_quality(_AlwaysBuy(), df, "TEST")
        d = report.to_dict()
        assert "strategy_name" in d
        assert "precision" in d
        assert "confusion_matrix" in d
        assert "buy_precision" in d
        assert "sell_precision" in d
        assert "signal_density" in d

    def test_forward_period_parameter(self):
        df = _make_df(100, trend="up")
        report_5 = evaluate_signal_quality(_AlwaysBuy(), df, "TEST", forward_period=5)
        report_20 = evaluate_signal_quality(_AlwaysBuy(), df, "TEST", forward_period=20)
        assert report_5.total_signals == report_20.total_signals

    def test_threshold_parameter(self):
        df = _make_df(100, trend="up")
        report_low = evaluate_signal_quality(_AlwaysBuy(), df, "TEST", min_return_threshold=0.001)
        report_high = evaluate_signal_quality(_AlwaysBuy(), df, "TEST", min_return_threshold=0.05)
        assert report_low.precision >= report_high.precision or report_low.buy_signals == report_high.buy_signals

    def test_confusion_matrix_structure(self):
        df = _make_df(100, trend="up")
        report = evaluate_signal_quality(_AlwaysBuy(), df, "TEST")
        cm = report.confusion_matrix
        assert "buy" in cm
        assert "sell" in cm
        assert "overall" in cm
        assert "tp" in cm["buy"]
        assert "fp" in cm["buy"]
        assert "fn" in cm["buy"]

    def test_holding_period_stats(self):
        df = _make_df(100, trend="up")
        report = evaluate_signal_quality(_AlwaysBuy(), df, "TEST")
        if report.holding_period_stats:
            assert "mean" in report.holding_period_stats
            assert "median" in report.holding_period_stats
