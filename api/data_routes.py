import asyncio
import logging
from typing import Optional

from fastapi import APIRouter, Query

from core.data_infra.tick_store import TickStore, DataType
from core.data_infra.data_adapter import UnifiedDataAdapter
from core.data_infra.realtime_stream import RealtimeStreamManager
from core.data_infra.history_manager import HistoryDataManager, AdjustType, CorporateAction
from core.data_infra.alt_data import AltDataPipeline

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/data", tags=["数据基础设施"])

tick_store = TickStore()
data_adapter = UnifiedDataAdapter()
stream_manager = RealtimeStreamManager()
history_manager = HistoryDataManager()
alt_pipeline = AltDataPipeline()


def _resp(success: bool, data=None, msg: str = ""):
    return {"code": 0 if success else 1, "data": data, "msg": msg}


# ==================== 01 Tick数据存储与回放 ====================

@router.get("/tick/symbols")
async def list_tick_symbols():
    symbols = tick_store.get_symbols()
    return _resp(True, data=symbols)


@router.get("/tick/info/{symbol}")
async def get_tick_info(symbol: str, data_type: str = Query("bar")):
    try:
        dt = DataType(data_type)
        info = tick_store.get_data_info(symbol, dt)
        return _resp(True, data=info)
    except ValueError:
        return _resp(False, msg=f"不支持的数据类型: {data_type}")


@router.get("/tick/read/{symbol}")
async def read_tick_data(
    symbol: str,
    data_type: str = Query("bar"),
    start: Optional[str] = Query(None),
    end: Optional[str] = Query(None),
    limit: Optional[int] = Query(None),
):
    try:
        dt = DataType(data_type)
        df = tick_store.read_ticks(symbol, dt, start, end, limit)
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


@router.delete("/tick/delete/{symbol}")
async def delete_tick_data(symbol: str, data_type: str = Query("bar"), date: Optional[str] = Query(None)):
    try:
        dt = DataType(data_type)
        tick_store.delete_data(symbol, dt, date)
        return _resp(True, msg="删除成功")
    except ValueError:
        return _resp(False, msg=f"不支持的数据类型: {data_type}")


# ==================== 02 统一数据适配层 ====================

@router.get("/adapter/health")
async def get_adapter_health():
    health = data_adapter.get_health_status()
    return _resp(True, data=health)


@router.post("/adapter/health-check")
async def run_health_check():
    results = await data_adapter.run_health_check()
    return _resp(True, data=results)


@router.get("/adapter/info")
async def get_adapter_info():
    info = data_adapter.get_adapter_info()
    return _resp(True, data=info)


@router.get("/adapter/realtime/{symbol}")
async def adapter_fetch_realtime(symbol: str, market: str = Query("A")):
    result = await data_adapter.fetch_realtime(symbol, market)
    if result:
        return _resp(True, data=result)
    return _resp(False, msg="所有数据源均不可用")


@router.get("/adapter/history/{symbol}")
async def adapter_fetch_history(
    symbol: str, market: str = Query("A"),
    start: str = Query("20240101"), end: str = Query("20261231"),
):
    result = await data_adapter.fetch_history(symbol, market, start, end)
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


# ==================== 03 实时行情流处理 ====================

@router.get("/stream/status")
async def get_stream_status():
    status = stream_manager.get_status()
    return _resp(True, data=status)


@router.post("/stream/subscribe/{symbol}")
async def stream_subscribe(symbol: str):
    success = stream_manager.subscribe(symbol)
    if success:
        return _resp(True, msg=f"已订阅 {symbol}")
    return _resp(False, msg="订阅失败，可能已达上限")


@router.delete("/stream/unsubscribe/{symbol}")
async def stream_unsubscribe(symbol: str):
    stream_manager.unsubscribe(symbol)
    return _resp(True, msg=f"已取消订阅 {symbol}")


@router.get("/stream/subscriptions")
async def get_stream_subscriptions():
    subs = stream_manager.get_all_subscriptions()
    return _resp(True, data=subs)


@router.post("/stream/start")
async def start_stream():
    await stream_manager.start()
    return _resp(True, msg="实时流已启动")


@router.post("/stream/stop")
async def stop_stream():
    await stream_manager.stop()
    return _resp(True, msg="实时流已停止")


# ==================== 04 历史数据管理 ====================

@router.get("/history/symbols")
async def list_history_symbols():
    symbols = history_manager.list_symbols()
    return _resp(True, data=symbols)


@router.get("/history/load/{symbol}")
async def load_history(symbol: str, adjust: str = Query("forward")):
    try:
        at = AdjustType(adjust)
        df = history_manager.load_history(symbol, at)
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


@router.get("/history/meta/{symbol}")
async def get_history_meta(symbol: str):
    meta = history_manager.get_meta(symbol)
    if meta:
        return _resp(True, data=meta)
    return _resp(False, msg="未找到元数据")


@router.get("/history/actions/{symbol}")
async def get_corporate_actions(symbol: str):
    actions = history_manager.get_corporate_actions(symbol)
    return _resp(True, data=actions)


@router.post("/history/actions")
async def add_corporate_action(
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
    history_manager.add_corporate_action(action)
    return _resp(True, msg="公司行为已添加")


@router.get("/history/factors/{symbol}")
async def get_adjustment_factors(symbol: str):
    factors = history_manager.get_adjustment_factors(symbol)
    data = []
    for f in factors:
        d = {"date": f.date, "factor": f.factor, "cumulative_factor": f.cumulative_factor}
        data.append(d)
    return _resp(True, data=data)


@router.get("/history/leak-check/{symbol}")
async def check_future_leak(symbol: str):
    df = history_manager.load_history(symbol)
    leaks = history_manager.check_future_leak(symbol, df)
    return _resp(True, data=leaks)


# ==================== 05 另类数据集成 ====================

@router.get("/alt/news/{symbol}")
async def get_news_sentiment(symbol: str, limit: int = Query(20)):
    data = await alt_pipeline.get_news_sentiment(symbol, limit)
    return _resp(True, data=data)


@router.get("/alt/northbound")
async def get_northbound_flow():
    data = await alt_pipeline.get_northbound_flow()
    return _resp(True, data=data)


@router.get("/alt/social/{symbol}")
async def get_social_heat(symbol: str):
    data = await alt_pipeline.get_social_heat(symbol)
    if data:
        return _resp(True, data=data)
    return _resp(False, msg="未获取到社交热度数据")


@router.post("/alt/social/batch")
async def get_social_heat_batch(symbols: str = Query(..., description="逗号分隔的股票代码")):
    symbol_list = [s.strip() for s in symbols.split(",") if s.strip()]
    data = await alt_pipeline.get_social_heat_batch(symbol_list)
    return _resp(True, data=data)


@router.get("/alt/comprehensive/{symbol}")
async def get_comprehensive_alt_data(symbol: str):
    data = await alt_pipeline.get_comprehensive_alt_data(symbol)
    return _resp(True, data=data)
