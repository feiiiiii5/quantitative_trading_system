import numpy as np
import pandas as pd

from core.seasonality import analyze_seasonality


def _make_df(n: int = 500) -> pd.DataFrame:
    rng = np.random.default_rng(42)
    dates = pd.date_range("2022-01-01", periods=n, freq="B")
    close = np.cumsum(rng.normal(0.05, 1.5, n)) + 100
    return pd.DataFrame({
        "date": dates,
        "open": close - 0.5,
        "high": close + 1,
        "low": close - 1,
        "close": close,
        "volume": rng.integers(1000, 10000, n),
    })


class TestSeasonality:
    def test_none_df(self):
        report = analyze_seasonality(None)
        assert report.symbol == ""

    def test_empty_df(self):
        report = analyze_seasonality(pd.DataFrame())
        assert report.seasonality_strength == 0

    def test_short_df(self):
        report = analyze_seasonality(_make_df(10))
        assert report.seasonality_strength == 0

    def test_sufficient_data(self):
        df = _make_df(500)
        report = analyze_seasonality(df, symbol="TEST", period="2y")
        assert report.symbol == "TEST"
        assert len(report.monthly_returns) > 0
        assert len(report.day_of_week_returns) > 0

    def test_monthly_returns(self):
        df = _make_df(500)
        report = analyze_seasonality(df, symbol="TEST")
        assert "Jan" in report.monthly_returns
        assert isinstance(report.monthly_returns["Jan"], float)

    def test_day_of_week_returns(self):
        df = _make_df(500)
        report = analyze_seasonality(df, symbol="TEST")
        assert "Mon" in report.day_of_week_returns
        assert "Fri" in report.day_of_week_returns

    def test_best_worst_month(self):
        df = _make_df(500)
        report = analyze_seasonality(df, symbol="TEST")
        assert report.best_month != ""
        assert report.worst_month != ""

    def test_best_worst_day(self):
        df = _make_df(500)
        report = analyze_seasonality(df, symbol="TEST")
        assert report.best_day != ""
        assert report.worst_day != ""

    def test_monthly_sharpe(self):
        df = _make_df(500)
        report = analyze_seasonality(df, symbol="TEST")
        assert len(report.monthly_sharpe) > 0

    def test_turn_of_month_effect(self):
        df = _make_df(500)
        report = analyze_seasonality(df, symbol="TEST")
        if report.turn_of_month_effect:
            assert "tom_avg_return" in report.turn_of_month_effect
            assert "non_tom_avg_return" in report.turn_of_month_effect

    def test_seasonality_strength_range(self):
        df = _make_df(500)
        report = analyze_seasonality(df, symbol="TEST")
        assert 0 <= report.seasonality_strength <= 1

    def test_to_dict(self):
        df = _make_df(500)
        report = analyze_seasonality(df, symbol="TEST")
        d = report.to_dict()
        assert "monthly_returns" in d
        assert "day_of_week_returns" in d
        assert "seasonality_strength" in d
        assert "best_month" in d
        assert "worst_month" in d
