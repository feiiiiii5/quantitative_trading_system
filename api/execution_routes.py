import logging
from typing import Optional

from fastapi import APIRouter, Query, Request

from core.execution.order_router import SmartOrderRouter, OrderRequest, OrderSide, OrderType
from core.execution.algo_engine import AlgoExecutionEngine, AlgoType
from core.execution.multi_account import MultiAccountManager
from core.execution.paper_live import PaperLiveSwitch

logger = logging.getLogger(__name__)
execution_router = APIRouter(prefix="/exec", tags=["执行与交易"])


def _resp(success: bool, data=None, msg: str = ""):
    return {"code": 0 if success else 1, "data": data, "msg": msg}


# ==================== 21 智能订单路由 ====================

@execution_router.get("/router/brokers")
async def get_brokers(request: Request):
    return _resp(True, data=request.app.state.order_router.get_brokers())


@execution_router.post("/router/route")
async def route_order(request: Request, 
    symbol: str = Query(...), side: str = Query("buy"),
    quantity: int = Query(...), price: float = Query(0),
    order_type: str = Query("market"),
):
    req = OrderRequest(
        symbol=symbol, side=OrderSide(side), quantity=quantity,
        price=price, order_type=OrderType(order_type),
    )
    result = request.app.state.order_router.route_order(req)
    return _resp(True, data=result.to_dict())


@execution_router.post("/router/oco")
async def create_oco_order(request: Request, 
    symbol: str = Query(...), quantity: int = Query(...),
    take_profit_price: float = Query(...), stop_loss_price: float = Query(...),
):
    order = request.app.state.order_router.create_oco_order(symbol, quantity, take_profit_price, stop_loss_price)
    return _resp(True, data=order.to_dict())


@execution_router.post("/router/iceberg")
async def create_iceberg_order(request: Request, 
    symbol: str = Query(...), side: str = Query("buy"),
    quantity: int = Query(...), price: float = Query(...),
    display_size: int = Query(100),
):
    order = request.app.state.order_router.create_iceberg_order(symbol, OrderSide(side), quantity, price, display_size)
    return _resp(True, data=order.to_dict())


# ==================== 22 算法执行引擎 ====================

@execution_router.post("/algo/twap")
async def execute_twap(request: Request, 
    symbol: str = Query(...), side: str = Query("buy"),
    quantity: int = Query(...), price: float = Query(...),
    n_slices: int = Query(4),
):
    result = request.app.state.algo_engine.execute_twap(symbol, side, quantity, price, n_slices)
    return _resp(True, data=result.to_dict())


@execution_router.post("/algo/vwap")
async def execute_vwap(request: Request, 
    symbol: str = Query(...), side: str = Query("buy"),
    quantity: int = Query(...), price: float = Query(...),
):
    result = request.app.state.algo_engine.execute_vwap(symbol, side, quantity, price)
    return _resp(True, data=result.to_dict())


@execution_router.post("/algo/pov")
async def execute_pov(request: Request, 
    symbol: str = Query(...), side: str = Query("buy"),
    quantity: int = Query(...), price: float = Query(...),
    participation_rate: float = Query(0.1),
):
    result = request.app.state.algo_engine.execute_pov(symbol, side, quantity, price, participation_rate)
    return _resp(True, data=result.to_dict())


@execution_router.post("/algo/is")
async def execute_is(request: Request, 
    symbol: str = Query(...), side: str = Query("buy"),
    quantity: int = Query(...), price: float = Query(...),
    urgency: str = Query("medium"),
):
    result = request.app.state.algo_engine.execute_is(symbol, side, quantity, price, urgency=urgency)
    return _resp(True, data=result.to_dict())


@execution_router.get("/algo/info")
async def get_algo_info(request: Request):
    return _resp(True, data=request.app.state.algo_engine.get_algo_info())


# ==================== 24 多账户管理 ====================

@execution_router.get("/account/master")
async def get_master_account(request: Request):
    return _resp(True, data=request.app.state.account_mgr.get_master_account())


@execution_router.post("/account/create")
async def create_sub_account(request: Request, name: str = Query(...), capital: float = Query(...), strategy: str = Query("")):
    sub = request.app.state.account_mgr.create_sub_account(name, capital, strategy)
    if sub:
        return _resp(True, data=sub.to_dict())
    return _resp(False, msg="资金不足或创建失败")


@execution_router.get("/account/list")
async def list_sub_accounts(request: Request):
    return _resp(True, data=request.app.state.account_mgr.list_sub_accounts())


@execution_router.post("/account/allocate")
async def allocate_capital(request: Request, account_id: str = Query(...), amount: float = Query(...)):
    success = request.app.state.account_mgr.allocate_capital(account_id, amount)
    return _resp(success, msg="分配成功" if success else "分配失败")


@execution_router.post("/account/copy-trade")
async def copy_trade(request: Request, 
    from_id: str = Query(...), to_id: str = Query(...),
    symbol: str = Query(...), quantity: int = Query(...),
    price: float = Query(...), side: str = Query("buy"),
):
    result = request.app.state.account_mgr.copy_trade(from_id, to_id, symbol, quantity, price, side)
    return _resp(result.get("success", False), data=result)


# ==================== 25 模拟与实盘切换 ====================

@execution_router.post("/paper/buy")
async def paper_buy(request: Request, 
    symbol: str = Query(...), name: str = Query(""),
    market: str = Query("A"), price: float = Query(...),
    strategy: str = Query("manual"),
):
    result = request.app.state.paper_live.paper_buy(symbol, name, market, price, strategy)
    return _resp(result.get("success", False), data=result)


@execution_router.post("/paper/sell")
async def paper_sell(request: Request, symbol: str = Query(...), price: float = Query(...)):
    result = request.app.state.paper_live.paper_sell(symbol, price)
    return _resp(result.get("success", False), data=result)


@execution_router.get("/paper/status")
async def get_paper_status(request: Request):
    return _resp(True, data=request.app.state.paper_live.get_paper_status())


@execution_router.post("/paper/reset")
async def reset_paper_account(request: Request, capital: float = Query(100000)):
    request.app.state.paper_live.reset_paper_account(capital)
    return _resp(True, msg="模拟账户已重置")


@execution_router.get("/paper/checklist")
async def get_pre_live_checklist(request: Request):
    return _resp(True, data=request.app.state.paper_live.check_pre_live_checklist())


@execution_router.post("/paper/switch-live")
async def switch_to_live(request: Request):
    result = request.app.state.paper_live.switch_to_live()
    return _resp(result.get("success", False), data=result)


@execution_router.post("/paper/switch-paper")
async def switch_to_paper(request: Request):
    result = request.app.state.paper_live.switch_to_paper()
    return _resp(True, data=result)
