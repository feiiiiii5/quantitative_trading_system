"""
QuantCore 数据治理模块
提供数据质量检测、复权处理、时点数据库、停牌处理、指数成分快照和数据血缘追踪
"""
from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any

import numpy as np
import pandas as pd

from core.database import SQLiteStore, get_db

logger = logging.getLogger(__name__)

__all__ = [
    "AnomalyRecord",
    "AnomalyType",
    "Severity",
    "AnomalyDetector",
    "AdjustMode",
    "AdjustmentFactorService",
    "PointInTimeDatabase",
    "SuspensionHandler",
    "IndexConstituentSnapshot",
    "DataLineageTracker",
    "DataQualityPipeline",
]


class AnomalyType(Enum):
    Z_SCORE = "z_score"
    EXCHANGE_LIMIT = "exchange_limit"
    VOLUME_SPIKE = "volume_spike"


class Severity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AdjustMode(Enum):
    NONE = ""
    QFQ = "qfq"
    HFQ = "hfq"


@dataclass(frozen=True)
class AnomalyRecord:
    symbol: str
    date: str
    anomaly_type: str
    severity: str
    details: str


@dataclass(frozen=True)
class LineageRecord:
    symbol: str
    date: str
    source: str
    version: str
    ingest_time: str


class AnomalyDetector:
    def __init__(
        self,
        db: SQLiteStore | None = None,
        z_score_threshold: float = 3.0,
        volume_spike_ratio: float = 1000.0,
    ):
        self._db = db or get_db()
        self._z_score_threshold = z_score_threshold
        self._volume_spike_ratio = volume_spike_ratio

    _BOARD_LIMITS: dict[str, float] = {
        "main": 0.10,
        "gem": 0.20,
        "star": 0.20,
        "bse": 0.30,
    }

    def _infer_board(self, symbol: str) -> str:
        if symbol.startswith(("688",)):
            return "star"
        if symbol.startswith(("300", "301")):
            return "gem"
        if symbol.startswith(("8",)):
            return "bse"
        return "main"

    def detect_z_score(
        self,
        df: pd.DataFrame,
        symbol: str,
        column: str = "close",
    ) -> list[AnomalyRecord]:
        if df.empty or column not in df.columns or "date" not in df.columns:
            return []

        prices = pd.to_numeric(df[column], errors="coerce").dropna()
        if len(prices) < 2:
            return []

        returns = prices.pct_change().dropna()
        if returns.std() == 0:
            return []

        z_scores = (returns - returns.mean()) / returns.std()
        dates = df["date"].iloc[1:].reset_index(drop=True)

        results: list[AnomalyRecord] = []
        for idx, (z_val, ret) in enumerate(zip(z_scores, returns, strict=False)):
            if abs(z_val) >= self._z_score_threshold:
                severity = (
                    Severity.CRITICAL.value
                    if abs(z_val) >= 5.0
                    else Severity.HIGH.value
                    if abs(z_val) >= 4.0
                    else Severity.MEDIUM.value
                )
                date_str = str(dates.iloc[idx]) if idx < len(dates) else ""
                results.append(
                    AnomalyRecord(
                        symbol=symbol,
                        date=date_str,
                        anomaly_type=AnomalyType.Z_SCORE.value,
                        severity=severity,
                        details=f"z={z_val:.2f}, return={ret:.4f}",
                    )
                )
        return results

    def detect_exchange_limit(
        self,
        df: pd.DataFrame,
        symbol: str,
    ) -> list[AnomalyRecord]:
        if df.empty or "close" not in df.columns or "date" not in df.columns:
            return []

        prices = pd.to_numeric(df["close"], errors="coerce").dropna()
        if len(prices) < 2:
            return []

        board = self._infer_board(symbol)
        limit_pct = self._BOARD_LIMITS.get(board, 0.10)
        returns = prices.pct_change().dropna()
        dates = df["date"].iloc[1:].reset_index(drop=True)

        results: list[AnomalyRecord] = []
        for idx, ret in enumerate(returns):
            if abs(ret) > limit_pct * 1.01:
                severity = (
                    Severity.CRITICAL.value
                    if abs(ret) > limit_pct * 1.5
                    else Severity.HIGH.value
                )
                date_str = str(dates.iloc[idx]) if idx < len(dates) else ""
                results.append(
                    AnomalyRecord(
                        symbol=symbol,
                        date=date_str,
                        anomaly_type=AnomalyType.EXCHANGE_LIMIT.value,
                        severity=severity,
                        details=(
                            f"change={ret:.4f}, board={board}, "
                            f"limit={limit_pct:.0%}"
                        ),
                    )
                )
        return results

    def detect_volume_spike(
        self,
        df: pd.DataFrame,
        symbol: str,
    ) -> list[AnomalyRecord]:
        if df.empty or "volume" not in df.columns or "date" not in df.columns:
            return []

        volumes = pd.to_numeric(df["volume"], errors="coerce").fillna(0)
        if len(volumes) < 2:
            return []

        median_vol = volumes.iloc[:-1].median()
        if median_vol <= 0:
            return []

        results: list[AnomalyRecord] = []
        for idx in range(1, len(volumes)):
            ratio = volumes.iloc[idx] / median_vol
            if ratio >= self._volume_spike_ratio:
                severity = (
                    Severity.CRITICAL.value
                    if ratio >= self._volume_spike_ratio * 10
                    else Severity.HIGH.value
                )
                date_str = str(df["date"].iloc[idx])
                results.append(
                    AnomalyRecord(
                        symbol=symbol,
                        date=date_str,
                        anomaly_type=AnomalyType.VOLUME_SPIKE.value,
                        severity=severity,
                        details=f"ratio={ratio:.0f}x, vol={volumes.iloc[idx]:.0f}, median={median_vol:.0f}",
                    )
                )
        return results

    def detect_all(
        self,
        df: pd.DataFrame,
        symbol: str,
    ) -> list[AnomalyRecord]:
        results: list[AnomalyRecord] = []
        results.extend(self.detect_z_score(df, symbol))
        results.extend(self.detect_exchange_limit(df, symbol))
        results.extend(self.detect_volume_spike(df, symbol))
        return results

    def save_anomalies(self, records: list[AnomalyRecord]) -> int:
        if not records:
            return 0

        now_str = time.strftime("%Y-%m-%d %H:%M:%S")
        for rec in records:
            self._db.buffered_write(
                """INSERT OR REPLACE INTO price_anomaly
                (symbol, date, anomaly_type, severity, details_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?)""",
                (rec.symbol, rec.date, rec.anomaly_type, rec.severity, rec.details, now_str),
            )
        return len(records)

    def load_anomalies(
        self,
        symbol: str,
        start_date: str = "",
        end_date: str = "",
    ) -> list[AnomalyRecord]:
        sql = "SELECT symbol, date, anomaly_type, severity, details_json FROM price_anomaly WHERE symbol=?"
        params: list[Any] = [symbol]
        if start_date:
            sql += " AND date>=?"
            params.append(start_date)
        if end_date:
            sql += " AND date<=?"
            params.append(end_date)
        sql += " ORDER BY date ASC"

        rows = self._db.fetchall(sql, tuple(params))
        return [
            AnomalyRecord(
                symbol=r["symbol"],
                date=r["date"],
                anomaly_type=r["anomaly_type"],
                severity=r["severity"],
                details=r.get("details_json", ""),
            )
            for r in rows
        ]


class AdjustmentFactorService:
    def __init__(self, db: SQLiteStore | None = None):
        self._db = db or get_db()
        self._mode = AdjustMode.NONE
        self._factor_cache: dict[str, pd.DataFrame] = {}
        self._cache_lock = threading.Lock()

    @property
    def mode(self) -> AdjustMode:
        return self._mode

    def set_mode(self, mode: AdjustMode) -> None:
        if mode == self._mode:
            return
        with self._cache_lock:
            self._mode = mode
            self._factor_cache.clear()
        logger.info("Adjust mode switched to %s", mode)

    def compute_adj_factors(
        self,
        symbol: str,
        market: str,
        kline_type: str = "101",
    ) -> pd.DataFrame:
        cache_key = f"{symbol}_{market}_{kline_type}"
        with self._cache_lock:
            if cache_key in self._factor_cache:
                return self._factor_cache[cache_key]

        df = self._db.load_kline_rows(symbol, market, kline_type, adjust="")
        if df.empty:
            return pd.DataFrame()

        df = df.sort_values("date").reset_index(drop=True)
        df["adj_factor"] = 1.0

        if "volume" not in df.columns or "close" not in df.columns:
            with self._cache_lock:
                self._factor_cache[cache_key] = df[["date", "adj_factor"]]
            return df[["date", "adj_factor"]]

        adj_col = df.columns.get_loc("adj_factor")
        closes = df["close"].values
        volumes = df["volume"].values
        adj_factors = np.ones(len(df))
        cumulative = 1.0
        for i in range(1, len(df)):
            prev_close = closes[i - 1]
            curr_close = closes[i]
            prev_vol = volumes[i - 1]
            curr_vol = volumes[i]

            if (
                prev_close > 0
                and curr_close > 0
                and prev_vol > 0
                and curr_vol == 0
                and abs(curr_close / prev_close - 1.0) > 0.15
            ):
                cumulative *= prev_close / curr_close

            adj_factors[i] = cumulative
        df.iloc[:, adj_col] = adj_factors

        result = df[["date", "adj_factor"]].copy()
        with self._cache_lock:
            self._factor_cache[cache_key] = result
        return result

    def incremental_update(
        self,
        symbol: str,
        market: str,
        kline_type: str = "101",
    ) -> pd.DataFrame:
        cache_key = f"{symbol}_{market}_{kline_type}"
        with self._cache_lock:
            cached = self._factor_cache.get(cache_key)

        df = self._db.load_kline_rows(symbol, market, kline_type, adjust="")
        if df.empty:
            return pd.DataFrame()

        df = df.sort_values("date").reset_index(drop=True)

        if cached is not None and not cached.empty:
            last_cached_date = cached["date"].max()
            mask = df["date"] > last_cached_date
            new_rows = df.loc[mask]
            if new_rows.empty:
                return cached

            last_factor_row = cached.loc[cached["date"] == last_cached_date, "adj_factor"]
            base_factor = float(last_factor_row.iloc[0]) if not last_factor_row.empty else 1.0

            new_factors: list[dict] = []
            cumulative = base_factor
            sorted_new = new_rows.sort_values("date").reset_index(drop=True)
            closes = df["close"].values
            volumes = df["volume"].values

            for i in range(len(sorted_new)):
                row_idx = sorted_new.index[i]
                if row_idx > 0:
                    prev_close = closes[row_idx - 1]
                    curr_close = closes[row_idx]
                    prev_vol = volumes[row_idx - 1]
                    curr_vol = volumes[row_idx]

                    if (
                        prev_close > 0
                        and curr_close > 0
                        and prev_vol > 0
                        and curr_vol == 0
                        and abs(curr_close / prev_close - 1.0) > 0.15
                    ):
                        cumulative *= prev_close / curr_close

                new_factors.append({
                    "date": str(sorted_new.iloc[i]["date"]),
                    "adj_factor": cumulative,
                })

            new_factors_df = pd.DataFrame(new_factors)
            result = pd.concat([cached, new_factors_df], ignore_index=True)
        else:
            result = self.compute_adj_factors(symbol, market, kline_type)

        with self._cache_lock:
            self._factor_cache[cache_key] = result
        return result

    def apply_adjust(
        self,
        symbol: str,
        market: str,
        kline_type: str = "101",
        mode: AdjustMode | None = None,
    ) -> pd.DataFrame:
        effective_mode = mode or self._mode
        if effective_mode == AdjustMode.NONE:
            return self._db.load_kline_rows(symbol, market, kline_type, adjust="")

        df = self._db.load_kline_rows(symbol, market, kline_type, adjust="")
        if df.empty:
            return df

        factors = self.compute_adj_factors(symbol, market, kline_type)
        if factors.empty:
            return df

        df = df.sort_values("date").reset_index(drop=True)
        merged = df.merge(factors, on="date", how="left")
        merged["adj_factor"] = merged["adj_factor"].fillna(1.0)

        price_cols = ["open", "high", "low", "close"]
        if effective_mode == AdjustMode.QFQ:
            latest_factor = float(merged["adj_factor"].iloc[-1]) if not merged.empty else 1.0
            if latest_factor == 0:
                latest_factor = 1.0
            for col in price_cols:
                if col in merged.columns:
                    merged[col] = merged[col] * merged["adj_factor"] / latest_factor
            if "volume" in merged.columns:
                merged["volume"] = merged["volume"] * latest_factor / merged["adj_factor"]
        elif effective_mode == AdjustMode.HFQ:
            for col in price_cols:
                if col in merged.columns:
                    merged[col] = merged[col] * merged["adj_factor"]
            if "volume" in merged.columns:
                merged["volume"] = merged["volume"] / merged["adj_factor"]

        merged = merged.drop(columns=["adj_factor"])
        return merged

    def persist_adj_factors(
        self,
        symbol: str,
        market: str,
        kline_type: str = "101",
    ) -> int:
        factors = self.compute_adj_factors(symbol, market, kline_type)
        if factors.empty:
            return 0

        count = 0
        for row in factors.to_dict("records"):
            self._db.buffered_write(
                """UPDATE kline SET adj_factor=? WHERE symbol=? AND market=? AND kline_type=? AND adjust='' AND date=?""",
                (float(row["adj_factor"]), symbol, market, kline_type, str(row["date"])),
            )
            count += 1
        return count


class PointInTimeDatabase:
    def __init__(self, db: SQLiteStore | None = None):
        self._db = db or get_db()

    def insert_financial_pit(
        self,
        symbol: str,
        report_period: str,
        publish_date: str,
        metric: str,
        value: float,
    ) -> None:
        self._db.buffered_write(
            """INSERT OR REPLACE INTO financial_pit
            (symbol, report_period, publish_date, metric, value)
            VALUES (?, ?, ?, ?, ?)""",
            (symbol, report_period, publish_date, metric, value),
        )

    def insert_financial_pit_batch(
        self,
        records: list[tuple[str, str, str, str, float]],
    ) -> int:
        if not records:
            return 0
        sql = """INSERT OR REPLACE INTO financial_pit
                 (symbol, report_period, publish_date, metric, value)
                 VALUES (?, ?, ?, ?, ?)"""
        self._db.executemany(sql, records)
        return len(records)

    def query_financial_pit(
        self,
        symbol: str,
        metric: str,
        as_of_date: str,
    ) -> list[dict]:
        sql = (
            "SELECT symbol, report_period, publish_date, metric, value "
            "FROM financial_pit "
            "WHERE symbol=? AND metric=? AND publish_date<=? "
            "ORDER BY publish_date DESC, report_period DESC"
        )
        return self._db.fetchall(sql, (symbol, metric, as_of_date))

    def query_latest_financial_pit(
        self,
        symbol: str,
        metric: str,
        as_of_date: str,
    ) -> dict | None:
        results = self.query_financial_pit(symbol, metric, as_of_date)
        return results[0] if results else None

    def query_multiple_metrics(
        self,
        symbol: str,
        metrics: list[str],
        as_of_date: str,
    ) -> dict[str, dict | None]:
        return {
            metric: self.query_latest_financial_pit(symbol, metric, as_of_date)
            for metric in metrics
        }

    def get_available_dates(
        self,
        symbol: str,
        metric: str,
    ) -> list[str]:
        sql = (
            "SELECT DISTINCT publish_date FROM financial_pit "
            "WHERE symbol=? AND metric=? ORDER BY publish_date ASC"
        )
        rows = self._db.fetchall(sql, (symbol, metric))
        return [r["publish_date"] for r in rows]


class SuspensionHandler:
    def __init__(self, db: SQLiteStore | None = None):
        self._db = db or get_db()

    def detect_suspensions(
        self,
        df: pd.DataFrame,
        symbol: str,
    ) -> pd.DataFrame:
        if df.empty or "volume" not in df.columns or "date" not in df.columns:
            return pd.DataFrame(columns=["symbol", "date", "is_suspended"])

        df = df.sort_values("date").reset_index(drop=True)
        volumes = pd.to_numeric(df["volume"], errors="coerce").fillna(0)
        closes = pd.to_numeric(df["close"], errors="coerce").fillna(0) if "close" in df.columns else pd.Series(0, index=df.index)

        has_prior_position = False
        suspended: list[dict] = []

        for i, (vol, close) in enumerate(zip(volumes, closes, strict=False)):
            is_zero_vol = vol <= 0
            if is_zero_vol and has_prior_position:
                suspended.append({
                    "symbol": symbol,
                    "date": str(df["date"].iloc[i]),
                    "is_suspended": True,
                })
            elif not is_zero_vol and close > 0:
                has_prior_position = True

        return pd.DataFrame(suspended) if suspended else pd.DataFrame(columns=["symbol", "date", "is_suspended"])

    def forward_fill_suspension(
        self,
        df: pd.DataFrame,
        position_cols: list[str] | None = None,
    ) -> pd.DataFrame:
        if df.empty:
            return df

        df = df.sort_values("date").reset_index(drop=True)
        if "volume" not in df.columns:
            return df

        volumes = pd.to_numeric(df["volume"], errors="coerce").fillna(0)
        default_fill_cols = ["close", "high", "low", "open"]
        fill_cols = position_cols or default_fill_cols

        last_valid: dict[str, Any] = {}
        for i, vol in enumerate(volumes):
            if vol > 0:
                for col in fill_cols:
                    if col in df.columns:
                        val = df.iloc[i][col]
                        if pd.notna(val):
                            last_valid[col] = val
            else:
                for col, val in last_valid.items():
                    if col in df.columns:
                        df.iloc[i, df.columns.get_loc(col)] = val

        return df

    def calculate_returns_with_suspension(
        self,
        df: pd.DataFrame,
    ) -> pd.DataFrame:
        if df.empty or "close" not in df.columns or "date" not in df.columns:
            return df

        df = df.sort_values("date").reset_index(drop=True)
        closes = pd.to_numeric(df["close"], errors="coerce")
        volumes = pd.to_numeric(df["volume"], errors="coerce").fillna(0) if "volume" in df.columns else pd.Series(1.0, index=df.index)

        returns = pd.Series(np.nan, index=df.index)
        for i in range(1, len(df)):
            prev_close = closes.iloc[i - 1]
            curr_close = closes.iloc[i]
            if prev_close > 0 and pd.notna(curr_close) and pd.notna(prev_close):
                if volumes.iloc[i] > 0:
                    returns.iloc[i] = (curr_close / prev_close) - 1.0
                else:
                    returns.iloc[i] = 0.0

        df = df.copy()
        df["return"] = returns
        df["cum_return"] = (1 + df["return"].fillna(0)).cumprod()
        return df


class IndexConstituentSnapshot:
    def __init__(self, db: SQLiteStore | None = None):
        self._db = db or get_db()

    def add_constituent(
        self,
        index_code: str,
        symbol: str,
        in_date: str,
        out_date: str = "",
    ) -> None:
        self._db.buffered_write(
            """INSERT OR REPLACE INTO index_constituent
            (index_code, symbol, in_date, out_date)
            VALUES (?, ?, ?, ?)""",
            (index_code, symbol, in_date, out_date),
        )

    def add_constituents_batch(
        self,
        records: list[tuple[str, str, str, str]],
    ) -> int:
        if not records:
            return 0
        sql = """INSERT OR REPLACE INTO index_constituent
                 (index_code, symbol, in_date, out_date)
                 VALUES (?, ?, ?, ?)"""
        self._db.executemany(sql, records)
        return len(records)

    def remove_constituent(
        self,
        index_code: str,
        symbol: str,
        out_date: str,
    ) -> None:
        self._db.buffered_write(
            """UPDATE index_constituent SET out_date=?
            WHERE index_code=? AND symbol=? AND (out_date IS NULL OR out_date='')""",
            (out_date, index_code, symbol),
        )

    def query_constituents(
        self,
        index_code: str,
        as_of_date: str,
    ) -> list[str]:
        sql = (
            "SELECT symbol FROM index_constituent "
            "WHERE index_code=? AND in_date<=? "
            "AND (out_date IS NULL OR out_date='' OR out_date>?) "
            "ORDER BY symbol"
        )
        rows = self._db.fetchall(sql, (index_code, as_of_date, as_of_date))
        return [r["symbol"] for r in rows]

    def query_constituent_history(
        self,
        index_code: str,
        symbol: str,
    ) -> list[dict]:
        sql = (
            "SELECT index_code, symbol, in_date, out_date "
            "FROM index_constituent "
            "WHERE index_code=? AND symbol=? "
            "ORDER BY in_date ASC"
        )
        return self._db.fetchall(sql, (index_code, symbol))

    def query_all_changes(
        self,
        index_code: str,
        start_date: str = "",
        end_date: str = "",
    ) -> list[dict]:
        sql = "SELECT * FROM index_constituent WHERE index_code=?"
        params: list[Any] = [index_code]
        if start_date:
            sql += " AND in_date>=?"
            params.append(start_date)
        if end_date:
            sql += " AND in_date<=?"
            params.append(end_date)
        sql += " ORDER BY in_date ASC"
        return self._db.fetchall(sql, tuple(params))

    def is_constituent(
        self,
        index_code: str,
        symbol: str,
        as_of_date: str,
    ) -> bool:
        constituents = self.query_constituents(index_code, as_of_date)
        return symbol in constituents


class DataLineageTracker:
    def __init__(self, db: SQLiteStore | None = None):
        self._db = db or get_db()

    def record_lineage(
        self,
        symbol: str,
        date: str,
        source: str,
        version: str,
    ) -> None:
        ingest_time = time.strftime("%Y-%m-%d %H:%M:%S")
        self._db.buffered_write(
            """INSERT OR REPLACE INTO data_lineage
            (symbol, date, source, version, ingest_time)
            VALUES (?, ?, ?, ?, ?)""",
            (symbol, date, source, version, ingest_time),
        )

    def record_lineage_batch(
        self,
        records: list[tuple[str, str, str, str]],
    ) -> int:
        if not records:
            return 0

        ingest_time = time.strftime("%Y-%m-%d %H:%M:%S")
        full_records = [(sym, dt, src, ver, ingest_time) for sym, dt, src, ver in records]
        sql = """INSERT OR REPLACE INTO data_lineage
                 (symbol, date, source, version, ingest_time)
                 VALUES (?, ?, ?, ?, ?)"""
        self._db.executemany(sql, full_records)
        return len(full_records)

    def query_lineage(
        self,
        symbol: str,
        start_date: str = "",
        end_date: str = "",
    ) -> list[LineageRecord]:
        sql = "SELECT symbol, date, source, version, ingest_time FROM data_lineage WHERE symbol=?"
        params: list[Any] = [symbol]
        if start_date:
            sql += " AND date>=?"
            params.append(start_date)
        if end_date:
            sql += " AND date<=?"
            params.append(end_date)
        sql += " ORDER BY date ASC"

        rows = self._db.fetchall(sql, tuple(params))
        return [
            LineageRecord(
                symbol=r["symbol"],
                date=r["date"],
                source=r["source"],
                version=r["version"],
                ingest_time=r["ingest_time"],
            )
            for r in rows
        ]

    def query_lineage_by_source(
        self,
        source: str,
        start_date: str = "",
        end_date: str = "",
    ) -> list[LineageRecord]:
        sql = "SELECT symbol, date, source, version, ingest_time FROM data_lineage WHERE source=?"
        params: list[Any] = [source]
        if start_date:
            sql += " AND date>=?"
            params.append(start_date)
        if end_date:
            sql += " AND date<=?"
            params.append(end_date)
        sql += " ORDER BY date ASC"

        rows = self._db.fetchall(sql, tuple(params))
        return [
            LineageRecord(
                symbol=r["symbol"],
                date=r["date"],
                source=r["source"],
                version=r["version"],
                ingest_time=r["ingest_time"],
            )
            for r in rows
        ]

    def get_latest_version(
        self,
        symbol: str,
        source: str,
    ) -> str | None:
        row = self._db.fetchone(
            "SELECT version FROM data_lineage WHERE symbol=? AND source=? ORDER BY date DESC LIMIT 1",
            (symbol, source),
        )
        return row["version"] if row else None


class DataQualityPipeline:
    """一站式数据质量处理：停牌标记、异常检测、前复权、PIT 财务数据

    回测引擎和信号端点在消费行情数据前应先调用 ``process()`` 清洗，
    确保停牌日收益率归零、除权日价格连续、异常值被标记。
    """

    _A_SHARE_MAIN_LIMIT = 0.115

    def __init__(
        self,
        db: SQLiteStore | None = None,
        enable_anomaly_detect: bool = True,
        enable_suspension: bool = True,
        enable_adjust: bool = True,
    ):
        self._anomaly = AnomalyDetector(db) if enable_anomaly_detect else None
        self._suspension = SuspensionHandler(db) if enable_suspension else None
        self._adjust_svc = AdjustmentFactorService(db) if enable_adjust else None
        self._pit = PointInTimeDatabase(db)
        self._anomaly_records: list[AnomalyRecord] = []

    @property
    def anomaly_records(self) -> list[AnomalyRecord]:
        return list(self._anomaly_records)

    def process(self, df: pd.DataFrame, symbol: str = "") -> pd.DataFrame:
        """对行情 DataFrame 执行全量数据质量处理

        处理步骤:
        1. 停牌日标记 (volume == 0 → is_suspended)
        2. 停牌日前向填充 OHLC（持仓不变）
        3. 异常收益率标记（超涨跌停限制）
        4. 前复权价格计算（adj_close）
        5. 停牌日收益率归零

        Returns:
            处理后的 DataFrame，新增 is_suspended / is_anomaly / adj_close 列
        """
        if df is None or df.empty:
            return df

        df = df.copy()

        if "volume" in df.columns:
            df["is_suspended"] = pd.to_numeric(df["volume"], errors="coerce").fillna(0) <= 0
        else:
            df["is_suspended"] = False

        if self._suspension is not None and "volume" in df.columns and "date" in df.columns:
            df = self._suspension.forward_fill_suspension(df)

        if "close" in df.columns and len(df) > 1:
            pct = pd.to_numeric(df["close"], errors="coerce").pct_change(fill_method=None).abs()
            df["is_anomaly"] = pct > self._A_SHARE_MAIN_LIMIT
        else:
            df["is_anomaly"] = False

        if "adj_factor" in df.columns:
            factors = pd.to_numeric(df["adj_factor"], errors="coerce").fillna(1.0)
            latest = float(factors.iloc[-1]) if len(factors) > 0 else 1.0
            if latest > 1e-9:
                df["adj_close"] = pd.to_numeric(df["close"], errors="coerce") * factors / latest
            else:
                df["adj_close"] = pd.to_numeric(df["close"], errors="coerce")
        else:
            df["adj_close"] = pd.to_numeric(df.get("close", 0), errors="coerce")

        if "close" in df.columns and "is_suspended" in df.columns:
            closes = pd.to_numeric(df["close"], errors="coerce")
            returns = closes.pct_change(fill_method=None)
            suspended_mask = df["is_suspended"].fillna(False)
            returns[suspended_mask] = 0.0
            df["return"] = returns

        if self._anomaly is not None and symbol:
            try:
                records = self._anomaly.detect_exchange_limit(df, symbol)
                if records:
                    self._anomaly_records.extend(records)
                    logger.debug("DataQualityPipeline: %s detected %s anomalies", symbol, len)
            except Exception as e:
                logger.debug("DataQualityPipeline anomaly detection failed for %s: %s", symbol, e)

        return df

    def query_pit_metric(self, symbol: str, metric: str, as_of_date: str) -> float | None:
        """查询 Point-in-Time 财务指标，避免 look-ahead bias"""
        result = self._pit.query_latest_financial_pit(symbol, metric, as_of_date)
        if result is not None:
            return float(result.get("value", 0))
        return None

    def query_pit_metrics(self, symbol: str, metrics: list[str], as_of_date: str) -> dict[str, float | None]:
        """批量查询 Point-in-Time 财务指标"""
        raw = self._pit.query_multiple_metrics(symbol, metrics, as_of_date)
        return {
            metric: float(r["value"]) if r is not None else None
            for metric, r in raw.items()
        }
