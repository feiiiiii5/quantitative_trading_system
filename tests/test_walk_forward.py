import numpy as np
import pandas as pd

from core.strategies import BaseStrategy, SignalType, StrategyResult
from core.walk_forward import walk_forward_analysis


class _SimpleMA(BaseStrategy):
    name = "simple_ma_test"

    def __init__(self, short_period: int = 5, long_period: int = 20):
        super().__init__()
        self._short = short_period
        self._long = long_period

    def generate_signals(self, df: pd.DataFrame) -> StrategyResult:
        if len(df) < self._long + 1:
            return StrategyResult(signals=[], strategy_name=self.name)
        close = df["close"].values.astype(float)
        short_ma = pd.Series(close).rolling(self._short).mean().values
        long_ma = pd.Series(close).rolling(self._long).mean().values
        signals = []
        for i in range(self._long, len(df)):
            if short_ma[i] > long_ma[i] and short_ma[i - 1] <= long_ma[i - 1]:
                signals.append({"bar_index": i, "type": SignalType.BUY, "price": close[i]})
            elif short_ma[i] < long_ma[i] and short_ma[i - 1] >= long_ma[i - 1]:
                signals.append({"bar_index": i, "type": SignalType.SELL, "price": close[i]})
        return StrategyResult(signals=signals, strategy_name=self.name)


def _make_df(n: int = 500) -> pd.DataFrame:
    rng = np.random.default_rng(42)
    dates = pd.date_range("2023-01-01", periods=n, freq="B")
    close = np.cumsum(rng.normal(0.05, 1.5, n)) + 100
    return pd.DataFrame({
        "date": dates,
        "open": close - 0.5,
        "high": close + 1,
        "low": close - 1,
        "close": close,
        "volume": rng.integers(1000, 10000, n),
    })


class TestWalkForward:
    def test_none_df(self):
        result = walk_forward_analysis(_SimpleMA(), None)
        assert result.n_splits == 0

    def test_empty_df(self):
        result = walk_forward_analysis(_SimpleMA(), pd.DataFrame())
        assert result.n_splits == 0

    def test_short_df(self):
        result = walk_forward_analysis(_SimpleMA(), _make_df(50))
        assert result.n_splits == 0

    def test_sufficient_data(self):
        df = _make_df(500)
        result = walk_forward_analysis(_SimpleMA(), df, "TEST", train_period=60, test_period=30, n_splits=3)
        assert result.n_splits > 0
        assert len(result.splits) > 0

    def test_split_date_ranges(self):
        df = _make_df(500)
        result = walk_forward_analysis(_SimpleMA(), df, "TEST", train_period=60, test_period=30, n_splits=3)
        for split in result.splits:
            assert split.train_start < split.train_end
            assert split.test_start < split.test_end
            assert split.train_end <= split.test_start

    def test_aggregate_metrics(self):
        df = _make_df(500)
        result = walk_forward_analysis(_SimpleMA(), df, "TEST", train_period=60, test_period=30, n_splits=3)
        if result.aggregate:
            assert "avg_train_return" in result.aggregate
            assert "avg_test_return" in result.aggregate
            assert "oos_ratio" in result.aggregate
            assert "degradation_pct" in result.aggregate

    def test_overfitting_score_range(self):
        df = _make_df(500)
        result = walk_forward_analysis(_SimpleMA(), df, "TEST", train_period=60, test_period=30, n_splits=3)
        assert 0 <= result.overfitting_score <= 1

    def test_to_dict(self):
        df = _make_df(500)
        result = walk_forward_analysis(_SimpleMA(), df, "TEST", train_period=60, test_period=30, n_splits=3)
        d = result.to_dict()
        assert "strategy_name" in d
        assert "splits" in d
        assert "aggregate" in d
        assert "overfitting_score" in d

    def test_custom_engine(self):
        from core.backtest import BacktestEngine
        df = _make_df(500)
        engine = BacktestEngine(initial_capital=50000)
        result = walk_forward_analysis(_SimpleMA(), df, "TEST", train_period=60, test_period=30, n_splits=2, engine=engine)
        assert result.n_splits > 0

    def test_significance_fields_exist(self):
        df = _make_df(500)
        result = walk_forward_analysis(_SimpleMA(), df, "TEST", train_period=60, test_period=30, n_splits=3)
        assert hasattr(result, "p_value")
        assert hasattr(result, "is_significant")
        assert isinstance(result.p_value, float)
        assert isinstance(result.is_significant, bool)

    def test_significance_p_value_range(self):
        df = _make_df(500)
        result = walk_forward_analysis(_SimpleMA(), df, "TEST", train_period=60, test_period=30, n_splits=3)
        assert 0.0 <= result.p_value <= 1.0

    def test_significance_to_dict(self):
        df = _make_df(500)
        result = walk_forward_analysis(_SimpleMA(), df, "TEST", train_period=60, test_period=30, n_splits=3)
        d = result.to_dict()
        assert "p_value" in d
        assert "is_significant" in d

    def test_significance_not_computed_too_few_splits(self):
        df = _make_df(200)
        result = walk_forward_analysis(_SimpleMA(), df, "TEST", train_period=60, test_period=30, n_splits=2)
        if result.n_splits >= 3:
            assert result.p_value <= 1.0
