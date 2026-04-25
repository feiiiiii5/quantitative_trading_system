import asyncio
import logging
import time
from collections import OrderedDict
from typing import Optional

import numpy as np
import pandas as pd
from fastapi import APIRouter, Query, Request

from core.data_fetcher import SmartDataFetcher, KLINE_TYPE_MAP
from core.indicators import TechnicalIndicators
from core.market_detector import MarketDetector
from core.market_hours import MarketHours
from core.prediction import PricePredictor
from core.stock_search import search_stocks, get_stock_info, get_all_industries, get_hot_search_terms, get_stocks_by_market, get_market_summary
from core.market_data import get_market_page, refresh_stock_list
from core.simulated_trading import SimulatedTrading
from core.file_cache import get as file_cache_get, set as file_cache_set

logger = logging.getLogger(__name__)
router = APIRouter()

_MAX_ROUTE_CACHE = 200
_cache: OrderedDict = OrderedDict()
_CACHE_TTL = 60


def _cache_get(key: str):
    entry = _cache.get(key)
    if entry and (time.time() - entry["ts"]) < entry.get("ttl", _CACHE_TTL):
        _cache.move_to_end(key)
        return entry["data"]
    if key in _cache:
        del _cache[key]
    return None


def _cache_set(key: str, data, ttl: Optional[int] = None):
    if key in _cache:
        _cache.move_to_end(key)
    _cache[key] = {"data": data, "ts": time.time(), "ttl": ttl or _CACHE_TTL}
    while len(_cache) > _MAX_ROUTE_CACHE:
        _cache.popitem(last=False)


def _json_response(success: bool, data=None, error: str = ""):
    return {"success": success, "data": data, "error": error}


@router.get("/search")
async def search_stock(
    request: Request,
    q: str = Query(..., min_length=1, max_length=20),
    market: Optional[str] = Query(None),
    limit: int = Query(10, ge=1, le=50),
    category: Optional[str] = Query(None),
):
    try:
        results = search_stocks(q, limit=limit, market=market, category=category)
        return _json_response(True, data=results)
    except Exception as e:
        logger.error(f"search error: {e}", exc_info=True)
        return _json_response(False, error=str(e))


@router.get("/search/industry")
async def get_industries(request: Request):
    try:
        industries = get_all_industries()
        return _json_response(True, data=industries)
    except Exception as e:
        return _json_response(False, error=str(e))


@router.get("/search/hot")
async def search_hot(request: Request):
    try:
        data = get_hot_search_terms()
        return _json_response(True, data=data)
    except Exception as e:
        return _json_response(False, error=str(e))


@router.get("/market-list/{market}")
async def get_market_list(request: Request, market: str, limit: int = Query(50), offset: int = Query(0)):
    try:
        data = get_stocks_by_market(market, limit, offset)
        return _json_response(True, data=data)
    except Exception as e:
        return _json_response(False, error=str(e))


@router.get("/market/{market}/page")
async def get_market_page_api(
    request: Request,
    market: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=80),
    sort: str = Query("pct"),
    asc: bool = Query(False),
    sector: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
):
    try:
        cache_key = f"mkt_page:{market}:{page}:{page_size}:{sort}:{asc}:{sector}:{search}"
        cached = file_cache_get(cache_key)
        if cached:
            return _json_response(True, data=cached)
        data = get_market_page(market, page=page, page_size=page_size, sort=sort, asc=asc, sector=sector, search=search)
        file_cache_set(cache_key, data, ttl=15)
        return _json_response(True, data=data)
    except Exception as e:
        logger.error(f"market page error: {e}", exc_info=True)
        return _json_response(False, error=str(e))


@router.post("/market/refresh/{market}")
async def refresh_market_list(request: Request, market: str):
    try:
        result = refresh_stock_list(market)
        return _json_response(True, data=result)
    except Exception as e:
        return _json_response(False, error=str(e))


@router.get("/market-summary")
async def get_market_summary_api(request: Request):
    try:
        cache_key = "market_summary"
        cached = file_cache_get(cache_key)
        if cached:
            return _json_response(True, data=cached)
        data = get_market_summary()
        file_cache_set(cache_key, data, ttl=3600)
        return _json_response(True, data=data)
    except Exception as e:
        return _json_response(False, error=str(e))


@router.get("/stock/{symbol}")
async def get_stock_full(
    request: Request, 
    symbol: str, 
    period: str = Query("1y"),
    fields: Optional[str] = Query(None, description="按需加载字段，逗号分隔: history,indicators,prediction,realtime,fundamentals")
):
    try:
        kline_type = KLINE_TYPE_MAP.get(period, "daily")
        cache_key = f"full:{symbol}:{period}:{kline_type}:{fields or 'all'}"
        cached = _cache_get(cache_key)
        if cached:
            return _json_response(True, data=cached)

        market_info = MarketDetector.get_config(symbol)
        stock_info = get_stock_info(symbol)

        # 按需加载字段
        requested_fields = fields.split(",") if fields else ["history", "indicators", "prediction", "realtime", "fundamentals"]
        tasks = []
        task_indices = {}
        
        if "history" in requested_fields:
            task_indices["history"] = len(tasks)
            tasks.append(request.app.state.fetcher.get_history(symbol, period, kline_type))
        
        if "realtime" in requested_fields:
            task_indices["realtime"] = len(tasks)
            tasks.append(request.app.state.fetcher.get_realtime(symbol))
        
        if "fundamentals" in requested_fields:
            task_indices["fundamentals"] = len(tasks)
            tasks.append(request.app.state.fetcher.get_fundamentals(symbol, market_info["market"]))

        results = await asyncio.gather(*tasks) if tasks else []
        
        # 初始化结果变量
        df = None
        realtime = None
        fundamentals = None
        
        # 根据任务索引分配结果
        if "history" in task_indices:
            df = results[task_indices["history"]]
        if "realtime" in task_indices:
            realtime = results[task_indices["realtime"]]
        if "fundamentals" in task_indices:
            fundamentals = results[task_indices["fundamentals"]]

        stock_name = realtime.get("name", "") if realtime else ""
        if not stock_name and stock_info:
            stock_name = stock_info.get("name", "")

        result = {
            "symbol": symbol,
            "name": stock_name,
            "market": market_info,
        }

        if stock_info:
            result["sector"] = stock_info.get("sector", "")

        if "history" in requested_fields and df is not None:
            if df.empty:
                result["history"] = []
                result["no_history"] = True
            else:
                history_data = _df_to_chart(df, kline_type)
                result["history"] = history_data
                result["is_intraday"] = kline_type == "intraday"
        
        if "indicators" in requested_fields and df is not None and not df.empty:
            indicators = TechnicalIndicators.compute_all(df)
            result["indicators"] = indicators
        
        if "prediction" in requested_fields and df is not None and not df.empty:
            prediction = PricePredictor.predict(df, symbol)
            result["prediction"] = prediction
        
        if "realtime" in requested_fields:
            result["realtime"] = realtime
        
        if "fundamentals" in requested_fields:
            result["fundamentals"] = fundamentals

        _cache_set(cache_key, result, ttl=30)
        return _json_response(True, data=result)
    except Exception as e:
        logger.error(f"get_stock_full error: {e}", exc_info=True)
        return _json_response(False, error=str(e))


@router.get("/history")
async def get_history(
    request: Request, 
    symbol: str = Query(...), 
    period: str = Query("1y"),
    page: int = Query(1, ge=1),
    limit: int = Query(100, ge=1, le=500)
):
    try:
        kline_type = KLINE_TYPE_MAP.get(period, "daily")
        cache_key = f"hist:{symbol}:{period}:{kline_type}:{page}:{limit}"
        cached = _cache_get(cache_key)
        if cached:
            return _json_response(True, data=cached)

        df = await request.app.state.fetcher.get_history(symbol, period, kline_type)
        if df.empty:
            return _json_response(False, error="No history data")
        
        # 实现分页
        total = len(df)
        start = (page - 1) * limit
        end = start + limit
        paginated_df = df.iloc[start:end]
        
        data = _df_to_chart(paginated_df, kline_type)
        result = {
            "data": data,
            "total": total,
            "page": page,
            "limit": limit,
            "pages": (total + limit - 1) // limit,
            "is_intraday": kline_type == "intraday",
        }
        
        _cache_set(cache_key, result, ttl=60)
        return _json_response(True, data=result)
    except Exception as e:
        logger.error(f"get_history error: {e}", exc_info=True)
        return _json_response(False, error=str(e))


@router.get("/realtime")
async def get_realtime(request: Request, symbol: str = Query(...)):
    try:
        cache_key = f"rt:{symbol}"
        cached = _cache_get(cache_key)
        if cached:
            return _json_response(True, data=cached)

        data = await request.app.state.fetcher.get_realtime(symbol)
        if not data:
            return _json_response(False, error="No realtime data")
        _cache_set(cache_key, data, ttl=8)
        return _json_response(True, data=data)
    except Exception as e:
        logger.error(f"get_realtime error: {e}", exc_info=True)
        return _json_response(False, error=str(e))


@router.get("/indicators")
async def get_indicators(request: Request, symbol: str = Query(...), period: str = Query("1y")):
    try:
        kline_type = KLINE_TYPE_MAP.get(period, "daily")
        cache_key = f"ind:{symbol}:{period}:{kline_type}"
        cached = _cache_get(cache_key)
        if cached:
            return _json_response(True, data=cached)

        df = await request.app.state.fetcher.get_history(symbol, period, kline_type)
        if df.empty:
            return _json_response(False, error="No data for indicators")
        indicators = TechnicalIndicators.compute_all(df)
        _cache_set(cache_key, indicators, ttl=30)
        return _json_response(True, data=indicators)
    except Exception as e:
        logger.error(f"get_indicators error: {e}", exc_info=True)
        return _json_response(False, error=str(e))


@router.get("/prediction")
async def get_prediction(request: Request, symbol: str = Query(...), period: str = Query("1y")):
    try:
        kline_type = KLINE_TYPE_MAP.get(period, "daily")
        cache_key = f"pred:{symbol}:{period}:{kline_type}"
        cached = _cache_get(cache_key)
        if cached:
            return _json_response(True, data=cached)

        df = await request.app.state.fetcher.get_history(symbol, period, kline_type)
        if df.empty:
            return _json_response(False, error="No data for prediction")
        prediction = PricePredictor.predict(df, symbol)
        _cache_set(cache_key, prediction, ttl=30)
        return _json_response(True, data=prediction)
    except Exception as e:
        logger.error(f"get_prediction error: {e}", exc_info=True)
        return _json_response(False, error=str(e))


@router.get("/market/{symbol}")
async def get_market_info(request: Request, symbol: str):
    try:
        info = MarketDetector.get_config(symbol)
        stock_info = get_stock_info(symbol)
        result = {"market_info": info}
        if stock_info:
            result["stock_info"] = stock_info
        return _json_response(True, data=result)
    except Exception as e:
        return _json_response(False, error=str(e))


@router.get("/hot")
async def get_hot_stocks(request: Request):
    try:
        cache_key = "hot:stocks"
        cached = _cache_get(cache_key)
        if cached:
            return _json_response(True, data=cached)

        data = await request.app.state.fetcher.get_hot_stocks()
        _cache_set(cache_key, data, ttl=60)
        return _json_response(True, data=data)
    except Exception as e:
        logger.error(f"get_hot_stocks error: {e}", exc_info=True)
        return _json_response(False, error=str(e))


@router.get("/hot-stocks")
async def get_hot_stocks_alias(request: Request, limit: int = Query(20, ge=1, le=50)):
    try:
        cache_key = f"hot:stocks:{limit}"
        cached = _cache_get(cache_key)
        if cached:
            return _json_response(True, data=cached)

        data = await request.app.state.fetcher.get_hot_stocks()
        if data and limit < len(data):
            data = data[:limit]
        _cache_set(cache_key, data, ttl=60)
        return _json_response(True, data=data)
    except Exception as e:
        logger.error(f"get_hot_stocks error: {e}", exc_info=True)
        return _json_response(False, error=str(e))


@router.get("/market-overview")
async def get_market_overview(request: Request):
    try:
        cache_key = "market:overview"
        cached = _cache_get(cache_key)
        if cached:
            return _json_response(True, data=cached)

        data = await request.app.state.fetcher.get_market_overview()
        _cache_set(cache_key, data, ttl=30)
        return _json_response(True, data=data)
    except Exception as e:
        logger.error(f"get_market_overview error: {e}", exc_info=True)
        return _json_response(False, error=str(e))


@router.get("/fundamentals")
async def get_fundamentals(request: Request, symbol: str = Query(...)):
    try:
        cache_key = f"fund:{symbol}"
        cached = _cache_get(cache_key)
        if cached:
            return _json_response(True, data=cached)

        market_info = MarketDetector.get_config(symbol)
        data = await request.app.state.fetcher.get_fundamentals(symbol, market_info["market"])
        _cache_set(cache_key, data, ttl=300)
        return _json_response(True, data=data)
    except Exception as e:
        logger.error(f"get_fundamentals error: {e}", exc_info=True)
        return _json_response(False, error=str(e))


@router.get("/market-status/{market}")
async def get_market_status(request: Request, market: str):
    try:
        if market not in ("A", "HK", "US"):
            return _json_response(False, error="Invalid market")
        status = MarketHours.get_market_status(market)
        refresh_interval = MarketHours.get_refresh_interval(market)
        status["refresh_interval"] = refresh_interval
        return _json_response(True, data=status)
    except Exception as e:
        return _json_response(False, error=str(e))


@router.get("/strategies")
async def get_strategies(request: Request):
    try:
        info = request.app.state.composite_strategy.get_strategy_info()
        return _json_response(True, data=info)
    except Exception as e:
        return _json_response(False, error=str(e))


@router.get("/strategies/{symbol}")
async def run_strategies(request: Request, symbol: str, period: str = Query("1y")):
    try:
        kline_type = KLINE_TYPE_MAP.get(period, "daily")
        cache_key = f"strat:{symbol}:{period}:{kline_type}"
        cached = _cache_get(cache_key)
        if cached:
            return _json_response(True, data=cached)

        df = await request.app.state.fetcher.get_history(symbol, period, kline_type)
        if df.empty:
            return _json_response(False, error="No data for strategy analysis")

        results = request.app.state.composite_strategy.run_all(df)
        composite = request.app.state.composite_strategy.composite_score(results)

        output = {
            "composite": composite,
            "strategies": {},
        }
        for name, result in results.items():
            output["strategies"][name] = {
                "name": result.name,
                "description": result.description,
                "score": result.score,
                "params": result.params,
                "current_signal": {
                    "type": result.current_signal.signal_type.value if result.current_signal else "hold",
                    "strength": result.current_signal.strength if result.current_signal else 0,
                    "reason": result.current_signal.reason if result.current_signal else "",
                    "price": result.current_signal.price if result.current_signal else 0,
                    "stop_loss": result.current_signal.stop_loss if result.current_signal else 0,
                    "take_profit": result.current_signal.take_profit if result.current_signal else 0,
                    "position_pct": result.current_signal.position_pct if result.current_signal else 0,
                } if result.current_signal else None,
                "signal_count": len(result.signals),
            }

        _cache_set(cache_key, output, ttl=30)
        return _json_response(True, data=output)
    except Exception as e:
        logger.error(f"run_strategies error: {e}", exc_info=True)
        return _json_response(False, error=str(e))


@router.get("/backtest/{symbol}")
async def run_backtest(request: Request, symbol: str, period: str = Query("1y")):
    try:
        kline_type = KLINE_TYPE_MAP.get(period, "daily")
        cache_key = f"bt:{symbol}:{period}:{kline_type}"
        cached = _cache_get(cache_key)
        if cached:
            return _json_response(True, data=cached)

        df = await request.app.state.fetcher.get_history(symbol, period, kline_type)
        if df.empty or len(df) < 60:
            return _json_response(False, error="数据不足，至少需要60个交易日")

        results = request.app.state.backtest_engine.run_multi(request.app.state.composite_strategy.strategies, df)

        output = {}
        for name, result in results.items():
            output[name] = {
                "strategy_name": result.strategy_name,
                "total_return": result.total_return,
                "annual_return": result.annual_return,
                "sharpe_ratio": result.sharpe_ratio,
                "max_drawdown": result.max_drawdown,
                "win_rate": result.win_rate,
                "profit_factor": result.profit_factor,
                "total_trades": result.total_trades,
                "win_trades": result.win_trades,
                "loss_trades": result.loss_trades,
                "avg_profit": result.avg_profit,
                "avg_loss": result.avg_loss,
                "avg_hold_days": result.avg_hold_days,
                "benchmark_return": result.benchmark_return,
                "alpha": result.alpha,
                "beta": result.beta,
                "equity_curve": result.equity_curve[-200:] if result.equity_curve else [],
                "drawdown_curve": result.drawdown_curve[-200:] if result.drawdown_curve else [],
                "dates": result.dates[-200:] if result.dates else [],
            }

        _cache_set(cache_key, output, ttl=120)
        return _json_response(True, data=output)
    except Exception as e:
        logger.error(f"backtest error: {e}", exc_info=True)
        return _json_response(False, error=str(e))


@router.post("/backtest/run")
async def run_backtest_post(
    request: Request,
    symbol: str = Query(...),
    strategy_type: str = Query("momentum"),
    start_date: str = Query("2023-01-01"),
    end_date: str = Query("2024-01-01"),
    initial_capital: float = Query(100000),
    mode: str = Query("vectorized"),
):
    try:
        kline_type = "daily"
        cache_key = f"bt:run:{symbol}:{strategy_type}:{start_date}:{end_date}"
        cached = _cache_get(cache_key)
        if cached:
            return _json_response(True, data=cached)

        df = await request.app.state.fetcher.get_history(symbol, "1y", kline_type)
        if df.empty or len(df) < 30:
            return _json_response(False, error="数据不足，至少需要30个交易日")

        results = request.app.state.backtest_engine.run_multi(request.app.state.composite_strategy.strategies, df)

        best_name = list(results.keys())[0] if results else None
        best = results.get(best_name) if best_name else None

        if not best:
            return _json_response(False, error="回测无结果")

        output = {
            "strategy_name": best.strategy_name,
            "total_return": best.total_return,
            "annual_return": best.annual_return,
            "sharpe_ratio": best.sharpe_ratio,
            "max_drawdown": best.max_drawdown,
            "win_rate": best.win_rate,
            "profit_factor": best.profit_factor,
            "total_trades": best.total_trades,
            "win_trades": best.win_trades,
            "loss_trades": best.loss_trades,
            "avg_profit": best.avg_profit,
            "avg_loss": best.avg_loss,
            "avg_hold_days": best.avg_hold_days,
            "benchmark_return": best.benchmark_return,
            "alpha": best.alpha,
            "beta": best.beta,
            "equity_curve": best.equity_curve[-200:] if best.equity_curve else [],
            "drawdown_curve": best.drawdown_curve[-200:] if best.drawdown_curve else [],
            "dates": best.dates[-200:] if best.dates else [],
        }

        _cache_set(cache_key, output, ttl=120)
        return _json_response(True, data=output)
    except Exception as e:
        logger.error(f"backtest run error: {e}", exc_info=True)
        return _json_response(False, error=str(e))


@router.get("/sim/account")
async def sim_get_account(request: Request):
    try:
        data = request.app.state.sim_trading.get_account_info()
        return _json_response(True, data=data)
    except Exception as e:
        return _json_response(False, error=str(e))


@router.get("/sim/performance")
async def sim_get_performance(request: Request):
    try:
        data = request.app.state.sim_trading.get_performance()
        return _json_response(True, data=data)
    except Exception as e:
        return _json_response(False, error=str(e))


@router.get("/sim/positions")
async def sim_get_positions(request: Request):
    try:
        data = request.app.state.sim_trading.get_account_info()
        positions = data.get("positions", [])
        return _json_response(True, data=positions)
    except Exception as e:
        return _json_response(False, error=str(e))


@router.get("/sim/trades")
async def sim_get_trades(request: Request, limit: int = Query(50), page: int = Query(1)):
    try:
        data = request.app.state.sim_trading.get_trade_history(limit, page)
        return _json_response(True, data=data)
    except Exception as e:
        return _json_response(False, error=str(e))


@router.get("/sim/stats")
async def sim_get_stats(request: Request):
    try:
        data = request.app.state.sim_trading.get_detailed_stats()
        return _json_response(True, data=data)
    except Exception as e:
        return _json_response(False, error=str(e))


@router.post("/sim/buy")
async def sim_buy(request: Request):
    try:
        body = await request.json() if request.headers.get("content-type", "").startswith("application/json") else {}
        symbol = body.get("symbol", "")
        name = body.get("name", "")
        market = body.get("market", "A")
        price = body.get("price", 0)
        strategy = body.get("strategy", "manual")
        stop_loss = body.get("stop_loss", 0)
        take_profit = body.get("take_profit", 0)
        order_type = body.get("order_type", "market")
        shares = body.get("shares", 0) or body.get("quantity", 0)
        if not symbol:
            return _json_response(False, error="缺少symbol参数")
        if price <= 0:
            return _json_response(False, error="价格必须大于0")
        if not name:
            from core.stock_search import get_stock_name
            name = get_stock_name(symbol) or symbol
        result = request.app.state.sim_trading.execute_buy(
            symbol, name, market, price, strategy, stop_loss, take_profit,
            order_type=order_type, shares=shares,
        )
        if result["success"]:
            return _json_response(True, data=result)
        return _json_response(False, error=result.get("error", "买入失败"))
    except Exception as e:
        return _json_response(False, error=str(e))


@router.post("/sim/sell")
async def sim_sell(request: Request):
    try:
        body = await request.json() if request.headers.get("content-type", "").startswith("application/json") else {}
        symbol = body.get("symbol", "")
        price = body.get("price", 0)
        reason = body.get("reason", "manual")
        shares = body.get("shares", 0) or body.get("quantity", 0)
        if not symbol:
            return _json_response(False, error="缺少symbol参数")
        if price <= 0:
            return _json_response(False, error="价格必须大于0")
        result = request.app.state.sim_trading.execute_sell(symbol, price, reason, shares=shares)
        if result["success"]:
            return _json_response(True, data=result)
        return _json_response(False, error=result.get("error", "卖出失败"))
    except Exception as e:
        return _json_response(False, error=str(e))


@router.post("/sim/reset")
async def sim_reset(request: Request):
    try:
        result = request.app.state.sim_trading.reset_account()
        return _json_response(True, data=result)
    except Exception as e:
        return _json_response(False, error=str(e))


@router.post("/sim/watch")
async def sim_add_watch(request: Request, symbol: str = Query(...), name: str = Query("")):
    try:
        if not name:
            from core.stock_search import get_stock_name
            name = get_stock_name(symbol) or symbol
        result = request.app.state.sim_trading.add_to_watchlist(symbol, name)
        return _json_response(True, data=result)
    except Exception as e:
        return _json_response(False, error=str(e))


@router.delete("/sim/watch")
async def sim_remove_watch(request: Request, symbol: str = Query(...)):
    try:
        result = request.app.state.sim_trading.remove_from_watchlist(symbol)
        return _json_response(True, data=result)
    except Exception as e:
        return _json_response(False, error=str(e))


@router.get("/sim/watch")
async def sim_get_watchlist(request: Request):
    try:
        data = request.app.state.sim_trading.get_watchlist()
        return _json_response(True, data=data)
    except Exception as e:
        return _json_response(False, error=str(e))


@router.post("/sim/auto/start")
async def sim_auto_start(request: Request, strategy_name: str = Query(...)):
    try:
        result = request.app.state.sim_trading.start_auto_trading(strategy_name, request.app.state.fetcher)
        return _json_response(True, data=result)
    except Exception as e:
        return _json_response(False, error=str(e))


@router.post("/sim/auto/stop")
async def sim_auto_stop(request: Request):
    try:
        result = request.app.state.sim_trading.stop_auto_trading()
        return _json_response(True, data=result)
    except Exception as e:
        return _json_response(False, error=str(e))


@router.get("/sim/auto/status")
async def sim_auto_status(request: Request):
    try:
        data = request.app.state.sim_trading.get_auto_trading_status()
        return _json_response(True, data=data)
    except Exception as e:
        return _json_response(False, error=str(e))


@router.post("/sim/order")
async def sim_place_order(request: Request,
    symbol: str = Query(...),
    name: str = Query(""),
    market: str = Query("A"),
    action: str = Query(...),
    order_type: str = Query(...),
    price: float = Query(...),
    shares: int = Query(...),
    trigger_price: float = Query(0),
    strategy: str = Query("manual"),
):
    try:
        if not name:
            from core.stock_search import get_stock_name
            name = get_stock_name(symbol) or symbol
        result = request.app.state.sim_trading.place_order(
            symbol, name, market, action, order_type, price, shares,
            trigger_price=trigger_price, strategy=strategy,
        )
        if result["success"]:
            return _json_response(True, data=result)
        return _json_response(False, error=result.get("error", "下单失败"))
    except Exception as e:
        return _json_response(False, error=str(e))


@router.delete("/sim/order/{order_id}")
async def sim_cancel_order(request: Request, order_id: str):
    try:
        result = request.app.state.sim_trading.cancel_order(order_id)
        if result["success"]:
            return _json_response(True, data=result)
        return _json_response(False, error=result.get("error", "取消失败"))
    except Exception as e:
        return _json_response(False, error=str(e))


@router.get("/sim/orders")
async def sim_get_orders(request: Request):
    try:
        data = request.app.state.sim_trading.get_pending_orders()
        return _json_response(True, data=data)
    except Exception as e:
        return _json_response(False, error=str(e))


@router.post("/sim/refresh-prices")
async def sim_refresh_prices(request: Request):
    try:
        sim: SimulatedTrading = request.app.state.sim_trading
        fetcher: SmartDataFetcher = request.app.state.fetcher
        price_map = {}
        for symbol in list(sim._positions.keys()):
            try:
                rt = await fetcher.get_realtime(symbol)
                if rt and rt.get("price", 0) > 0:
                    price_map[symbol] = rt["price"]
            except Exception:
                pass
        updated = sim.update_position_prices(price_map)
        sim.check_pending_orders(price_map)
        account = sim.get_account_info()
        return _json_response(True, data={"updated": updated, "account": account})
    except Exception as e:
        return _json_response(False, error=str(e))


@router.get("/indicator-explain/{indicator}")
async def get_indicator_explanation(request: Request, indicator: str):
    explanations = {
        "macd": {
            "name": "MACD",
            "full_name": "移动平均收敛/发散指标",
            "category": "趋势指标",
            "definition": "MACD是通过计算两条不同周期的指数移动平均线(EMA)之间的差值来判断趋势方向和强度的技术指标。",
            "calculation": "DIF = EMA(12) - EMA(26)\nDEA = EMA(DIF, 9)\nMACD柱 = (DIF - DEA) × 2",
            "interpretation": {
                "golden_cross": "DIF上穿DEA，称为金叉，通常为买入信号",
                "death_cross": "DIF下穿DEA，称为死叉，通常为卖出信号",
                "above_zero": "DIF和DEA在零轴上方，表示多头趋势",
                "below_zero": "DIF和DEA在零轴下方，表示空头趋势",
                "divergence": "价格创新高但MACD未创新高，为顶背离；价格创新低但MACD未创新低，为底背离",
            },
            "tips": "零轴上方的金叉比零轴下方的金叉更可靠；MACD柱状图由绿转红表示动能转多。",
        },
        "rsi": {
            "name": "RSI",
            "full_name": "相对强弱指标",
            "category": "动量指标",
            "definition": "RSI衡量一段时间内价格上涨幅度与下跌幅度的比值，反映市场买卖力量的对比。",
            "calculation": "RSI = 100 - 100/(1+RS)\nRS = N日内平均上涨幅度 / N日内平均下跌幅度\n常用周期: 6、12、24",
            "interpretation": {
                "overbought": "RSI > 70，市场超买，可能面临回调",
                "oversold": "RSI < 30，市场超卖，可能出现反弹",
                "midline": "RSI > 50为多头区域，RSI < 50为空头区域",
                "divergence": "价格与RSI走势相反时，预示趋势可能反转",
            },
            "tips": "在强趋势中RSI可能长期处于超买/超卖区域，需结合其他指标确认。",
        },
        "kdj": {
            "name": "KDJ",
            "full_name": "随机指标",
            "category": "动量指标",
            "definition": "KDJ通过计算一定周期内收盘价在最高价和最低价之间的位置来判断超买超卖状态。",
            "calculation": "RSV = (收盘价-N日最低价)/(N日最高价-N日最低价)×100\nK = 2/3×前日K + 1/3×RSV\nD = 2/3×前日D + 1/3×K\nJ = 3K - 2D",
            "interpretation": {
                "overbought": "K>80, D>80, J>100为超买区域",
                "oversold": "K<20, D<20, J<0为超卖区域",
                "golden_cross": "K线上穿D线为金叉，买入信号",
                "death_cross": "K线下穿D线为死叉，卖出信号",
                "j_extreme": "J值>100或<0时，表示短期过度偏离，反转概率增大",
            },
            "tips": "J值对价格变化最敏感，适合短线操作参考；KDJ在震荡市中效果较好，趋势市中容易钝化。",
        },
        "boll": {
            "name": "BOLL",
            "full_name": "布林带",
            "category": "波动率指标",
            "definition": "布林带由中轨(移动平均线)和上下两条标准差通道组成，反映价格波动的区间和趋势。",
            "calculation": "中轨 = MA(N)\n上轨 = 中轨 + K×标准差\n下轨 = 中轨 - K×标准差\n常用参数: N=20, K=2",
            "interpretation": {
                "squeeze": "布林带收窄，表示波动率降低，可能即将出现大幅突破",
                "breakout": "价格突破上轨为强势，跌破下轨为弱势",
                "walk_band": "价格沿上轨运行为强势上涨，沿下轨运行为强势下跌",
                "mean_reversion": "价格从上下轨回归中轨的概率较大",
            },
            "tips": "布林带收窄后的突破方向通常代表后续趋势方向；带宽指标可用于量化收窄程度。",
        },
        "ma": {
            "name": "MA",
            "full_name": "移动平均线",
            "category": "趋势指标",
            "definition": "移动平均线是将一定周期内的收盘价取平均值连成的线，用于判断趋势方向和支撑压力位。",
            "calculation": "MA(N) = (C1+C2+...+CN)/N\n常用周期: 5、10、20、60、120",
            "interpretation": {
                "golden_cross": "短期均线上穿长期均线，为金叉买入信号",
                "death_cross": "短期均线下穿长期均线，为死叉卖出信号",
                "support": "均线向上时对价格有支撑作用",
                "resistance": "均线向下时对价格有压力作用",
                "alignment": "均线多头排列(5>10>20>60)为强势，空头排列为弱势",
            },
            "tips": "均线周期越长越稳定但越滞后；多条均线配合使用效果更好。",
        },
        "supertrend": {
            "name": "SuperTrend",
            "full_name": "超级趋势指标",
            "category": "趋势指标",
            "definition": "SuperTrend基于ATR计算的趋势跟踪指标，通过价格与趋势线的关系判断多空方向。",
            "calculation": "上轨 = (最高价+最低价)/2 + 乘数×ATR\n下轨 = (最高价+最低价)/2 - 乘数×ATR\n常用参数: 周期=10, 乘数=3",
            "interpretation": {
                "bullish": "价格在SuperTrend上方，趋势线为绿色，为多头",
                "bearish": "价格在SuperTrend下方，趋势线为红色，为空头",
                "flip": "趋势线由红转绿为买入信号，由绿转红为卖出信号",
            },
            "tips": "SuperTrend在趋势市中表现优秀，震荡市中可能频繁发出假信号。",
        },
        "cci": {
            "name": "CCI",
            "full_name": "商品通道指标",
            "category": "动量指标",
            "definition": "CCI衡量价格偏离其统计平均值的程度，用于判断超买超卖和趋势强度。",
            "calculation": "TP = (最高价+最低价+收盘价)/3\nCCI = (TP-MA)/(0.015×MD)\nMA=TP的N日简单平均，MD=平均偏差",
            "interpretation": {
                "above_100": "CCI>100，价格异常偏高，处于强势上涨",
                "below_minus100": "CCI<-100，价格异常偏低，处于强势下跌",
                "normal": "CCI在-100到100之间，价格处于正常波动范围",
            },
            "tips": "CCI没有上限和下限，极端值可能持续较长时间。",
        },
        "atr": {
            "name": "ATR",
            "full_name": "平均真实波幅",
            "category": "波动率指标",
            "definition": "ATR衡量一定周期内价格波动的平均幅度，反映市场的波动性。",
            "calculation": "TR = max(最高价-最低价, |最高价-前收|, |最低价-前收|)\nATR = TR的N日移动平均\n常用周期: 14",
            "interpretation": {
                "high_atr": "ATR较高，市场波动剧烈，风险和机会并存",
                "low_atr": "ATR较低，市场波动平缓，可能酝酿突破",
                "use": "常用于设置止损位(ATR的1.5-3倍)和仓位管理",
            },
            "tips": "ATR不判断方向，只衡量波动幅度；可用于动态调整止损止盈距离。",
        },
        "volume_ratio": {
            "name": "量比",
            "full_name": "成交量比率",
            "category": "成交量指标",
            "definition": "量比是当日即时成交量与过去5日平均成交量的比值，反映当前成交活跃程度。",
            "calculation": "量比 = 当前累计成交量 / (过去5日平均同时段成交量)",
            "interpretation": {
                "high": "量比>1.5，成交活跃，关注度高",
                "low": "量比<0.7，成交清淡，市场关注度低",
                "normal": "量比在0.7-1.5之间，成交正常",
            },
            "tips": "量价配合分析更有效：放量上涨为健康上涨，放量下跌需警惕。",
        },
    }
    data = explanations.get(indicator.lower())
    if data:
        return _json_response(True, data=data)
    return _json_response(False, error=f"未找到指标 {indicator} 的说明")


def _df_to_chart(df, kline_type: str = "daily") -> list:
    is_intraday = kline_type == "intraday" or (
        len(df) > 0 and "date" in df.columns
        and hasattr(df["date"].iloc[0], "hour")
        and df["date"].iloc[0].hour > 0
    )

    dates = df["date"].values
    times = []
    for d in dates:
        ts = pd.Timestamp(d)
        if is_intraday:
            times.append(int(ts.timestamp()))
        else:
            times.append(str(ts.date()))

    opens = df["open"].values.astype(float)
    highs = df["high"].values.astype(float)
    lows = df["low"].values.astype(float)
    closes = df["close"].values.astype(float)

    has_volume = "volume" in df.columns
    volumes = df["volume"].values.astype(float) if has_volume else None

    result = []
    for i in range(len(df)):
        item = {
            "time": times[i],
            "open": round(opens[i], 2),
            "high": round(highs[i], 2),
            "low": round(lows[i], 2),
            "close": round(closes[i], 2),
        }
        if has_volume and volumes is not None:
            vol = volumes[i]
            if not np.isnan(vol):
                item["volume"] = int(vol)
        result.append(item)
    return result
