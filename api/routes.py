import asyncio
import json
import logging
import time
from collections import OrderedDict
from typing import Optional

from fastapi import APIRouter, Query, Request, WebSocket, WebSocketDisconnect

from core.data_fetcher import SmartDataFetcher
from core.database import get_db
from core.stock_search import search_stocks, get_stock_info, get_stock_name, get_all_industries
from core.market_data import get_market_page, get_realtime_quotes, get_stock_list
from core.simulated_trading import SimulatedTrading
from core.strategies import STRATEGY_REGISTRY
from core.backtest import run_backtest

logger = logging.getLogger(__name__)

router = APIRouter()

_MAX_CACHE = 200
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
    while len(_cache) > _MAX_CACHE:
        _cache.popitem(last=False)


def _ok(data=None, error: str = ""):
    return {"success": not error, "data": data, "error": error}


@router.get("/search")
async def search_stock(q: str = Query(..., min_length=1), limit: int = Query(10), market: Optional[str] = None):
    try:
        return _ok(search_stocks(q, limit=limit, market=market))
    except Exception as e:
        return _ok(error=str(e))


@router.get("/realtime")
async def realtime(request: Request, symbol: str = Query(...)):
    try:
        key = f"rt:{symbol}"
        cached = _cache_get(key)
        if cached:
            return _ok(cached)
        data = await request.app.state.fetcher.get_realtime(symbol)
        if not data:
            return _ok(error="No data")
        _cache_set(key, data, ttl=8)
        return _ok(data)
    except Exception as e:
        return _ok(error=str(e))


@router.get("/kline")
async def kline(
    request: Request,
    symbol: str = Query(...),
    period: str = Query("daily"),
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = Query(500),
):
    try:
        key = f"kl:{symbol}:{period}:{start_date}:{end_date}:{limit}"
        cached = _cache_get(key)
        if cached:
            return _ok(cached)
        data = await request.app.state.fetcher.get_kline(
            symbol, period=period, start_date=start_date, end_date=end_date, limit=limit
        )
        if data is not None:
            _cache_set(key, data, ttl=30)
            return _ok(data)
        return _ok(error="No data")
    except Exception as e:
        return _ok(error=str(e))


@router.get("/market/overview")
async def market_overview(request: Request):
    try:
        key = "mkt:overview"
        cached = _cache_get(key)
        if cached:
            return _ok(cached)
        data = await request.app.state.fetcher.get_market_overview()
        _cache_set(key, data, ttl=15)
        return _ok(data)
    except Exception as e:
        return _ok(error=str(e))


@router.get("/market/hot")
async def hot_stocks(request: Request, limit: int = Query(20)):
    try:
        key = f"mkt:hot:{limit}"
        cached = _cache_get(key)
        if cached:
            return _ok(cached)
        data = await request.app.state.fetcher.get_hot_stocks(limit=limit)
        _cache_set(key, data, ttl=30)
        return _ok(data)
    except Exception as e:
        return _ok(error=str(e))


@router.get("/market/temperature")
async def market_temperature(request: Request):
    try:
        key = "mkt:temp"
        cached = _cache_get(key)
        if cached:
            return _ok(cached)
        data = await request.app.state.fetcher.get_market_temperature()
        _cache_set(key, data, ttl=60)
        return _ok(data)
    except Exception as e:
        return _ok(error=str(e))


@router.get("/market/northbound")
async def northbound_flow(request: Request, limit: int = Query(30)):
    try:
        key = f"mkt:nb:{limit}"
        cached = _cache_get(key)
        if cached:
            return _ok(cached)
        data = await request.app.state.fetcher.get_northbound_flow(limit=limit)
        _cache_set(key, data, ttl=300)
        return _ok(data)
    except Exception as e:
        return _ok(error=str(e))


@router.get("/market/sectors")
async def market_sectors(request: Request):
    try:
        key = "mkt:sectors"
        cached = _cache_get(key)
        if cached:
            return _ok(cached)
        data = await request.app.state.fetcher.get_sector_data()
        _cache_set(key, data, ttl=120)
        return _ok(data)
    except Exception as e:
        return _ok(error=str(e))


@router.get("/market/list")
async def market_list(
    market: str = Query("A"),
    page: int = Query(1),
    page_size: int = Query(50),
    sort: str = Query("pct"),
    asc: bool = Query(False),
    sector: Optional[str] = None,
    search: Optional[str] = None,
):
    try:
        data = get_market_page(market, page=page, page_size=page_size, sort=sort, asc=asc, sector=sector, search=search)
        return _ok(data)
    except Exception as e:
        return _ok(error=str(e))


@router.get("/market/indices")
async def market_indices(request: Request):
    try:
        key = "mkt:indices"
        cached = _cache_get(key)
        if cached:
            return _ok(cached)
        data = await request.app.state.fetcher.get_market_overview()
        indices = data.get("indices", []) if isinstance(data, dict) else []
        _cache_set(key, indices, ttl=15)
        return _ok(indices)
    except Exception as e:
        return _ok(error=str(e))


@router.get("/stock/info")
async def stock_info(symbol: str = Query(...)):
    try:
        info = get_stock_info(symbol)
        if info:
            return _ok(info)
        return _ok(error="Not found")
    except Exception as e:
        return _ok(error=str(e))


@router.get("/stock/financial")
async def stock_financial(request: Request, symbol: str = Query(...)):
    try:
        key = f"fin:{symbol}"
        cached = _cache_get(key)
        if cached:
            return _ok(cached)
        data = await request.app.state.fetcher.get_financial_data(symbol)
        _cache_set(key, data, ttl=3600)
        return _ok(data)
    except Exception as e:
        return _ok(error=str(e))


@router.get("/stock/indicators")
async def stock_indicators(
    request: Request,
    symbol: str = Query(...),
    period: str = Query("daily"),
    limit: int = Query(500),
):
    try:
        key = f"ind:{symbol}:{period}:{limit}"
        cached = _cache_get(key)
        if cached:
            return _ok(cached)
        kline_data = await request.app.state.fetcher.get_kline(symbol, period=period, limit=limit)
        if not kline_data:
            return _ok(error="No kline data")
        from core.indicators import calc_all_indicators
        result = calc_all_indicators(kline_data)
        _cache_set(key, result, ttl=30)
        return _ok(result)
    except Exception as e:
        return _ok(error=str(e))


@router.get("/industries")
async def industries():
    try:
        return _ok(get_all_industries())
    except Exception as e:
        return _ok(error=str(e))


@router.get("/strategy/list")
async def strategy_list():
    try:
        strategies = []
        for name, cls in STRATEGY_REGISTRY.items():
            strategies.append({
                "name": name,
                "description": cls.__doc__ or "",
                "params": getattr(cls, "PARAMS", {}),
            })
        return _ok(strategies)
    except Exception as e:
        return _ok(error=str(e))


@router.post("/strategy/backtest")
async def strategy_backtest(request: Request):
    try:
        body = await request.json()
        symbol = body.get("symbol", "600519")
        strategy_name = body.get("strategy", "ma_cross")
        start_date = body.get("start_date", "2024-01-01")
        end_date = body.get("end_date", "2025-12-31")
        initial_capital = body.get("initial_capital", 1000000)
        params = body.get("params", {})

        result = await asyncio.to_thread(
            run_backtest,
            symbol=symbol,
            strategy_name=strategy_name,
            start_date=start_date,
            end_date=end_date,
            initial_capital=initial_capital,
            params=params,
        )
        return _ok(result)
    except Exception as e:
        logger.error(f"Backtest error: {e}")
        return _ok(error=str(e))


@router.get("/strategy/signals")
async def strategy_signals(
    request: Request,
    symbol: str = Query(...),
    strategy_name: str = Query("ma_cross"),
    period: str = Query("daily"),
    limit: int = Query(200),
    params: Optional[str] = None,
):
    try:
        key = f"sig:{symbol}:{strategy_name}:{period}:{limit}:{params}"
        cached = _cache_get(key)
        if cached:
            return _ok(cached)

        kline_data = await request.app.state.fetcher.get_kline(symbol, period=period, limit=limit)
        if not kline_data:
            return _ok(error="No kline data")

        strategy_params = json.loads(params) if params else {}
        if strategy_name not in STRATEGY_REGISTRY:
            return _ok(error=f"Strategy {strategy_name} not found")

        strategy_cls = STRATEGY_REGISTRY[strategy_name]
        strategy = strategy_cls(**strategy_params)
        signals = strategy.generate_signals(kline_data)

        _cache_set(key, signals, ttl=30)
        return _ok(signals)
    except Exception as e:
        return _ok(error=str(e))


@router.get("/portfolio/summary")
async def portfolio_summary(request: Request):
    try:
        trading: SimulatedTrading = request.app.state.trading
        summary = await asyncio.to_thread(trading.get_account_info)
        return _ok(summary)
    except Exception as e:
        return _ok(error=str(e))


@router.get("/portfolio/positions")
async def portfolio_positions(request: Request):
    try:
        trading: SimulatedTrading = request.app.state.trading
        info = await asyncio.to_thread(trading.get_account_info)
        positions = info.get("positions", [])
        return _ok(positions)
    except Exception as e:
        return _ok(error=str(e))


@router.get("/portfolio/trades")
async def portfolio_trades(request: Request, symbol: Optional[str] = None, limit: int = Query(100)):
    try:
        trading: SimulatedTrading = request.app.state.trading
        result = await asyncio.to_thread(trading.get_trade_history, limit=limit)
        trades = result.get("trades", [])
        if symbol:
            trades = [t for t in trades if t.get("symbol") == symbol]
        return _ok(trades)
    except Exception as e:
        return _ok(error=str(e))


@router.post("/portfolio/buy")
async def portfolio_buy(request: Request):
    try:
        body = await request.json()
        symbol = body.get("symbol", "")
        quantity = int(body.get("quantity", 0))
        price = float(body.get("price", 0))
        if not symbol or quantity <= 0:
            return _ok(error="Invalid params")

        trading: SimulatedTrading = request.app.state.trading
        name = get_stock_name(symbol) or symbol
        market = "A"
        if symbol.isalpha():
            market = "US"
        elif symbol.startswith("0") and len(symbol) == 5:
            market = "HK"
        result = await asyncio.to_thread(trading.execute_buy, symbol=symbol, name=name, market=market, price=price, shares=quantity)
        return _ok(result)
    except Exception as e:
        return _ok(error=str(e))


@router.post("/portfolio/sell")
async def portfolio_sell(request: Request):
    try:
        body = await request.json()
        symbol = body.get("symbol", "")
        quantity = int(body.get("quantity", 0))
        price = float(body.get("price", 0))
        if not symbol or quantity <= 0:
            return _ok(error="Invalid params")

        trading: SimulatedTrading = request.app.state.trading
        result = await asyncio.to_thread(trading.execute_sell, symbol=symbol, price=price, shares=quantity)
        return _ok(result)
    except Exception as e:
        return _ok(error=str(e))


@router.post("/portfolio/reset")
async def portfolio_reset(request: Request):
    try:
        trading: SimulatedTrading = request.app.state.trading
        result = await asyncio.to_thread(trading.reset_account)
        return _ok(result)
    except Exception as e:
        return _ok(error=str(e))


@router.get("/watchlist")
async def get_watchlist(request: Request):
    try:
        db = get_db()
        wl = db.get_config("watchlist", [])
        if not wl:
            wl = ["600519", "000858", "300750", "002594", "601318", "000333"]
        results = []
        for code in wl:
            info = get_stock_info(code)
            if info:
                results.append(info)
        return _ok(results)
    except Exception as e:
        return _ok(error=str(e))


@router.post("/watchlist/add")
async def watchlist_add(request: Request):
    try:
        body = await request.json()
        symbol = body.get("symbol", "")
        if not symbol:
            return _ok(error="No symbol")
        db = get_db()
        wl = db.get_config("watchlist", [])
        if symbol not in wl:
            wl.append(symbol)
            db.set_config("watchlist", wl)
        return _ok(wl)
    except Exception as e:
        return _ok(error=str(e))


@router.post("/watchlist/remove")
async def watchlist_remove(request: Request):
    try:
        body = await request.json()
        symbol = body.get("symbol", "")
        if not symbol:
            return _ok(error="No symbol")
        db = get_db()
        wl = db.get_config("watchlist", [])
        if symbol in wl:
            wl.remove(symbol)
            db.set_config("watchlist", wl)
        return _ok(wl)
    except Exception as e:
        return _ok(error=str(e))


@router.get("/health")
async def health():
    return {"status": "ok", "ts": time.time()}


class ConnectionManager:
    def __init__(self):
        self.active: list[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active.append(ws)

    def disconnect(self, ws: WebSocket):
        if ws in self.active:
            self.active.remove(ws)

    async def broadcast(self, data: dict):
        dead = []
        for ws in self.active:
            try:
                await ws.send_json(data)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)


_manager = ConnectionManager()


@router.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await _manager.connect(ws)
    try:
        while True:
            raw = await ws.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                continue

            msg_type = msg.get("type", "")

            if msg_type == "subscribe":
                symbols = msg.get("symbols", [])
                await ws.send_json({"type": "subscribed", "symbols": symbols})
            elif msg_type == "ping":
                await ws.send_json({"type": "pong", "ts": time.time()})
    except WebSocketDisconnect:
        _manager.disconnect(ws)
    except Exception:
        _manager.disconnect(ws)


async def push_realtime_data(fetcher: SmartDataFetcher):
    while True:
        try:
            if not _manager.active:
                await asyncio.sleep(5)
                continue

            db = get_db()
            wl = db.get_config("watchlist", [])
            if not wl:
                wl = ["600519", "000858", "300750"]

            for symbol in wl[:20]:
                try:
                    data = await fetcher.get_realtime(symbol)
                    if data:
                        await _manager.broadcast({
                            "type": "quote",
                            "symbol": symbol,
                            "data": data,
                        })
                except Exception:
                    pass

            await asyncio.sleep(3)
        except Exception as e:
            logger.error(f"WS push error: {e}")
            await asyncio.sleep(10)
