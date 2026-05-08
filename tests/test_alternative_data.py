from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd
import pytest

from core.alternative_data import (
    AlternativeDataManager,
    AlternativeDataSource,
    DataAlignmentTool,
    EarningsCallSource,
    NewsSentimentSource,
    SignalValidityChecker,
    SignalValidityReport,
    SocialMediaHeatSource,
)

_START = date(2024, 1, 2)
_END = date(2024, 3, 31)
_SYMBOLS = ["AAPL", "MSFT"]


class TestNewsSentimentSource:
    def test_news_sentiment_frequency(self) -> None:
        source = NewsSentimentSource()
        assert source.frequency == "D"

    def test_news_sentiment_name(self) -> None:
        source = NewsSentimentSource()
        assert source.name == "news_sentiment"

    def test_news_sentiment_fetch_returns_dataframe(self) -> None:
        source = NewsSentimentSource()
        df = source.fetch(_SYMBOLS, _START, _END)
        assert isinstance(df, pd.DataFrame)
        assert isinstance(df.index, pd.MultiIndex)
        assert df.index.names == ["symbol", "date"]

    def test_news_sentiment_fetch_columns(self) -> None:
        source = NewsSentimentSource()
        df = source.fetch(_SYMBOLS, _START, _END)
        assert "sentiment" in df.columns

    def test_news_sentiment_fetch_values_clipped(self) -> None:
        source = NewsSentimentSource()
        df = source.fetch(_SYMBOLS, _START, _END)
        assert df["sentiment"].min() >= -1.0
        assert df["sentiment"].max() <= 1.0


class TestEarningsCallSource:
    def test_earnings_call_frequency(self) -> None:
        source = EarningsCallSource()
        assert source.frequency == "event"

    def test_earnings_call_name(self) -> None:
        source = EarningsCallSource()
        assert source.name == "earnings_call"

    def test_earnings_call_fetch_returns_dataframe(self) -> None:
        source = EarningsCallSource()
        df = source.fetch(_SYMBOLS, _START, _END)
        assert isinstance(df, pd.DataFrame)
        assert isinstance(df.index, pd.MultiIndex)
        assert df.index.names == ["symbol", "date"]

    def test_earnings_call_fetch_columns(self) -> None:
        source = EarningsCallSource()
        df = source.fetch(_SYMBOLS, _START, _END)
        for col in ("sentiment", "surprise_pct", "guidance_sentiment"):
            assert col in df.columns

    def test_earnings_call_quarter_dates(self) -> None:
        source = EarningsCallSource()
        quarter_dates = source._quarter_dates(date(2024, 1, 1), date(2024, 12, 31))
        quarter_months = {d.month for d in quarter_dates}
        assert quarter_months == {1, 4, 7, 10}
        for d in quarter_dates:
            assert d.day == 15


class TestSocialMediaHeatSource:
    def test_social_media_frequency(self) -> None:
        source = SocialMediaHeatSource()
        assert source.frequency == "D"

    def test_social_media_name(self) -> None:
        source = SocialMediaHeatSource()
        assert source.name == "social_media_heat"

    def test_social_media_fetch_returns_dataframe(self) -> None:
        source = SocialMediaHeatSource()
        df = source.fetch(_SYMBOLS, _START, _END)
        assert isinstance(df, pd.DataFrame)
        assert isinstance(df.index, pd.MultiIndex)
        assert df.index.names == ["symbol", "date"]

    def test_social_media_fetch_columns(self) -> None:
        source = SocialMediaHeatSource()
        df = source.fetch(_SYMBOLS, _START, _END)
        for col in ("mention_count", "sentiment_score", "viral_score"):
            assert col in df.columns

    def test_social_media_fetch_viral_score_capped(self) -> None:
        source = SocialMediaHeatSource()
        df = source.fetch(_SYMBOLS, _START, _END)
        assert df["viral_score"].max() <= 1.0


class TestDataAlignmentTool:
    def test_data_alignment_daily_returns_asis(self) -> None:
        source = NewsSentimentSource()
        df = source.fetch(_SYMBOLS, _START, _END)
        result = DataAlignmentTool.align_to_daily(df, "D")
        pd.testing.assert_frame_equal(result, df)

    def test_data_alignment_event_to_daily(self) -> None:
        source = EarningsCallSource()
        wide_start = date(2024, 1, 2)
        wide_end = date(2024, 12, 31)
        df = source.fetch(_SYMBOLS, wide_start, wide_end)
        result = DataAlignmentTool.align_to_daily(df, "event")
        assert len(result) > len(df)
        symbols_in_result = result.index.get_level_values("symbol").unique().tolist()
        assert set(symbols_in_result) == set(_SYMBOLS)

    def test_data_alignment_requires_multiindex(self) -> None:
        df = pd.DataFrame({"sentiment": [0.1, 0.2]}, index=[0, 1])
        with pytest.raises(ValueError, match="MultiIndex"):
            DataAlignmentTool.align_to_daily(df, "event")

    def test_data_alignment_multiple_sources(self) -> None:
        news = NewsSentimentSource().fetch(_SYMBOLS, _START, _END)
        social = SocialMediaHeatSource().fetch(_SYMBOLS, _START, _END)
        sources = {"news_sentiment": news, "social_media_heat": social}
        result = DataAlignmentTool.align_multiple_sources(sources)
        for col in result.columns:
            assert "_" in col
        assert any(col.startswith("news_sentiment_") for col in result.columns)
        assert any(col.startswith("social_media_heat_") for col in result.columns)

    def test_data_alignment_multiple_sources_single(self) -> None:
        news = NewsSentimentSource().fetch(_SYMBOLS, _START, _END)
        sources = {"news_sentiment": news}
        result = DataAlignmentTool.align_multiple_sources(sources)
        assert len(result.columns) == len(news.columns)
        assert all(col.startswith("news_sentiment_") for col in result.columns)


class TestSignalValidityReport:
    def test_signal_validity_report_fields(self) -> None:
        report = SignalValidityReport(
            source_name="test",
            mean_ic=0.05,
            icir=1.2,
            hit_rate=0.6,
            n_observations=100,
            is_valid=True,
        )
        assert report.source_name == "test"
        assert report.mean_ic == 0.05
        assert report.icir == 1.2
        assert report.hit_rate == 0.6
        assert report.n_observations == 100
        assert report.is_valid is True


class TestSignalValidityChecker:
    @staticmethod
    def _build_signal_and_returns(
        n_symbols: int = 10,
        n_dates: int = 30,
        correlation: float = 0.8,
        seed: int = 42,
    ) -> tuple[pd.DataFrame, pd.DataFrame]:
        rng = np.random.default_rng(seed)
        dates = pd.bdate_range("2024-01-02", periods=n_dates)
        symbols = [f"S{i}" for i in range(n_symbols)]
        index = pd.MultiIndex.from_product(
            [symbols, dates], names=["symbol", "date"]
        )
        raw_signal = rng.standard_normal(len(index))
        noise = rng.standard_normal(len(index))
        signal_vals = correlation * raw_signal + (1 - correlation) * noise
        return_vals = raw_signal * 0.01
        signal_df = pd.DataFrame({"test_signal": signal_vals}, index=index)
        forward_returns = pd.DataFrame({"fwd_ret": return_vals}, index=index)
        return signal_df, forward_returns

    def test_signal_validity_checker_no_overlap(self) -> None:
        checker = SignalValidityChecker()
        signal_df = pd.DataFrame(
            {"test_signal": [0.1, 0.2]},
            index=pd.MultiIndex.from_tuples(
                [("A", date(2024, 1, 2)), ("B", date(2024, 1, 3))],
                names=["symbol", "date"],
            ),
        )
        forward_returns = pd.DataFrame(
            {"fwd_ret": [0.01, 0.02]},
            index=pd.MultiIndex.from_tuples(
                [("C", date(2025, 1, 2)), ("D", date(2025, 1, 3))],
                names=["symbol", "date"],
            ),
        )
        report = checker.validate_signal(signal_df, forward_returns)
        assert report.is_valid is False
        assert report.n_observations == 0

    def test_signal_validity_checker_insufficient_data(self) -> None:
        checker = SignalValidityChecker()
        signal_df = pd.DataFrame(
            {"test_signal": [0.1, 0.2, 0.3]},
            index=pd.MultiIndex.from_tuples(
                [
                    ("A", date(2024, 1, 2)),
                    ("B", date(2024, 1, 2)),
                    ("A", date(2024, 1, 3)),
                ],
                names=["symbol", "date"],
            ),
        )
        forward_returns = pd.DataFrame(
            {"fwd_ret": [0.01, 0.02, 0.03]},
            index=pd.MultiIndex.from_tuples(
                [
                    ("A", date(2024, 1, 2)),
                    ("B", date(2024, 1, 2)),
                    ("A", date(2024, 1, 3)),
                ],
                names=["symbol", "date"],
            ),
        )
        report = checker.validate_signal(signal_df, forward_returns)
        assert report.is_valid is False
        assert report.n_observations == 0

    def test_signal_validity_checker_valid_signal(self) -> None:
        checker = SignalValidityChecker()
        signal_df, forward_returns = self._build_signal_and_returns(
            n_symbols=20, n_dates=60, correlation=0.9
        )
        report = checker.validate_signal(signal_df, forward_returns)
        assert report.is_valid is True
        assert report.n_observations > 0

    def test_signal_validity_checker_weak_signal(self) -> None:
        checker = SignalValidityChecker()
        signal_df, forward_returns = self._build_signal_and_returns(
            n_symbols=20, n_dates=60, correlation=0.01
        )
        report = checker.validate_signal(signal_df, forward_returns)
        assert report.is_valid is False


class TestAlternativeDataManager:
    def test_alternative_data_manager_register_source(self) -> None:
        manager = AlternativeDataManager()
        source = NewsSentimentSource()
        manager.register_source(source)
        result = manager.fetch_all(_SYMBOLS, _START, _END)
        assert "news_sentiment" in result

    def test_alternative_data_manager_fetch_all(self) -> None:
        manager = AlternativeDataManager()
        manager.register_source(NewsSentimentSource())
        manager.register_source(SocialMediaHeatSource())
        result = manager.fetch_all(_SYMBOLS, _START, _END)
        assert isinstance(result, dict)
        assert "news_sentiment" in result
        assert "social_media_heat" in result
        for df in result.values():
            assert isinstance(df, pd.DataFrame)

    def test_alternative_data_manager_fetch_all_empty(self) -> None:
        manager = AlternativeDataManager()
        result = manager.fetch_all(_SYMBOLS, _START, _END)
        assert result == {}

    def test_alternative_data_manager_get_combined_signals(self) -> None:
        manager = AlternativeDataManager()
        manager.register_source(NewsSentimentSource())
        manager.register_source(SocialMediaHeatSource())
        combined = manager.get_combined_signals(_SYMBOLS, _START, _END)
        assert isinstance(combined, pd.DataFrame)
        assert not combined.empty
        assert any(col.startswith("news_sentiment_") for col in combined.columns)
        assert any(col.startswith("social_media_heat_") for col in combined.columns)

    def test_alternative_data_manager_get_combined_signals_no_sources(self) -> None:
        manager = AlternativeDataManager()
        combined = manager.get_combined_signals(_SYMBOLS, _START, _END)
        assert isinstance(combined, pd.DataFrame)
        assert combined.empty

    def test_alternative_data_manager_validate_all(self) -> None:
        manager = AlternativeDataManager()
        manager.register_source(NewsSentimentSource())
        manager.get_combined_signals(_SYMBOLS, _START, _END)
        rng = np.random.default_rng(42)
        cached = manager._cached_data
        all_index = cached["news_sentiment"].index
        forward_returns = pd.DataFrame(
            {"fwd_ret": rng.standard_normal(len(all_index)) * 0.01},
            index=all_index,
        )
        reports = manager.validate_all(forward_returns)
        assert isinstance(reports, dict)
        for report in reports.values():
            assert isinstance(report, SignalValidityReport)
