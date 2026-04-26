import json
import logging
import sqlite3
import threading
from collections import defaultdict, deque
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
CACHE_DIR = DATA_DIR / "cache"
DB_PATH = DATA_DIR / "market_cache.db"

# Connection pooling for database
_DB_CONNECTION_POOL = {}
_DB_POOL_SIZE = 5


def _now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _json_dumps(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, separators=(",", ":"))


def _get_db_connection(db_path: str):
    """Get a database connection from the pool"""
    import hashlib
    
    key = hashlib.md5(db_path.encode()).hexdigest()
    
    if key in _DB_CONNECTION_POOL and _DB_CONNECTION_POOL[key]:
        return _DB_CONNECTION_POOL[key].pop()
    
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def _return_db_connection(conn):
    """Return a database connection to the pool"""
    import sqlite3
    import hashlib
    
    if not conn or not isinstance(conn, sqlite3.Connection):
        return
    
    try:
        db_path = conn.execute("PRAGMA database_list").fetchone()[2]
        key = hashlib.md5(db_path.encode()).hexdigest()
        
        if key not in _DB_CONNECTION_POOL:
            _DB_CONNECTION_POOL[key] = []
        
        if len(_DB_CONNECTION_POOL[key]) < _DB_POOL_SIZE:
            _DB_CONNECTION_POOL[key].append(conn)
        else:
            conn.close()
    except Exception:
        try:
            conn.close()
        except Exception:
            pass


class SQLiteStore:
    def __init__(self, db_path: Path | str = DB_PATH):
        self.db_path = Path(db_path)
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        self._write_lock = threading.Lock()
        self._source_windows: dict[tuple[str, str], deque] = defaultdict(lambda: deque(maxlen=100))
        self._init_db()

    def _init_db(self) -> None:
        conn = None
        try:
            conn = _get_db_connection(str(self.db_path))
            with self._write_lock:
                conn.execute("PRAGMA journal_mode=WAL")
                conn.execute("PRAGMA synchronous=NORMAL")
                conn.execute("PRAGMA temp_store=MEMORY")
                conn.execute("PRAGMA foreign_keys=ON")
                conn.executescript(
                    """
                    CREATE TABLE IF NOT EXISTS kline_cache (
                        symbol TEXT NOT NULL,
                        market TEXT NOT NULL,
                        kline_type TEXT NOT NULL,
                        adjust TEXT NOT NULL DEFAULT 'qfq',
                        instrument_type TEXT NOT NULL DEFAULT 'stock',
                        date TEXT NOT NULL,
                        open REAL,
                        high REAL,
                        low REAL,
                        close REAL,
                        volume REAL,
                        amount REAL DEFAULT 0,
                        adjusted_factor REAL DEFAULT 1,
                        is_dirty INTEGER DEFAULT 0,
                        source TEXT DEFAULT '',
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                        updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                        PRIMARY KEY (symbol, market, kline_type, adjust, date)
                    );
                    CREATE INDEX IF NOT EXISTS idx_kline_symbol_type_date
                        ON kline_cache(symbol, market, kline_type, adjust, date);

                    CREATE TABLE IF NOT EXISTS financial_data (
                        symbol TEXT NOT NULL,
                        report_date TEXT NOT NULL,
                        revenue REAL DEFAULT 0,
                        net_profit REAL DEFAULT 0,
                        gross_margin REAL DEFAULT 0,
                        net_margin REAL DEFAULT 0,
                        roe REAL DEFAULT 0,
                        roa REAL DEFAULT 0,
                        debt_ratio REAL DEFAULT 0,
                        payload TEXT DEFAULT '{}',
                        updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                        PRIMARY KEY (symbol, report_date)
                    );

                    CREATE TABLE IF NOT EXISTS stock_info (
                        symbol TEXT NOT NULL,
                        market TEXT NOT NULL,
                        name TEXT NOT NULL,
                        instrument_type TEXT NOT NULL DEFAULT 'stock',
                        industry TEXT DEFAULT '',
                        concepts TEXT DEFAULT '',
                        market_value REAL DEFAULT 0,
                        float_market_value REAL DEFAULT 0,
                        list_date TEXT DEFAULT '',
                        pe_ttm REAL DEFAULT 0,
                        pb REAL DEFAULT 0,
                        extra_json TEXT DEFAULT '{}',
                        updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                        PRIMARY KEY (symbol, market)
                    );
                    CREATE INDEX IF NOT EXISTS idx_stock_info_name
                        ON stock_info(name);
                    CREATE INDEX IF NOT EXISTS idx_stock_info_industry
                        ON stock_info(industry);
                    CREATE INDEX IF NOT EXISTS idx_stock_info_type
                        ON stock_info(instrument_type);

                    CREATE TABLE IF NOT EXISTS data_source_stats (
                        source_name TEXT NOT NULL,
                        request_type TEXT NOT NULL,
                        success_rate REAL DEFAULT 0,
                        avg_response_ms REAL DEFAULT 0,
                        total_requests INTEGER DEFAULT 0,
                        success_requests INTEGER DEFAULT 0,
                        failure_requests INTEGER DEFAULT 0,
                        priority INTEGER DEFAULT 100,
                        last_error TEXT DEFAULT '',
                        recent_requests_json TEXT DEFAULT '[]',
                        updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                        PRIMARY KEY (source_name, request_type)
                    );

                    CREATE TABLE IF NOT EXISTS zt_pool (
                        trade_date TEXT NOT NULL,
                        pool_type TEXT NOT NULL,
                        symbol TEXT NOT NULL,
                        name TEXT DEFAULT '',
                        order_amount REAL DEFAULT 0,
                        reason TEXT DEFAULT '',
                        seal_time TEXT DEFAULT '',
                        payload TEXT DEFAULT '{}',
                        updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                        PRIMARY KEY (trade_date, pool_type, symbol)
                    );

                    CREATE TABLE IF NOT EXISTS northbound_flow (
                        trade_date TEXT PRIMARY KEY,
                        sh_connect REAL DEFAULT 0,
                        sz_connect REAL DEFAULT 0,
                        total_flow REAL DEFAULT 0,
                        net_buy REAL DEFAULT 0,
                        top_stocks_json TEXT DEFAULT '[]',
                        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                    );

                    CREATE TABLE IF NOT EXISTS market_sentiment (
                        trade_date TEXT PRIMARY KEY,
                        advancers INTEGER DEFAULT 0,
                        decliners INTEGER DEFAULT 0,
                        up_down_ratio REAL DEFAULT 0,
                        turnover_amount REAL DEFAULT 0,
                        margin_balance_change REAL DEFAULT 0,
                        new_high_low_ratio REAL DEFAULT 0,
                        mcclellan REAL DEFAULT 0,
                        ad_line REAL DEFAULT 0,
                        new_high_low_index REAL DEFAULT 0,
                        payload TEXT DEFAULT '{}',
                        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                    );

                    CREATE TABLE IF NOT EXISTS config (
                        config_key TEXT PRIMARY KEY,
                        config_value TEXT NOT NULL,
                        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                    );

                    CREATE TABLE IF NOT EXISTS api_metrics (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        endpoint TEXT NOT NULL,
                        latency_ms REAL DEFAULT 0,
                        status_code INTEGER DEFAULT 200,
                        cache_hit INTEGER DEFAULT 0,
                        source TEXT DEFAULT '',
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP
                    );
                    CREATE INDEX IF NOT EXISTS idx_api_metrics_endpoint_time
                        ON api_metrics(endpoint, created_at);

                    CREATE TABLE IF NOT EXISTS system_metrics (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        metric_name TEXT NOT NULL,
                        metric_value REAL DEFAULT 0,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP
                    );

                    CREATE TABLE IF NOT EXISTS usage_events (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        event_type TEXT NOT NULL,
                        symbol TEXT DEFAULT '',
                        strategy TEXT DEFAULT '',
                        duration_ms REAL DEFAULT 0,
                        payload TEXT DEFAULT '{}',
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP
                    );

                    CREATE TABLE IF NOT EXISTS trade_log (
                        id TEXT PRIMARY KEY,
                        trade_time TEXT NOT NULL,
                        symbol TEXT NOT NULL,
                        name TEXT DEFAULT '',
                        direction TEXT NOT NULL,
                        quantity INTEGER DEFAULT 0,
                        price REAL DEFAULT 0,
                        fee REAL DEFAULT 0,
                        slippage_cost REAL DEFAULT 0,
                        strategy_name TEXT DEFAULT '',
                        signal_values TEXT DEFAULT '{}',
                        cost_basis REAL DEFAULT 0,
                        pnl_amount REAL DEFAULT 0,
                        pnl_pct REAL DEFAULT 0,
                        note TEXT DEFAULT ''
                    );

                    CREATE TABLE IF NOT EXISTS instrument_snapshots (
                        trade_date TEXT NOT NULL,
                        symbol TEXT NOT NULL,
                        market TEXT NOT NULL,
                        instrument_type TEXT NOT NULL,
                        payload TEXT DEFAULT '{}',
                        updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                        PRIMARY KEY (trade_date, symbol, market, instrument_type)
                    );

                    CREATE TABLE IF NOT EXISTS account_snapshots (
                        snapshot_time TEXT PRIMARY KEY,
                        total_assets REAL DEFAULT 0,
                        cash REAL DEFAULT 0,
                        market_value REAL DEFAULT 0,
                        benchmark TEXT DEFAULT '000300',
                        payload TEXT DEFAULT '{}'
                    );

                    CREATE TABLE IF NOT EXISTS economic_calendar (
                        event_id TEXT PRIMARY KEY,
                        event_date TEXT NOT NULL,
                        event_type TEXT DEFAULT '',
                        title TEXT NOT NULL,
                        detail TEXT DEFAULT '',
                        importance TEXT DEFAULT '',
                        market TEXT DEFAULT '',
                        payload TEXT DEFAULT '{}',
                        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                    );
                    """
                )
                self._init_default_config(conn)
                conn.commit()
        finally:
            if conn:
                _return_db_connection(conn)

    def _init_default_config(self, conn) -> None:
        defaults = {
            "refresh_interval_seconds": 15,
            "default_period": "1y",
            "default_symbol": "600519",
            "auto_trade_order_ratio": 0.1,
            "commission_rate": 0.0003,
            "default_stop_loss_pct": 0.05,
            "default_take_profit_pct": 0.1,
            "default_adjust": "qfq",
        }
        for key, value in defaults.items():
            conn.execute(
                """
                INSERT INTO config(config_key, config_value, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(config_key) DO NOTHING
                """,
                (key, _json_dumps(value), _now_str()),
            )

    def execute(self, sql: str, params: Iterable[Any] = (), conn=None) -> sqlite3.Cursor:
        conn_provided = conn is not None
        if not conn_provided:
            conn = _get_db_connection(str(self.db_path))
        try:
            with self._write_lock:
                cursor = conn.execute(sql, tuple(params))
                conn.commit()
                return cursor
        finally:
            if not conn_provided and conn:
                _return_db_connection(conn)

    def executemany(self, sql: str, params: Iterable[Iterable[Any]], conn=None) -> None:
        conn_provided = conn is not None
        if not conn_provided:
            conn = _get_db_connection(str(self.db_path))
        try:
            with self._write_lock:
                conn.executemany(sql, list(params))
                conn.commit()
        finally:
            if not conn_provided and conn:
                _return_db_connection(conn)

    def fetchone(self, sql: str, params: Iterable[Any] = (), conn=None) -> Optional[dict]:
        conn_provided = conn is not None
        if not conn_provided:
            conn = _get_db_connection(str(self.db_path))
        try:
            row = conn.execute(sql, tuple(params)).fetchone()
            return dict(row) if row else None
        finally:
            if not conn_provided and conn:
                _return_db_connection(conn)

    def fetchall(self, sql: str, params: Iterable[Any] = (), conn=None) -> list[dict]:
        conn_provided = conn is not None
        if not conn_provided:
            conn = _get_db_connection(str(self.db_path))
        try:
            rows = conn.execute(sql, tuple(params)).fetchall()
            return [dict(row) for row in rows]
        finally:
            if not conn_provided and conn:
                _return_db_connection(conn)

    def upsert_kline_rows(
        self,
        symbol: str,
        market: str,
        kline_type: str,
        rows: list[dict],
        adjust: str = "qfq",
        instrument_type: str = "stock",
        conn=None,
    ) -> None:
        if not rows:
            return
        now = _now_str()
        payload = []
        for row in rows:
            payload.append(
                (
                    symbol,
                    market,
                    kline_type,
                    adjust,
                    instrument_type,
                    str(row.get("date", "")),
                    float(row.get("open", 0) or 0),
                    float(row.get("high", 0) or 0),
                    float(row.get("low", 0) or 0),
                    float(row.get("close", 0) or 0),
                    float(row.get("volume", 0) or 0),
                    float(row.get("amount", 0) or 0),
                    float(row.get("adjusted_factor", 1) or 1),
                    int(row.get("is_dirty", 0) or 0),
                    str(row.get("source", "")),
                    now,
                    now,
                )
            )
        self.executemany(
            """
            INSERT INTO kline_cache(
                symbol, market, kline_type, adjust, instrument_type, date,
                open, high, low, close, volume, amount, adjusted_factor,
                is_dirty, source, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(symbol, market, kline_type, adjust, date) DO UPDATE SET
                open=excluded.open,
                high=excluded.high,
                low=excluded.low,
                close=excluded.close,
                volume=excluded.volume,
                amount=excluded.amount,
                adjusted_factor=excluded.adjusted_factor,
                is_dirty=excluded.is_dirty,
                source=excluded.source,
                instrument_type=excluded.instrument_type,
                updated_at=excluded.updated_at
            """,
            payload,
            conn=conn,
        )

    def load_kline_rows(
        self,
        symbol: str,
        market: str,
        kline_type: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        adjust: str = "qfq",
        conn=None,
    ) -> pd.DataFrame:
        where = ["symbol = ?", "market = ?", "kline_type = ?", "adjust = ?"]
        params: list[Any] = [symbol, market, kline_type, adjust]
        if start_date:
            where.append("date >= ?")
            params.append(start_date)
        if end_date:
            where.append("date <= ?")
            params.append(end_date)
        rows = self.fetchall(
            f"""
            SELECT date, open, high, low, close, volume, amount,
                   adjusted_factor, is_dirty, source, updated_at
            FROM kline_cache
            WHERE {' AND '.join(where)}
            ORDER BY date ASC
            """,
            params,
            conn=conn,
        )
        if not rows:
            return pd.DataFrame()
        df = pd.DataFrame(rows)
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"], errors="coerce")
            df = df.dropna(subset=["date"]).reset_index(drop=True)
        return df

    def get_latest_kline_date(
        self,
        symbol: str,
        market: str,
        kline_type: str,
        adjust: str = "qfq",
        conn=None,
    ) -> Optional[str]:
        row = self.fetchone(
            """
            SELECT MAX(date) AS latest_date
            FROM kline_cache
            WHERE symbol = ? AND market = ? AND kline_type = ? AND adjust = ?
            """,
            (symbol, market, kline_type, adjust),
            conn=conn,
        )
        return row.get("latest_date") if row else None

    def get_last_update_time(
        self,
        symbol: str,
        market: str,
        kline_type: str,
        adjust: str = "qfq",
        trade_date: Optional[str] = None,
        conn=None,
    ) -> Optional[str]:
        where = ["symbol = ?", "market = ?", "kline_type = ?", "adjust = ?"]
        params: list[Any] = [symbol, market, kline_type, adjust]
        if trade_date:
            where.append("date = ?")
            params.append(trade_date)
        row = self.fetchone(
            f"""
            SELECT MAX(updated_at) AS updated_at
            FROM kline_cache
            WHERE {' AND '.join(where)}
            """,
            params,
            conn=conn,
        )
        return row.get("updated_at") if row else None

    def count_cached_symbols(self, conn=None) -> int:
        row = self.fetchone("SELECT COUNT(DISTINCT symbol) AS total FROM kline_cache", conn=conn)
        return int(row["total"]) if row else 0

    def upsert_financial_rows(self, symbol: str, rows: list[dict], conn=None) -> None:
        if not rows:
            return
        now = _now_str()
        payload = []
        for row in rows:
            payload.append(
                (
                    symbol,
                    str(row.get("report_date", row.get("日期", ""))),
                    float(row.get("revenue", 0) or 0),
                    float(row.get("net_profit", 0) or 0),
                    float(row.get("gross_margin", 0) or 0),
                    float(row.get("net_margin", 0) or 0),
                    float(row.get("roe", 0) or 0),
                    float(row.get("roa", 0) or 0),
                    float(row.get("debt_ratio", 0) or 0),
                    _json_dumps(row),
                    now,
                )
            )
        self.executemany(
            """
            INSERT INTO financial_data(
                symbol, report_date, revenue, net_profit, gross_margin,
                net_margin, roe, roa, debt_ratio, payload, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(symbol, report_date) DO UPDATE SET
                revenue=excluded.revenue,
                net_profit=excluded.net_profit,
                gross_margin=excluded.gross_margin,
                net_margin=excluded.net_margin,
                roe=excluded.roe,
                roa=excluded.roa,
                debt_ratio=excluded.debt_ratio,
                payload=excluded.payload,
                updated_at=excluded.updated_at
            """,
            payload,
            conn=conn,
        )

    def get_financials(self, symbol: str, conn=None) -> list[dict]:
        return self.fetchall(
            """
            SELECT symbol, report_date, revenue, net_profit, gross_margin,
                   net_margin, roe, roa, debt_ratio, payload, updated_at
            FROM financial_data
            WHERE symbol = ?
            ORDER BY report_date DESC
            """,
            (symbol,),
            conn=conn,
        )

    def upsert_stock_info_rows(self, rows: list[dict], conn=None) -> None:
        if not rows:
            return
        now = _now_str()
        payload = []
        for row in rows:
            extra = row.get("extra_json", {})
            if not isinstance(extra, str):
                extra = _json_dumps(extra)
            payload.append(
                (
                    str(row.get("symbol", "")),
                    str(row.get("market", "A")),
                    str(row.get("name", "")),
                    str(row.get("instrument_type", "stock")),
                    str(row.get("industry", "")),
                    str(row.get("concepts", "")),
                    float(row.get("market_value", 0) or 0),
                    float(row.get("float_market_value", 0) or 0),
                    str(row.get("list_date", "")),
                    float(row.get("pe_ttm", 0) or 0),
                    float(row.get("pb", 0) or 0),
                    extra,
                    now,
                )
            )
        self.executemany(
            """
            INSERT INTO stock_info(
                symbol, market, name, instrument_type, industry, concepts,
                market_value, float_market_value, list_date, pe_ttm, pb,
                extra_json, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(symbol, market) DO UPDATE SET
                name=excluded.name,
                instrument_type=excluded.instrument_type,
                industry=excluded.industry,
                concepts=excluded.concepts,
                market_value=excluded.market_value,
                float_market_value=excluded.float_market_value,
                list_date=excluded.list_date,
                pe_ttm=excluded.pe_ttm,
                pb=excluded.pb,
                extra_json=excluded.extra_json,
                updated_at=excluded.updated_at
            """,
            payload,
            conn=conn,
        )

    def search_stock_info(
        self,
        query: str,
        limit: int = 20,
        market: Optional[str] = None,
        instrument_types: Optional[list[str]] = None,
        conn=None,
    ) -> list[dict]:
        query = query.strip()
        if not query:
            return []
        where = ["(symbol LIKE ? OR name LIKE ? OR industry LIKE ? OR concepts LIKE ?)"]
        params: list[Any] = [f"{query}%", f"%{query}%", f"%{query}%", f"%{query}%"]
        if market:
            where.append("market = ?")
            params.append(market)
        if instrument_types:
            placeholders = ",".join("?" for _ in instrument_types)
            where.append(f"instrument_type IN ({placeholders})")
            params.extend(instrument_types)
        return self.fetchall(
            f"""
            SELECT symbol AS code, name, market, industry AS sector,
                   instrument_type, concepts, market_value, float_market_value,
                   list_date, pe_ttm, pb, extra_json
            FROM stock_info
            WHERE {' AND '.join(where)}
            ORDER BY
                CASE WHEN symbol = ? THEN 0 ELSE 1 END,
                CASE WHEN symbol LIKE ? THEN 0 ELSE 1 END,
                market_value DESC,
                symbol ASC
            LIMIT ?
            """,
            [*params, query, f"{query}%", limit],
            conn=conn,
        )

    def get_stock_info(self, symbol: str, market: Optional[str] = None, conn=None) -> Optional[dict]:
        if market:
            row = self.fetchone(
                """
                SELECT symbol AS code, name, market, industry AS sector, instrument_type,
                       concepts, market_value, float_market_value, list_date, pe_ttm, pb, extra_json
                FROM stock_info
                WHERE symbol = ? AND market = ?
                """,
                (symbol, market),
                conn=conn,
            )
        else:
            row = self.fetchone(
                """
                SELECT symbol AS code, name, market, industry AS sector, instrument_type,
                       concepts, market_value, float_market_value, list_date, pe_ttm, pb, extra_json
                FROM stock_info
                WHERE symbol = ?
                ORDER BY market = 'A' DESC, market_value DESC
                LIMIT 1
                """,
                (symbol,),
                conn=conn,
            )
        return row

    def record_source_request(
        self,
        source_name: str,
        request_type: str,
        success: bool,
        latency_ms: float,
        error: str = "",
        conn=None,
    ) -> None:
        key = (source_name, request_type)
        event = {
            "ts": _now_str(),
            "success": bool(success),
            "latency_ms": round(float(latency_ms or 0), 2),
            "error": error[:500] if error else "",
        }
        window = self._source_windows[key]
        window.append(event)
        total = len(window)
        success_requests = sum(1 for item in window if item["success"])
        failure_requests = total - success_requests
        avg_response_ms = float(np.mean([item["latency_ms"] for item in window])) if window else 0
        success_rate = success_requests / total if total else 0
        priority = 100 if success_rate >= 0.5 else 200
        self.execute(
            """
            INSERT INTO data_source_stats(
                source_name, request_type, success_rate, avg_response_ms,
                total_requests, success_requests, failure_requests, priority,
                last_error, recent_requests_json, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(source_name, request_type) DO UPDATE SET
                success_rate=excluded.success_rate,
                avg_response_ms=excluded.avg_response_ms,
                total_requests=excluded.total_requests,
                success_requests=excluded.success_requests,
                failure_requests=excluded.failure_requests,
                priority=excluded.priority,
                last_error=excluded.last_error,
                recent_requests_json=excluded.recent_requests_json,
                updated_at=excluded.updated_at
            """,
            (
                source_name,
                request_type,
                success_rate,
                avg_response_ms,
                total,
                success_requests,
                failure_requests,
                priority,
                error[:500],
                _json_dumps(list(window)),
                _now_str(),
            ),
            conn=conn,
        )

    def get_source_stats(self, conn=None) -> list[dict]:
        return self.fetchall(
            """
            SELECT source_name, request_type, success_rate, avg_response_ms,
                   total_requests, success_requests, failure_requests, priority,
                   last_error, recent_requests_json, updated_at
            FROM data_source_stats
            ORDER BY priority ASC, success_rate DESC, avg_response_ms ASC
            """,
            conn=conn,
        )

    def upsert_zt_pool_rows(self, trade_date: str, pool_type: str, rows: list[dict]) -> None:
        if not rows:
            return
        payload = []
        for row in rows:
            payload.append(
                (
                    trade_date,
                    pool_type,
                    str(row.get("symbol", row.get("代码", ""))),
                    str(row.get("name", row.get("名称", ""))),
                    float(row.get("order_amount", row.get("封单资金", 0)) or 0),
                    str(row.get("reason", row.get("涨停原因", ""))),
                    str(row.get("seal_time", row.get("首次封板时间", ""))),
                    _json_dumps(row),
                    _now_str(),
                )
            )
        self.executemany(
            """
            INSERT INTO zt_pool(
                trade_date, pool_type, symbol, name, order_amount, reason,
                seal_time, payload, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(trade_date, pool_type, symbol) DO UPDATE SET
                name=excluded.name,
                order_amount=excluded.order_amount,
                reason=excluded.reason,
                seal_time=excluded.seal_time,
                payload=excluded.payload,
                updated_at=excluded.updated_at
            """,
            payload,
        )

    def get_zt_pool(self, trade_date: str, pool_type: Optional[str] = None, conn=None) -> list[dict]:
        if pool_type:
            return self.fetchall(
                """
                SELECT trade_date, pool_type, symbol, name, order_amount, reason,
                       seal_time, payload, updated_at
                FROM zt_pool
                WHERE trade_date = ? AND pool_type = ?
                ORDER BY order_amount DESC, seal_time ASC
                """,
                (trade_date, pool_type),
                conn=conn,
            )
        return self.fetchall(
            """
            SELECT trade_date, pool_type, symbol, name, order_amount, reason,
                   seal_time, payload, updated_at
            FROM zt_pool
            WHERE trade_date = ?
            ORDER BY pool_type ASC, order_amount DESC
            """,
            (trade_date,),
            conn=conn,
        )

    def upsert_northbound(self, rows: list[dict]) -> None:
        if not rows:
            return
        payload = []
        for row in rows:
            payload.append(
                (
                    str(row.get("trade_date", row.get("date", ""))),
                    float(row.get("sh_connect", 0) or 0),
                    float(row.get("sz_connect", 0) or 0),
                    float(row.get("total_flow", 0) or 0),
                    float(row.get("net_buy", 0) or 0),
                    _json_dumps(row.get("top_stocks", [])),
                    _now_str(),
                )
            )
        self.executemany(
            """
            INSERT INTO northbound_flow(
                trade_date, sh_connect, sz_connect, total_flow, net_buy,
                top_stocks_json, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(trade_date) DO UPDATE SET
                sh_connect=excluded.sh_connect,
                sz_connect=excluded.sz_connect,
                total_flow=excluded.total_flow,
                net_buy=excluded.net_buy,
                top_stocks_json=excluded.top_stocks_json,
                updated_at=excluded.updated_at
            """,
            payload,
        )

    def get_northbound(self, limit: int = 10, conn=None) -> list[dict]:
        return self.fetchall(
            """
            SELECT trade_date, sh_connect, sz_connect, total_flow, net_buy,
                   top_stocks_json, updated_at
            FROM northbound_flow
            ORDER BY trade_date DESC
            LIMIT ?
            """,
            (limit,),
            conn=conn,
        )

    def upsert_market_sentiment(self, row: dict) -> None:
        self.execute(
            """
            INSERT INTO market_sentiment(
                trade_date, advancers, decliners, up_down_ratio, turnover_amount,
                margin_balance_change, new_high_low_ratio, mcclellan, ad_line,
                new_high_low_index, payload, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(trade_date) DO UPDATE SET
                advancers=excluded.advancers,
                decliners=excluded.decliners,
                up_down_ratio=excluded.up_down_ratio,
                turnover_amount=excluded.turnover_amount,
                margin_balance_change=excluded.margin_balance_change,
                new_high_low_ratio=excluded.new_high_low_ratio,
                mcclellan=excluded.mcclellan,
                ad_line=excluded.ad_line,
                new_high_low_index=excluded.new_high_low_index,
                payload=excluded.payload,
                updated_at=excluded.updated_at
            """,
            (
                str(row.get("trade_date", row.get("date", ""))),
                int(row.get("advancers", 0) or 0),
                int(row.get("decliners", 0) or 0),
                float(row.get("up_down_ratio", 0) or 0),
                float(row.get("turnover_amount", 0) or 0),
                float(row.get("margin_balance_change", 0) or 0),
                float(row.get("new_high_low_ratio", 0) or 0),
                float(row.get("mcclellan", 0) or 0),
                float(row.get("ad_line", 0) or 0),
                float(row.get("new_high_low_index", 0) or 0),
                _json_dumps(row),
                _now_str(),
            ),
        )

    def get_market_sentiment(self, limit: int = 20, conn=None) -> list[dict]:
        return self.fetchall(
            """
            SELECT trade_date, advancers, decliners, up_down_ratio, turnover_amount,
                   margin_balance_change, new_high_low_ratio, mcclellan, ad_line,
                   new_high_low_index, payload, updated_at
            FROM market_sentiment
            ORDER BY trade_date DESC
            LIMIT ?
            """,
            (limit,),
            conn=conn,
        )

    def set_config(self, key: str, value: Any, conn=None) -> None:
        self.execute(
            """
            INSERT INTO config(config_key, config_value, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(config_key) DO UPDATE SET
                config_value=excluded.config_value,
                updated_at=excluded.updated_at
            """,
            (key, _json_dumps(value), _now_str()),
            conn=conn,
        )

    def get_config(self, key: str, default: Any = None, conn=None) -> Any:
        row = self.fetchone("SELECT config_value FROM config WHERE config_key = ?", (key,), conn=conn)
        if not row:
            return default
        try:
            return json.loads(row["config_value"])
        except json.JSONDecodeError:
            return row["config_value"]

    def list_config(self, conn=None) -> dict[str, Any]:
        rows = self.fetchall("SELECT config_key, config_value FROM config ORDER BY config_key ASC", conn=conn)
        output: dict[str, Any] = {}
        for row in rows:
            try:
                output[row["config_key"]] = json.loads(row["config_value"])
            except json.JSONDecodeError:
                output[row["config_key"]] = row["config_value"]
        return output

    def record_api_metric(
        self,
        endpoint: str,
        latency_ms: float,
        status_code: int = 200,
        cache_hit: bool = False,
        source: str = "",
        conn=None,
    ) -> None:
        self.execute(
            """
            INSERT INTO api_metrics(endpoint, latency_ms, status_code, cache_hit, source)
            VALUES (?, ?, ?, ?, ?)
            """,
            (endpoint, float(latency_ms or 0), int(status_code), int(bool(cache_hit)), source),
            conn=conn,
        )

    def get_api_metrics(self, lookback_hours: int = 1, conn=None) -> dict[str, dict]:
        rows = self.fetchall(
            """
            SELECT endpoint, latency_ms, status_code, cache_hit, created_at
            FROM api_metrics
            WHERE datetime(created_at) >= datetime('now', ?)
            ORDER BY created_at DESC
            """,
            (f"-{lookback_hours} hours",),
            conn=conn,
        )
        grouped: dict[str, list[dict]] = defaultdict(list)
        for row in rows:
            grouped[row["endpoint"]].append(row)
        output: dict[str, dict] = {}
        for endpoint, items in grouped.items():
            latencies = np.array([float(item["latency_ms"]) for item in items], dtype=float)
            cache_hits = sum(int(item["cache_hit"]) for item in items)
            output[endpoint] = {
                "p50": round(float(np.percentile(latencies, 50)), 2),
                "p95": round(float(np.percentile(latencies, 95)), 2),
                "p99": round(float(np.percentile(latencies, 99)), 2),
                "avg": round(float(np.mean(latencies)), 2),
                "count": len(items),
                "error_count": sum(1 for item in items if int(item["status_code"]) >= 400),
                "cache_hit_rate": round(cache_hits / len(items), 4) if items else 0,
            }
        return output

    def record_system_metric(self, metric_name: str, metric_value: float, conn=None) -> None:
        self.execute(
            "INSERT INTO system_metrics(metric_name, metric_value) VALUES (?, ?)",
            (metric_name, float(metric_value or 0)),
            conn=conn,
        )

    def get_system_metric_series(self, metric_name: str, limit: int = 120, conn=None) -> list[dict]:
        return self.fetchall(
            """
            SELECT metric_name, metric_value, created_at
            FROM system_metrics
            WHERE metric_name = ?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (metric_name, limit),
            conn=conn,
        )

    def record_usage(
        self,
        event_type: str,
        symbol: str = "",
        strategy: str = "",
        duration_ms: float = 0,
        payload: Optional[dict] = None,
        conn=None,
    ) -> None:
        self.execute(
            """
            INSERT INTO usage_events(event_type, symbol, strategy, duration_ms, payload)
            VALUES (?, ?, ?, ?, ?)
            """,
            (event_type, symbol, strategy, float(duration_ms or 0), _json_dumps(payload or {})),
            conn=conn,
        )

    def get_usage_summary(self, conn=None) -> dict[str, Any]:
        return {
            "top_symbols": self.fetchall(
                """
                SELECT symbol, COUNT(*) AS total
                FROM usage_events
                WHERE symbol <> ''
                GROUP BY symbol
                ORDER BY total DESC
                LIMIT 20
                """,
                conn=conn,
            ),
            "active_hours": self.fetchall(
                """
                SELECT strftime('%H', created_at) AS hour, COUNT(*) AS total
                FROM usage_events
                GROUP BY hour
                ORDER BY hour ASC
                """,
                conn=conn,
            ),
            "top_strategies": self.fetchall(
                """
                SELECT strategy, COUNT(*) AS total
                FROM usage_events
                WHERE strategy <> ''
                GROUP BY strategy
                ORDER BY total DESC
                LIMIT 20
                """,
                conn=conn,
            ),
            "avg_backtest_ms": self.fetchone(
                """
                SELECT COALESCE(AVG(duration_ms), 0) AS avg_ms
                FROM usage_events
                WHERE event_type = 'backtest'
                """,
                conn=conn,
            ),
        }

    def log_trade(self, row: dict, conn=None) -> None:
        self.execute(
            """
            INSERT OR REPLACE INTO trade_log(
                id, trade_time, symbol, name, direction, quantity, price, fee,
                slippage_cost, strategy_name, signal_values, cost_basis,
                pnl_amount, pnl_pct, note
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row.get("id"),
                row.get("trade_time", _now_str()),
                row.get("symbol", ""),
                row.get("name", ""),
                row.get("direction", ""),
                int(row.get("quantity", 0) or 0),
                float(row.get("price", 0) or 0),
                float(row.get("fee", 0) or 0),
                float(row.get("slippage_cost", 0) or 0),
                row.get("strategy_name", ""),
                _json_dumps(row.get("signal_values", {})),
                float(row.get("cost_basis", 0) or 0),
                float(row.get("pnl_amount", 0) or 0),
                float(row.get("pnl_pct", 0) or 0),
                row.get("note", ""),
            ),
            conn=conn,
        )

    def get_trade_logs(
        self,
        symbol: str = "",
        strategy_name: str = "",
        limit: int = 200,
        conn=None,
    ) -> list[dict]:
        where = ["1 = 1"]
        params: list[Any] = []
        if symbol:
            where.append("symbol = ?")
            params.append(symbol)
        if strategy_name:
            where.append("strategy_name = ?")
            params.append(strategy_name)
        params.append(limit)
        return self.fetchall(
            f"""
            SELECT *
            FROM trade_log
            WHERE {' AND '.join(where)}
            ORDER BY trade_time DESC
            LIMIT ?
            """,
            params,
            conn=conn,
        )

    def save_account_snapshot(
        self,
        total_assets: float,
        cash: float,
        market_value: float,
        payload: Optional[dict] = None,
        benchmark: str = "000300",
        conn=None,
    ) -> None:
        snapshot_time = _now_str()
        self.execute(
            """
            INSERT OR REPLACE INTO account_snapshots(
                snapshot_time, total_assets, cash, market_value, benchmark, payload
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (snapshot_time, total_assets, cash, market_value, benchmark, _json_dumps(payload or {})),
            conn=conn,
        )

    def get_account_snapshots(self, limit: int = 200, conn=None) -> list[dict]:
        return self.fetchall(
            """
            SELECT snapshot_time, total_assets, cash, market_value, benchmark, payload
            FROM account_snapshots
            ORDER BY snapshot_time DESC
            LIMIT ?
            """,
            (limit,),
            conn=conn,
        )

    def upsert_economic_events(self, rows: list[dict], conn=None) -> None:
        if not rows:
            return
        payload = []
        for row in rows:
            payload.append(
                (
                    str(row.get("event_id", row.get("id", ""))),
                    str(row.get("event_date", row.get("date", ""))),
                    str(row.get("event_type", row.get("type", ""))),
                    str(row.get("title", "")),
                    str(row.get("detail", row.get("description", ""))),
                    str(row.get("importance", "")),
                    str(row.get("market", "")),
                    _json_dumps(row),
                    _now_str(),
                )
            )
        self.executemany(
            """
            INSERT INTO economic_calendar(
                event_id, event_date, event_type, title, detail,
                importance, market, payload, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(event_id) DO UPDATE SET
                event_date=excluded.event_date,
                event_type=excluded.event_type,
                title=excluded.title,
                detail=excluded.detail,
                importance=excluded.importance,
                market=excluded.market,
                payload=excluded.payload,
                updated_at=excluded.updated_at
            """,
            payload,
            conn=conn,
        )

    def get_economic_events(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        conn=None,
    ) -> list[dict]:
        where = ["1 = 1"]
        params: list[Any] = []
        if start_date:
            where.append("event_date >= ?")
            params.append(start_date)
        if end_date:
            where.append("event_date <= ?")
            params.append(end_date)
        return self.fetchall(
            f"""
            SELECT event_id, event_date, event_type, title, detail, importance,
                   market, payload, updated_at
            FROM economic_calendar
            WHERE {' AND '.join(where)}
            ORDER BY event_date ASC, importance DESC, title ASC
            """,
            params,
            conn=conn,
        )


_DB_SINGLETON: Optional[SQLiteStore] = None
_DB_SINGLETON_LOCK = threading.Lock()


def get_db() -> SQLiteStore:
    global _DB_SINGLETON
    if _DB_SINGLETON is None:
        with _DB_SINGLETON_LOCK:
            if _DB_SINGLETON is None:
                try:
                    _DB_SINGLETON = SQLiteStore()
                except Exception as e:
                    logger.error(f"Failed to initialize database: {e}")
                    raise
    return _DB_SINGLETON
