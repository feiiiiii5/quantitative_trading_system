import logging
from datetime import datetime

from fastapi import APIRouter, Query

from api.utils import json_response as _json_response

logger = logging.getLogger(__name__)
duckdb_router = APIRouter()

try:
    from core.duckdb_analytics import DuckDBAnalytics
    DUCKDB_AVAILABLE = True
except ImportError:
    DUCKDB_AVAILABLE = False
    logger.debug("DuckDB not available, analytics endpoints will return graceful errors")

_analytics = None


def _get_analytics() -> "DuckDBAnalytics | None":
    global _analytics
    if not DUCKDB_AVAILABLE:
        return None
    if _analytics is None:
        try:
            _analytics = DuckDBAnalytics()
        except Exception as e:
            logger.warning("Failed to initialize DuckDB analytics: %s", e)
            return None
    return _analytics


@duckdb_router.get("/duckdb/status")
async def duckdb_status():
    return _json_response(True, data={
        "duckdb_available": DUCKDB_AVAILABLE,
        "in_memory_mode": True,
    })


@duckdb_router.get("/duckdb/tables")
async def list_tables():
    analytics = _get_analytics()
    if analytics is None:
        return _json_response(False, error="DuckDB is not available. Install with: pip install duckdb")
    tables = analytics.list_tables()
    return _json_response(True, data={"tables": tables})


@duckdb_router.get("/duckdb/describe/{table_name}")
async def describe_table(table_name: str):
    if not table_name.replace("_", "").isalnum():
        return _json_response(False, error="Invalid table name")
    analytics = _get_analytics()
    if analytics is None:
        return _json_response(False, error="DuckDB is not available. Install with: pip install duckdb")
    info = analytics.get_table_info(table_name)
    if info is None:
        return _json_response(False, error=f"Table '{table_name}' not found or not accessible")
    return _json_response(True, data={"table": table_name, "info": info})


@duckdb_router.get("/duckdb/correlation")
async def correlation_matrix(
    table_name: str = Query("price_data"),
    method: str = Query("pearson"),
    limit: int = Query(100, ge=1, le=500),
):
    if method not in ("pearson", "spearman"):
        return _json_response(False, error="method must be 'pearson' or 'spearman'")
    if not table_name.replace("_", "").isalnum():
        return _json_response(False, error="Invalid table name")
    analytics = _get_analytics()
    if analytics is None:
        return _json_response(False, error="DuckDB is not available. Install with: pip install duckdb")
    result = analytics.get_correlation_matrix(table_name, method, limit)
    if result is None:
        return _json_response(False, error=f"Failed to compute correlation for {table_name}")
    return _json_response(True, data={"table": table_name, "method": method, "matrix": result})


@duckdb_router.get("/duckdb/rolling-correlation")
async def rolling_correlation(
    symbol_a: str = Query(...),
    symbol_b: str = Query(...),
    period: int = Query(20, ge=5, le=252),
    table_name: str = Query("price_data"),
):
    if not symbol_a.replace("_", "").isalnum() or not symbol_b.replace("_", "").isalnum():
        return _json_response(False, error="Invalid symbol")
    if not table_name.replace("_", "").isalnum():
        return _json_response(False, error="Invalid table name")
    analytics = _get_analytics()
    if analytics is None:
        return _json_response(False, error="DuckDB is not available. Install with: pip install duckdb")
    result = analytics.get_rolling_correlation(symbol_a, symbol_b, period, table_name)
    if result is None:
        return _json_response(False, error=f"Failed to compute rolling correlation for {symbol_a} vs {symbol_b}")
    return _json_response(True, data={
        "symbol_a": symbol_a,
        "symbol_b": symbol_b,
        "period": period,
        "correlation": result,
    })


@duckdb_router.get("/duckdb/describe-ohlcv/{symbol}")
async def describe_ohlcv(
    symbol: str,
    start_date: str = Query(None),
    end_date: str = Query(None),
):
    if not symbol.replace("_", "").replace(".", "").isalnum():
        return _json_response(False, error="Invalid symbol")
    try:
        if start_date:
            datetime.strptime(start_date, "%Y-%m-%d")
        if end_date:
            datetime.strptime(end_date, "%Y-%m-%d")
    except ValueError:
        return _json_response(False, error="Invalid date format, use YYYY-MM-DD")

    analytics = _get_analytics()
    if analytics is None:
        return _json_response(False, error="DuckDB is not available. Install with: pip install duckdb")
    result = analytics.describe_ohlcv(symbol, start_date, end_date)
    if result is None:
        return _json_response(False, error=f"No data for {symbol} in date range")
    return _json_response(True, data={"symbol": symbol, "stats": result})
