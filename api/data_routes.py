import asyncio
import logging
from typing import Optional

from fastapi import APIRouter, Query, Request

from core.data_infra.tick_store import TickStore, DataType
from core.data_infra.data_adapter import UnifiedDataAdapter
from core.data_infra.realtime_stream import RealtimeStreamManager
from core.data_infra.history_manager import HistoryDataManager, AdjustType, CorporateAction
from core.data_infra.alt_data import AltDataPipeline

logger = logging.getLogger(__name__)
data_router = APIRouter(prefix="/data", tags=["数据基础设施"])


def _resp(success: bool, data=None, msg: str = ""):
    return {"code": 0 if success else 1, "data": data, "msg": msg}


@data_router.get("/tick/symbols")
async def list_tick_symbols(request: Request):
    symbols = request.app.state.tick_store.get_symbols()
    return _resp(True, data=symbols)


@data_router.get("/tick/info/{symbol}")
async def get_tick_info(request: Request, symbol: str, data_type: str = Query("bar")):
    try:
        dt = DataType(data_type)
        info = request.app.state.tick_store.get_data_info(symbol, dt)
        return _resp(True, data=info)
    except ValueError:
        return _resp(False, msg=f"不支持的数据类型: {data_type}")


@data_router.get("/tick/read/{symbol}")
async def read_tick_data(
    request: Request,
    symbol: str,
    data_type: str = Query("bar"),
    start: Optional[str] = Query(None),
    end: Optional[str] = Query(None),
    limit: Optional[int] = Query(None),
):
    try:
        dt = DataType(data_type)
        df = request.app.state.tick_store.read_ticks(symbol, dt, start, end, limit)
        if df.empty:
            return _resp(True, data=[])
        data = df.to_dict("records")
        for item in data:
            for k, v in item.items():
                if hasattr(v, "item"):
                    item[k] = v.item()
        return _resp(True, data=data)
    except ValueError:
        return _resp(False, msg=f"不支持的数据类型: {data_type}")


@data_router.delete("/tick/delete/{symbol}")
async def delete_tick_data(request: Request, symbol: str, data_type: str = Query("bar"), date: Optional[str] = Query(None)):
    try:
        dt = DataType(data_type)
        async with request.app.state.write_lock:
            request.app.state.tick_store.delete_data(symbol, dt, date)
        return _resp(True, msg="删除成功")
    except ValueError:
        return _resp(False, msg=f"不支持的数据类型: {data_type}")


@data_router.get("/adapter/health")
async def get_adapter_health(request: Request):
    health = request.app.state.data_adapter.get_health_status()
    return _resp(True, data=health)


@data_router.post("/adapter/health-check")
async def run_health_check(request: Request):
    results = await request.app.state.data_adapter.run_health_check()
    return _resp(True, data=results)


@data_router.get("/adapter/info")
async def get_adapter_info(request: Request):
    info = request.app.state.data_adapter.get_adapter_info()
    return _resp(True, data=info)


@data_router.get("/adapter/realtime/{symbol}")
async def adapter_fetch_realtime(request: Request, symbol: str, market: str = Query("A")):
    result = await request.app.state.data_adapter.fetch_realtime(symbol, market)
    if result:
        return _resp(True, data=result)
    return _resp(False, msg="所有数据源均不可用")


@data_router.get("/adapter/history/{symbol}")
async def adapter_fetch_history(
    request: Request,
    symbol: str, market: str = Query("A"),
    start: str = Query("20240101"), end: str = Query("20261231"),
):
    result = await request.app.state.data_adapter.fetch_history(symbol, market, start, end)
    if result is not None and not result.empty:
        data = result.to_dict("records")
        for item in data:
            for k, v in item.items():
                if hasattr(v, "item"):
                    item[k] = v.item()
                elif hasattr(v, "strftime"):
                    item[k] = str(v)
        return _resp(True, data=data)
    return _resp(False, msg="所有数据源均不可用")


@data_router.get("/stream/status")
async def get_stream_status(request: Request):
    status = request.app.state.stream_manager.get_status()
    return _resp(True, data=status)


@data_router.post("/stream/subscribe/{symbol}")
async def stream_subscribe(request: Request, symbol: str):
    async with request.app.state.write_lock:
        success = request.app.state.stream_manager.subscribe(symbol)
    if success:
        return _resp(True, msg=f"已订阅 {symbol}")
    return _resp(False, msg="订阅失败，可能已达上限")


@data_router.delete("/stream/unsubscribe/{symbol}")
async def stream_unsubscribe(request: Request, symbol: str):
    async with request.app.state.write_lock:
        request.app.state.stream_manager.unsubscribe(symbol)
    return _resp(True, msg=f"已取消订阅 {symbol}")


@data_router.get("/stream/subscriptions")
async def get_stream_subscriptions(request: Request):
    subs = request.app.state.stream_manager.get_all_subscriptions()
    return _resp(True, data=subs)


@data_router.post("/stream/start")
async def start_stream(request: Request):
    await request.app.state.stream_manager.start()
    return _resp(True, msg="实时流已启动")


@data_router.post("/stream/stop")
async def stop_stream(request: Request):
    await request.app.state.stream_manager.stop()
    return _resp(True, msg="实时流已停止")


@data_router.get("/history/symbols")
async def list_history_symbols(request: Request):
    symbols = request.app.state.history_manager.list_symbols()
    return _resp(True, data=symbols)


@data_router.get("/history/load/{symbol}")
async def load_history(request: Request, symbol: str, adjust: str = Query("forward")):
    try:
        at = AdjustType(adjust)
        df = request.app.state.history_manager.load_history(symbol, at)
        if df.empty:
            return _resp(True, data=[])
        data = df.to_dict("records")
        for item in data:
            for k, v in item.items():
                if hasattr(v, "item"):
                    item[k] = v.item()
                elif hasattr(v, "strftime"):
                    item[k] = str(v)
        return _resp(True, data=data)
    except ValueError:
        return _resp(False, msg=f"不支持的复权类型: {adjust}")


@data_router.get("/history/meta/{symbol}")
async def get_history_meta(request: Request, symbol: str):
    meta = request.app.state.history_manager.get_meta(symbol)
    if meta:
        return _resp(True, data=meta)
    return _resp(False, msg="未找到元数据")


@data_router.get("/history/actions/{symbol}")
async def get_corporate_actions(request: Request, symbol: str):
    actions = request.app.state.history_manager.get_corporate_actions(symbol)
    return _resp(True, data=actions)


@data_router.post("/history/actions")
async def add_corporate_action(
    request: Request,
    symbol: str = Query(...),
    date: str = Query(...),
    action_type: str = Query(...),
    dividend_per_share: float = Query(0),
    split_ratio: float = Query(1),
    bonus_ratio: float = Query(0),
    description: str = Query(""),
):
    action = CorporateAction(
        symbol=symbol, date=date, action_type=action_type,
        dividend_per_share=dividend_per_share, split_ratio=split_ratio,
        bonus_ratio=bonus_ratio, description=description,
    )
    async with request.app.state.write_lock:
        request.app.state.history_manager.add_corporate_action(action)
    return _resp(True, msg="公司行为已添加")


@data_router.get("/history/factors/{symbol}")
async def get_adjustment_factors(request: Request, symbol: str):
    factors = request.app.state.history_manager.get_adjustment_factors(symbol)
    data = []
    for f in factors:
        d = {"date": f.date, "factor": f.factor, "cumulative_factor": f.cumulative_factor}
        data.append(d)
    return _resp(True, data=data)


@data_router.get("/history/leak-check/{symbol}")
async def check_future_leak(request: Request, symbol: str):
    df = request.app.state.history_manager.load_history(symbol)
    leaks = request.app.state.history_manager.check_future_leak(symbol, df)
    return _resp(True, data=leaks)


@data_router.get("/alt/news/{symbol}")
async def get_news_sentiment(request: Request, symbol: str, limit: int = Query(20)):
    data = await request.app.state.alt_pipeline.get_news_sentiment(symbol, limit)
    return _resp(True, data=data)


@data_router.get("/alt/northbound")
async def get_northbound_flow(request: Request):
    data = await request.app.state.alt_pipeline.get_northbound_flow()
    return _resp(True, data=data)


@data_router.get("/alt/social/{symbol}")
async def get_social_heat(request: Request, symbol: str):
    data = await request.app.state.alt_pipeline.get_social_heat(symbol)
    if data:
        return _resp(True, data=data)
    return _resp(False, msg="未获取到社交热度数据")


@data_router.post("/alt/social/batch")
async def get_social_heat_batch(request: Request, symbols: str = Query(..., description="逗号分隔的股票代码")):
    symbol_list = [s.strip() for s in symbols.split(",") if s.strip()]
    data = await request.app.state.alt_pipeline.get_social_heat_batch(symbol_list)
    return _resp(True, data=data)


@data_router.get("/alt/comprehensive/{symbol}")
async def get_comprehensive_alt_data(request: Request, symbol: str):
    data = await request.app.state.alt_pipeline.get_comprehensive_alt_data(symbol)
    return _resp(True, data=data)
