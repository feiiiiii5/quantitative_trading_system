import logging
from typing import Optional

from fastapi import APIRouter, Query

from core.execution.order_router import SmartOrderRouter, OrderRequest, OrderSide, OrderType
from core.execution.algo_engine import AlgoExecutionEngine, AlgoType
from core.execution.multi_account import MultiAccountManager
from core.execution.paper_live import PaperLiveSwitch

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/exec", tags=["执行与交易"])

order_router = SmartOrderRouter()
algo_engine = AlgoExecutionEngine()
account_mgr = MultiAccountManager()
paper_live = PaperLiveSwitch()


def _resp(success: bool, data=None, msg: str = ""):
    return {"code": 0 if success else 1, "data": data, "msg": msg}


# ==================== 21 智能订单路由 ====================

@router.get("/router/brokers")
async def get_brokers():
    return _resp(True, data=order_router.get_brokers())


@router.post("/router/route")
async def route_order(
    symbol: str = Query(...), side: str = Query("buy"),
    quantity: int = Query(...), price: float = Query(0),
    order_type: str = Query("market"),
):
    req = OrderRequest(
        symbol=symbol, side=OrderSide(side), quantity=quantity,
        price=price, order_type=OrderType(order_type),
    )
    result = order_router.route_order(req)
    return _resp(True, data=result.to_dict())


@router.post("/router/oco")
async def create_oco_order(
    symbol: str = Query(...), quantity: int = Query(...),
    take_profit_price: float = Query(...), stop_loss_price: float = Query(...),
):
    order = order_router.create_oco_order(symbol, quantity, take_profit_price, stop_loss_price)
    return _resp(True, data=order.to_dict())


@router.post("/router/iceberg")
async def create_iceberg_order(
    symbol: str = Query(...), side: str = Query("buy"),
    quantity: int = Query(...), price: float = Query(...),
    display_size: int = Query(100),
):
    order = order_router.create_iceberg_order(symbol, OrderSide(side), quantity, price, display_size)
    return _resp(True, data=order.to_dict())


# ==================== 22 算法执行引擎 ====================

@router.post("/algo/twap")
async def execute_twap(
    symbol: str = Query(...), side: str = Query("buy"),
    quantity: int = Query(...), price: float = Query(...),
    n_slices: int = Query(4),
):
    result = algo_engine.execute_twap(symbol, side, quantity, price, n_slices)
    return _resp(True, data=result.to_dict())


@router.post("/algo/vwap")
async def execute_vwap(
    symbol: str = Query(...), side: str = Query("buy"),
    quantity: int = Query(...), price: float = Query(...),
):
    result = algo_engine.execute_vwap(symbol, side, quantity, price)
    return _resp(True, data=result.to_dict())


@router.post("/algo/pov")
async def execute_pov(
    symbol: str = Query(...), side: str = Query("buy"),
    quantity: int = Query(...), price: float = Query(...),
    participation_rate: float = Query(0.1),
):
    result = algo_engine.execute_pov(symbol, side, quantity, price, participation_rate)
    return _resp(True, data=result.to_dict())


@router.post("/algo/is")
async def execute_is(
    symbol: str = Query(...), side: str = Query("buy"),
    quantity: int = Query(...), price: float = Query(...),
    urgency: str = Query("medium"),
):
    result = algo_engine.execute_is(symbol, side, quantity, price, urgency=urgency)
    return _resp(True, data=result.to_dict())


@router.get("/algo/info")
async def get_algo_info():
    return _resp(True, data=algo_engine.get_algo_info())


# ==================== 24 多账户管理 ====================

@router.get("/account/master")
async def get_master_account():
    return _resp(True, data=account_mgr.get_master_account())


@router.post("/account/create")
async def create_sub_account(name: str = Query(...), capital: float = Query(...), strategy: str = Query("")):
    sub = account_mgr.create_sub_account(name, capital, strategy)
    if sub:
        return _resp(True, data=sub.to_dict())
    return _resp(False, msg="资金不足或创建失败")


@router.get("/account/list")
async def list_sub_accounts():
    return _resp(True, data=account_mgr.list_sub_accounts())


@router.post("/account/allocate")
async def allocate_capital(account_id: str = Query(...), amount: float = Query(...)):
    success = account_mgr.allocate_capital(account_id, amount)
    return _resp(success, msg="分配成功" if success else "分配失败")


@router.post("/account/copy-trade")
async def copy_trade(
    from_id: str = Query(...), to_id: str = Query(...),
    symbol: str = Query(...), quantity: int = Query(...),
    price: float = Query(...), side: str = Query("buy"),
):
    result = account_mgr.copy_trade(from_id, to_id, symbol, quantity, price, side)
    return _resp(result.get("success", False), data=result)


# ==================== 25 模拟与实盘切换 ====================

@router.post("/paper/buy")
async def paper_buy(
    symbol: str = Query(...), name: str = Query(""),
    market: str = Query("A"), price: float = Query(...),
    strategy: str = Query("manual"),
):
    result = paper_live.paper_buy(symbol, name, market, price, strategy)
    return _resp(result.get("success", False), data=result)


@router.post("/paper/sell")
async def paper_sell(symbol: str = Query(...), price: float = Query(...)):
    result = paper_live.paper_sell(symbol, price)
    return _resp(result.get("success", False), data=result)


@router.get("/paper/status")
async def get_paper_status():
    return _resp(True, data=paper_live.get_paper_status())


@router.post("/paper/reset")
async def reset_paper_account(capital: float = Query(100000)):
    paper_live.reset_paper_account(capital)
    return _resp(True, msg="模拟账户已重置")


@router.get("/paper/checklist")
async def get_pre_live_checklist():
    return _resp(True, data=paper_live.check_pre_live_checklist())


@router.post("/paper/switch-live")
async def switch_to_live():
    result = paper_live.switch_to_live()
    return _resp(result.get("success", False), data=result)


@router.post("/paper/switch-paper")
async def switch_to_paper():
    result = paper_live.switch_to_paper()
    return _resp(True, data=result)
