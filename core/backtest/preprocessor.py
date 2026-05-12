# MODIFIED: Backtest data preprocessing pipeline | VERSION: 2026-05-11
from __future__ import annotations

import logging
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class PreprocessedData:
    df: pd.DataFrame
    quality_report: dict = field(default_factory=dict)
    is_valid: bool = True
    warnings: list[str] = field(default_factory=list)


class BacktestDataPreprocessor:
    def __init__(
        self,
        min_avg_amount: float = 5_000_000,
        outlier_sigma: float = 5.0,
        min_rows: int = 60,
    ):
        self._min_avg_amount = min_avg_amount
        self._outlier_sigma = outlier_sigma
        self._min_rows = min_rows
        self._report: dict = {}

    def process(self, df: pd.DataFrame, symbol: str = "") -> PreprocessedData:
        warnings: list[str] = []
        if df is None or len(df) < self._min_rows:
            return PreprocessedData(
                df=df if df is not None else pd.DataFrame(),
                quality_report={"error": "insufficient_data"},
                is_valid=False,
                warnings=[f"数据不足: 需要>{self._min_rows}行, 实际{len(df) if df is not None else 0}行"],
            )

        df = df.copy()
        self._report = {"symbol": symbol, "original_rows": len(df)}

        df = self._fill_missing_prices(df)
        df = self._fill_missing_volume(df)
        df, outlier_count = self._detect_and_handle_outliers(df)
        df, suspension_days = self._mark_suspension_days(df)
        df = self._compute_technical_features(df)
        df, is_liquid = self._filter_illiquid(df)

        self._report["missing_pct"] = self._report.get("missing_pct", 0)
        self._report["outlier_count"] = outlier_count
        self._report["suspension_days"] = suspension_days
        self._report["is_liquid"] = is_liquid
        self._report["final_rows"] = len(df)

        if not is_liquid:
            warnings.append(f"流动性不足: 日均成交额<{self._min_avg_amount:,.0f}")

        return PreprocessedData(
            df=df,
            quality_report=self._report,
            is_valid=len(df) >= self._min_rows,
            warnings=warnings,
        )

    def _fill_missing_prices(self, df: pd.DataFrame) -> pd.DataFrame:
        price_cols = [c for c in ("open", "high", "low", "close") if c in df.columns]
        missing_before = sum(df[c].isna().sum() for c in price_cols)
        self._report["missing_pct"] = round(missing_before / max(len(df) * len(price_cols), 1) * 100, 2)
        for col in price_cols:
            df[col] = df[col].ffill()
            df[col] = df[col].bfill(limit=3)
        return df

    def _fill_missing_volume(self, df: pd.DataFrame) -> pd.DataFrame:
        if "volume" not in df.columns:
            return df
        missing_vol = df["volume"].isna().sum()
        if missing_vol > 0:
            rolling_mean = df["volume"].rolling(5, min_periods=1).mean()
            df["volume"] = df["volume"].fillna(rolling_mean)
            df["volume"] = df["volume"].fillna(0)
        return df

    def _detect_and_handle_outliers(self, df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
        outlier_count = 0
        for col in ("open", "high", "low", "close"):
            if col not in df.columns:
                continue
            series = df[col].astype(float)
            if len(series) < 10:
                continue
            mean = series.mean()
            std = series.std()
            if std == 0:
                continue
            lower = mean - self._outlier_sigma * std
            upper = mean + self._outlier_sigma * std
            mask = (series < lower) | (series > upper)
            outlier_count += int(mask.sum())
            df.loc[mask, col] = df[col].clip(lower=lower, upper=upper)
        return df, outlier_count

    def _mark_suspension_days(self, df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
        suspension_days = 0
        if "volume" in df.columns and "close" in df.columns:
            vol_zero = df["volume"].astype(float) == 0
            if "open" in df.columns:
                price_unchanged = df["close"].astype(float) == df["open"].astype(float)
            else:
                price_unchanged = pd.Series(False, index=df.index)
            suspension = vol_zero & price_unchanged
            suspension_days = int(suspension.sum())
            df["is_suspended"] = suspension
        return df, suspension_days

    def _compute_technical_features(self, df: pd.DataFrame) -> pd.DataFrame:
        if "close" not in df.columns:
            return df
        close = df["close"].astype(float)
        if len(close) >= 20:
            df["ma5"] = close.rolling(5).mean().ffill().bfill()
            df["ma10"] = close.rolling(10).mean().ffill().bfill()
            df["ma20"] = close.rolling(20).mean().ffill().bfill()
            delta = close.diff()
            gain = delta.clip(lower=0)
            loss = (-delta).clip(lower=0)
            avg_gain = gain.rolling(14, min_periods=1).mean()
            avg_loss = loss.rolling(14, min_periods=1).mean()
            rs = avg_gain / avg_loss.replace(0, np.inf)
            df["rsi14"] = (100 - (100 / (1 + rs))).clip(0, 100).ffill().bfill()
        if "high" in df.columns and "low" in df.columns:
            high = df["high"].astype(float)
            low = df["low"].astype(float)
            prev_close = close.shift(1).ffill()
            tr = pd.concat([
                high - low,
                (high - prev_close).abs(),
                (low - prev_close).abs(),
            ], axis=1).max(axis=1)
            df["atr14"] = tr.rolling(14, min_periods=1).mean().ffill().bfill()
        return df

    def _filter_illiquid(self, df: pd.DataFrame) -> tuple[pd.DataFrame, bool]:
        if "volume" not in df.columns or "close" not in df.columns:
            return df, True
        avg_amount = (df["close"].astype(float) * df["volume"].astype(float)).mean()
        is_liquid = avg_amount >= self._min_avg_amount
        return df, is_liquid
