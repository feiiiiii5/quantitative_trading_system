from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date

import numpy as np
import pandas as pd
from scipy import stats

logger = logging.getLogger(__name__)


class AlternativeDataSource(ABC):
    @abstractmethod
    def fetch(self, symbols: list[str], start: date, end: date) -> pd.DataFrame:
        ...

    @property
    @abstractmethod
    def frequency(self) -> str:
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        ...


class NewsSentimentSource(AlternativeDataSource):
    @property
    def frequency(self) -> str:
        return "D"

    @property
    def name(self) -> str:
        return "news_sentiment"

    def fetch(self, symbols: list[str], start: date, end: date) -> pd.DataFrame:
        logger.info("Fetching news sentiment for %d symbols from %s to %s", len(symbols), start, end)
        dates = pd.bdate_range(start, end)
        records: list[tuple[str, date, float]] = []
        for symbol in symbols:
            sentiment_series = self._simulate_sentiment(len(dates))
            for dt, val in zip(dates, sentiment_series, strict=False):
                records.append((symbol, dt, val))
        index = pd.MultiIndex.from_tuples(
            [(r[0], r[1]) for r in records], names=["symbol", "date"]
        )
        return pd.DataFrame(
            {"sentiment": [r[2] for r in records]}, index=index
        )

    def _simulate_sentiment(self, n: int, rho: float = 0.85) -> np.ndarray:
        rng = np.random.default_rng()
        result = np.empty(n, dtype=np.float64)
        result[0] = rng.uniform(-0.3, 0.3)
        for i in range(1, n):
            innovation = rng.normal(0, 0.15)
            result[i] = rho * result[i - 1] + innovation
        return np.clip(result, -1.0, 1.0)


class EarningsCallSource(AlternativeDataSource):
    @property
    def frequency(self) -> str:
        return "event"

    @property
    def name(self) -> str:
        return "earnings_call"

    def fetch(self, symbols: list[str], start: date, end: date) -> pd.DataFrame:
        logger.info("Fetching earnings call data for %d symbols from %s to %s", len(symbols), start, end)
        rng = np.random.default_rng()
        records: list[tuple[str, date, float, float, float]] = []
        quarters = self._quarter_dates(start, end)
        for symbol in symbols:
            for q_date in quarters:
                sentiment = rng.uniform(-0.5, 0.5)
                surprise_pct = rng.normal(0, 5)
                guidance = rng.uniform(-0.4, 0.4)
                records.append((symbol, q_date, sentiment, surprise_pct, guidance))
        index = pd.MultiIndex.from_tuples(
            [(r[0], r[1]) for r in records], names=["symbol", "date"]
        )
        return pd.DataFrame(
            {
                "sentiment": [r[2] for r in records],
                "surprise_pct": [r[3] for r in records],
                "guidance_sentiment": [r[4] for r in records],
            },
            index=index,
        )

    def _quarter_dates(self, start: date, end: date) -> list[date]:
        quarter_months = [1, 4, 7, 10]
        results: list[date] = []
        year = start.year
        while year <= end.year:
            for m in quarter_months:
                d = date(year, m, 15)
                if start <= d <= end:
                    results.append(d)
            year += 1
        return results


class SocialMediaHeatSource(AlternativeDataSource):
    @property
    def frequency(self) -> str:
        return "D"

    @property
    def name(self) -> str:
        return "social_media_heat"

    def fetch(self, symbols: list[str], start: date, end: date) -> pd.DataFrame:
        logger.info("Fetching social media heat for %d symbols from %s to %s", len(symbols), start, end)
        rng = np.random.default_rng()
        dates = pd.bdate_range(start, end)
        records: list[tuple[str, date, int, float, float]] = []
        for symbol in symbols:
            for dt in dates:
                mention_count = rng.poisson(50)
                sentiment_score = rng.uniform(-1, 1)
                viral_score = rng.exponential(0.3)
                records.append((symbol, dt, mention_count, sentiment_score, min(viral_score, 1.0)))
        index = pd.MultiIndex.from_tuples(
            [(r[0], r[1]) for r in records], names=["symbol", "date"]
        )
        return pd.DataFrame(
            {
                "mention_count": [r[2] for r in records],
                "sentiment_score": [r[3] for r in records],
                "viral_score": [r[4] for r in records],
            },
            index=index,
        )


class DataAlignmentTool:
    @staticmethod
    def align_to_daily(data: pd.DataFrame, source_freq: str) -> pd.DataFrame:
        if source_freq == "D":
            return data
        if not data.index.names == ["symbol", "date"]:
            raise ValueError("DataFrame must have MultiIndex (symbol, date)")
        symbols = data.index.get_level_values("symbol").unique()
        all_dates = pd.bdate_range(
            data.index.get_level_values("date").min(),
            data.index.get_level_values("date").max(),
        )
        full_index = pd.MultiIndex.from_product(
            [symbols, all_dates], names=["symbol", "date"]
        )
        reindexed = data.reindex(full_index)
        reindexed = reindexed.groupby(level="symbol").ffill()
        return reindexed

    @staticmethod
    def align_multiple_sources(sources: dict[str, pd.DataFrame]) -> pd.DataFrame:
        frames: list[pd.DataFrame] = []
        for source_name, df in sources.items():
            flat = df.copy()
            flat.columns = [f"{source_name}_{col}" for col in flat.columns]
            frames.append(flat)
        merged = frames[0]
        for frame in frames[1:]:
            merged = merged.join(frame, how="outer")
        return merged


@dataclass(frozen=True)
class SignalValidityReport:
    source_name: str
    mean_ic: float
    icir: float
    hit_rate: float
    n_observations: int
    is_valid: bool


class SignalValidityChecker:
    IC_THRESHOLD: float = 0.02
    ICIR_THRESHOLD: float = 0.5
    HIT_RATE_THRESHOLD: float = 0.5

    def validate_signal(
        self,
        signal_df: pd.DataFrame,
        forward_returns: pd.DataFrame,
    ) -> SignalValidityReport:
        common_idx = signal_df.index.intersection(forward_returns.index)
        if len(common_idx) == 0:
            logger.warning("No overlapping indices between signal and forward returns")
            return SignalValidityReport(
                source_name="unknown",
                mean_ic=0.0,
                icir=0.0,
                hit_rate=0.0,
                n_observations=0,
                is_valid=False,
            )
        signal_aligned = signal_df.loc[common_idx]
        returns_aligned = forward_returns.loc[common_idx]
        signal_cols = signal_aligned.select_dtypes(include=[np.number]).columns
        return_col = returns_aligned.select_dtypes(include=[np.number]).columns[0]
        ics: list[float] = []
        hit_counts: list[int] = []
        total_counts: list[int] = []
        dates = signal_aligned.index.get_level_values("date").unique()
        for dt in dates:
            try:
                sig_slice = signal_aligned.xs(dt, level="date")[signal_cols]
                ret_slice = returns_aligned.xs(dt, level="date")[[return_col]]
            except KeyError:
                continue
            merged = sig_slice.join(ret_slice, how="inner").dropna()
            if len(merged) < 5:
                continue
            for col in signal_cols:
                if col not in merged.columns:
                    continue
                ic_val, _ = stats.spearmanr(merged[col], merged[return_col])
                if np.isfinite(ic_val):
                    ics.append(ic_val)
                same_sign = (np.sign(merged[col]) == np.sign(merged[return_col])).sum()
                hit_counts.append(int(same_sign))
                total_counts.append(len(merged))
        if not ics:
            logger.warning("Insufficient data for IC calculation")
            return SignalValidityReport(
                source_name="unknown",
                mean_ic=0.0,
                icir=0.0,
                hit_rate=0.0,
                n_observations=0,
                is_valid=False,
            )
        mean_ic = float(np.mean(ics))
        std_ic = float(np.std(ics, ddof=1)) if len(ics) > 1 else 1.0
        icir = mean_ic / std_ic if std_ic != 0 else 0.0
        total_hits = sum(hit_counts)
        total_obs = sum(total_counts)
        hit_rate = total_hits / total_obs if total_obs > 0 else 0.0
        is_valid = (
            abs(mean_ic) >= self.IC_THRESHOLD
            and abs(icir) >= self.ICIR_THRESHOLD
            and hit_rate >= self.HIT_RATE_THRESHOLD
        )
        source_name = signal_df.columns[0].split("_")[0] if len(signal_df.columns) > 0 else "unknown"
        return SignalValidityReport(
            source_name=source_name,
            mean_ic=mean_ic,
            icir=icir,
            hit_rate=hit_rate,
            n_observations=total_obs,
            is_valid=is_valid,
        )


class AlternativeDataManager:
    def __init__(self) -> None:
        self._sources: dict[str, AlternativeDataSource] = {}
        self._cached_data: dict[str, pd.DataFrame] = {}
        self._alignment_tool = DataAlignmentTool()
        self._validity_checker = SignalValidityChecker()

    def register_source(self, source: AlternativeDataSource) -> None:
        self._sources[source.name] = source
        logger.info("Registered alternative data source: %s (freq=%s)", source.name, source.frequency)

    def fetch_all(
        self, symbols: list[str], start: date, end: date
    ) -> dict[str, pd.DataFrame]:
        results: dict[str, pd.DataFrame] = {}
        for name, source in self._sources.items():
            try:
                raw = source.fetch(symbols, start, end)
                aligned = self._alignment_tool.align_to_daily(raw, source.frequency)
                results[name] = aligned
                logger.info("Fetched and aligned source: %s (%d rows)", name, len(aligned))
            except (ValueError, KeyError, OSError) as e:
                logger.exception("Failed to fetch source: %s (%s)", name, e)
        return results

    def validate_all(
        self, forward_returns: pd.DataFrame
    ) -> dict[str, SignalValidityReport]:
        reports: dict[str, SignalValidityReport] = {}
        for name, df in self._cached_data.items():
            report = self._validity_checker.validate_signal(df, forward_returns)
            reports[name] = report
            logger.info(
                "Validation for %s: IC=%.4f, ICIR=%.4f, hit_rate=%.4f, valid=%s",
                name, report.mean_ic, report.icir, report.hit_rate, report.is_valid,
            )
        return reports

    def get_combined_signals(
        self, symbols: list[str], start: date, end: date
    ) -> pd.DataFrame:
        fetched = self.fetch_all(symbols, start, end)
        self._cached_data = fetched
        if not fetched:
            logger.warning("No alternative data sources registered")
            return pd.DataFrame()
        combined = self._alignment_tool.align_multiple_sources(fetched)
        combined = combined.sort_index()
        combined = combined.dropna(how="all")
        logger.info("Combined signals: %d rows, %d columns", len(combined), len(combined.columns))
        return combined
