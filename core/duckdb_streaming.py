__all__ = ["StreamingConfig", "DuckDBStreamingPipeline"]

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class StreamingConfig:
    max_buffer_size: int = 10000
    flush_interval_seconds: float = 5.0
    enable_compression: bool = False


class DuckDBStreamingPipeline:
    def __init__(
        self,
        table_name: str = "realtime_data",
        config: StreamingConfig | None = None,
    ):
        self._table_name = table_name
        self._config = config or StreamingConfig()
        self._buffer: list[dict] = []
        self._last_flush_time: float | None = None
        self._duckdb_available = False
        try:
            import duckdb
            self._con = duckdb.connect(database=":memory:")
            self._duckdb_available = True
            self._init_table()
        except ImportError:
            logger.warning("DuckDB not available, streaming pipeline will use pandas fallback")
        except Exception as e:
            logger.warning("Failed to initialize DuckDB streaming: %s", e)

    def _init_table(self) -> None:
        if not self._duckdb_available:
            return
        try:
            self._con.execute(f"""
                CREATE TABLE IF NOT EXISTS {self._table_name} (
                    symbol VARCHAR,
                    timestamp TIMESTAMP,
                    open DOUBLE,
                    high DOUBLE,
                    low DOUBLE,
                    close DOUBLE,
                    volume DOUBLE,
                    received_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            self._con.execute(f"CREATE SEQUENCE IF NOT EXISTS {self._table_name}_id_seq")
        except Exception as e:
            logger.warning("Failed to initialize streaming table: %s", e)

    def ingest(self, data: dict | list[dict]) -> int:
        if isinstance(data, dict):
            data = [data]
        self._buffer.extend(data)
        if len(self._buffer) >= self._config.max_buffer_size:
            return self.flush()
        return 0

    def ingest_dataframe(self, df: pd.DataFrame) -> int:
        if self._duckdb_available:
            return self._ingest_duckdb(df)
        return self._ingest_pandas(df)

    def _ingest_duckdb(self, df: pd.DataFrame) -> int:
        try:
            if df is None or len(df) == 0:
                return 0
            rel = self._con.from_df(df)
            rel.insert_into(self._table_name)
            return len(df)
        except Exception as e:
            logger.warning("DuckDB streaming ingest failed: %s, falling back to pandas", e)
            return self._ingest_pandas(df)

    def _ingest_pandas(self, df: pd.DataFrame) -> int:
        if df is None or len(df) == 0:
            return 0
        count = len(df)
        self._buffer.extend(df.to_dict("records"))
        if len(self._buffer) >= self._config.max_buffer_size:
            self._flush_buffer()
        return count

    def flush(self) -> int:
        if not self._duckdb_available:
            return self._flush_buffer()
        if not self._buffer:
            return 0
        try:
            df = pd.DataFrame(self._buffer)
            count = self._ingest_duckdb(df)
            self._buffer = []
            self._last_flush_time = datetime.now().timestamp()
            return count
        except Exception as e:
            logger.warning("DuckDB streaming flush failed: %s", e)
            return 0

    def _flush_buffer(self) -> int:
        count = len(self._buffer)
        self._buffer = []
        self._last_flush_time = datetime.now().timestamp()
        return count

    def query_stream(self, sql: str, params: list | None = None) -> pd.DataFrame | None:
        if not self._duckdb_available:
            logger.warning("DuckDB not available for streaming query")
            return None
        try:
            result = self._con.execute(sql, params or []).fetchdf()
            return result
        except Exception as e:
            logger.warning("Streaming query failed: %s", e)
            return None

    def get_aggregates(self, symbol: str | None = None) -> dict[str, Any]:
        if not self._duckdb_available:
            return {"error": "DuckDB not available"}
        try:
            where_clause = f"WHERE symbol = '{symbol}'" if symbol else ""
            result = self._con.execute(f"""
                SELECT
                    COUNT(*) as total_bars,
                    AVG(close) as avg_close,
                    MIN(close) as min_close,
                    MAX(close) as max_close,
                    AVG(volume) as avg_volume
                FROM {self._table_name}
                {where_clause}
            """).fetchone()
            if result:
                return {
                    "total_bars": result[0],
                    "avg_close": round(result[1], 2) if result[1] else 0,
                    "min_close": round(result[2], 2) if result[2] else 0,
                    "max_close": round(result[3], 2) if result[3] else 0,
                    "avg_volume": round(result[4], 2) if result[4] else 0,
                }
        except Exception as e:
            logger.warning("Aggregate query failed: %s", e)
        return {"error": "Query failed"}

    def get_buffer_size(self) -> int:
        return len(self._buffer)

    def is_duckdb_available(self) -> bool:
        return self._duckdb_available

    def close(self) -> None:
        if self._duckdb_available:
            self._con.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
