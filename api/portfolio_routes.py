import logging

import numpy as np
from fastapi import APIRouter, Query, Request


logger = logging.getLogger(__name__)
portfolio_router = APIRouter(prefix="/portfolio", tags=["组合管理"])


def _resp(success: bool, data=None, msg: str = ""):
    return {"code": 0 if success else 1, "data": data, "msg": msg}


@portfolio_router.post("/capital/allocate")
async def allocate_capital(
    request: Request,
    strategies: str = Query(..., description="JSON格式策略指标数据"),
    total_capital: float = Query(100000),
    method: str = Query("sharpe"),
):
    try:
        import json
        strat_data = json.loads(strategies)
        result = request.app.state.capital_allocator.allocate(strat_data, total_capital, method)
        return _resp(True, data=result)
    except Exception as e:
        return _resp(False, msg=str(e))


@portfolio_router.post("/capital/correlation")
async def update_correlation(
    request: Request,
    strategy_names: str = Query(..., description="逗号分隔的策略名"),
    returns_data: str = Query(..., description="JSON格式收益率数据"),
):
    try:
        import json
        names = [s.strip() for s in strategy_names.split(",")]
        ret_data = json.loads(returns_data)
        ret_arrays = {k: np.array(v) for k, v in ret_data.items()}
        result = request.app.state.capital_allocator.update_correlation_matrix(names, ret_arrays)
        return _resp(True, data=result)
    except Exception as e:
        return _resp(False, msg=str(e))


@portfolio_router.get("/capital/info")
async def get_allocator_info(request: Request):
    return _resp(True, data=request.app.state.capital_allocator.get_info())


@portfolio_router.post("/rebalance/calendar")
async def calendar_rebalance(
    request: Request,
    positions: str = Query(..., description="JSON格式持仓数据"),
    target_weights: str = Query(..., description="JSON格式目标权重"),
    current_date: str = Query(""),
    frequency: str = Query("monthly"),
):
    try:
        import json
        pos = json.loads(positions)
        weights = json.loads(target_weights)
        orders = request.app.state.rebalance_engine.check_calendar_rebalance(
            pos, weights, current_date, frequency,
        )
        return _resp(True, data=[o.to_dict() for o in orders])
    except Exception as e:
        return _resp(False, msg=str(e))


@portfolio_router.post("/rebalance/threshold")
async def threshold_rebalance(
    request: Request,
    positions: str = Query(..., description="JSON格式持仓数据"),
    target_weights: str = Query(..., description="JSON格式目标权重"),
    threshold: float = Query(0.05),
):
    try:
        import json
        pos = json.loads(positions)
        weights = json.loads(target_weights)
        orders = request.app.state.rebalance_engine.check_threshold_rebalance(pos, weights, threshold)
        return _resp(True, data=[o.to_dict() for o in orders])
    except Exception as e:
        return _resp(False, msg=str(e))


@portfolio_router.post("/rebalance/tax-aware")
async def tax_aware_rebalance(
    request: Request,
    positions: str = Query(..., description="JSON格式持仓数据"),
    target_weights: str = Query(..., description="JSON格式目标权重"),
    tax_rate: float = Query(0.2),
):
    try:
        import json
        pos = json.loads(positions)
        weights = json.loads(target_weights)
        orders = request.app.state.rebalance_engine.tax_aware_rebalance(pos, weights, tax_rate)
        return _resp(True, data=[o.to_dict() for o in orders])
    except Exception as e:
        return _resp(False, msg=str(e))


@portfolio_router.post("/rebalance/cost-estimate")
async def estimate_rebalance_cost(
    request: Request,
    orders: str = Query(..., description="JSON格式再平衡订单"),
):
    try:
        import json
        order_data = json.loads(orders)
        cost = request.app.state.rebalance_engine.estimate_transaction_costs(order_data)
        return _resp(True, data=cost)
    except Exception as e:
        return _resp(False, msg=str(e))


@portfolio_router.post("/attribution/daily")
async def daily_attribution(
    request: Request,
    portfolio_returns: str = Query(..., description="JSON格式组合收益"),
    benchmark_returns: str = Query(..., description="JSON格式基准收益"),
    portfolio_weights: str = Query(..., description="JSON格式组合权重"),
    benchmark_weights: str = Query(..., description="JSON格式基准权重"),
):
    try:
        import json
        pr = json.loads(portfolio_returns)
        br = json.loads(benchmark_returns)
        pw = json.loads(portfolio_weights)
        bw = json.loads(benchmark_weights)
        result = request.app.state.attribution.daily_attribution(pr, br, pw, bw)
        return _resp(True, data=result.to_dict())
    except Exception as e:
        return _resp(False, msg=str(e))


@portfolio_router.post("/attribution/rolling")
async def rolling_attribution(
    request: Request,
    portfolio_returns: str = Query(..., description="JSON格式组合收益"),
    benchmark_returns: str = Query(..., description="JSON格式基准收益"),
    window: int = Query(22),
):
    try:
        import json
        pr = json.loads(portfolio_returns)
        br = json.loads(benchmark_returns)
        result = request.app.state.attribution.rolling_attribution(pr, br, window)
        return _resp(True, data=result)
    except Exception as e:
        return _resp(False, msg=str(e))


@portfolio_router.post("/attribution/excess-return")
async def excess_return_decomposition(
    request: Request,
    portfolio_returns: str = Query(..., description="逗号分隔的组合收益率"),
    benchmark_returns: str = Query(..., description="逗号分隔的基准收益率"),
):
    try:
        pr = np.array([float(r) for r in portfolio_returns.split(",") if r.strip()])
        br = np.array([float(r) for r in benchmark_returns.split(",") if r.strip()])
        result = request.app.state.attribution.excess_return_decomposition(pr, br)
        return _resp(True, data=result)
    except Exception as e:
        return _resp(False, msg=str(e))


@portfolio_router.post("/derivatives/add-futures")
async def add_futures_position(
    request: Request,
    symbol: str = Query(...),
    quantity: int = Query(...),
    entry_price: float = Query(...),
    contract_month: str = Query(...),
    multiplier: float = Query(1),
    margin_rate: float = Query(0.1),
):
    from core.portfolio.derivatives import FuturesPosition
    pos = FuturesPosition(
        symbol=symbol, contract=contract_month, quantity=quantity,
        entry_price=entry_price, current_price=entry_price, multiplier=multiplier, margin_rate=margin_rate,
    )
    async with request.app.state.write_lock:
        request.app.state.derivatives_mgr.add_future(pos)
    return _resp(True, data=pos.to_dict())


@portfolio_router.post("/derivatives/add-option")
async def add_option_position(
    request: Request,
    symbol: str = Query(...),
    quantity: int = Query(...),
    entry_price: float = Query(...),
    option_type: str = Query("call"),
    strike: float = Query(...),
    expiry: str = Query(...),
    underlying: str = Query(""),
    delta: float = Query(0),
    gamma: float = Query(0),
    theta: float = Query(0),
    vega: float = Query(0),
):
    from core.portfolio.derivatives import OptionPosition
    pos = OptionPosition(
        symbol=symbol, option_type=option_type, strike=strike, expiry=expiry,
        quantity=quantity, entry_price=entry_price, underlying_price=0,
        delta=delta, gamma=gamma, theta=theta, vega=vega,
    )
    async with request.app.state.write_lock:
        request.app.state.derivatives_mgr.add_option(pos)
    return _resp(True, data=pos.to_dict())


@portfolio_router.get("/derivatives/roll-warnings")
async def get_roll_warnings(request: Request):
    warnings = request.app.state.derivatives_mgr.check_roll_reminders()
    return _resp(True, data=warnings)


@portfolio_router.post("/derivatives/roll")
async def roll_futures(request: Request, symbol: str = Query(...), new_contract_month: str = Query(...)):
    async with request.app.state.write_lock:
        result = request.app.state.derivatives_mgr.auto_roll(symbol, new_contract_month)
    return _resp(result is not None, data=result)


@portfolio_router.get("/derivatives/greeks-summary")
async def get_greeks_summary(request: Request):
    summary = request.app.state.derivatives_mgr.calculate_option_greeks_summary()
    return _resp(True, data=summary)


@portfolio_router.post("/derivatives/hedge-ratio")
async def calculate_hedge_ratio(
    request: Request,
    portfolio_delta: float = Query(...),
):
    result = request.app.state.derivatives_mgr.calculate_hedge_ratio(portfolio_delta)
    return _resp(True, data=result)


@portfolio_router.post("/tearsheet/generate")
async def generate_tearsheet(
    request: Request,
    equity_curve: str = Query(..., description="逗号分隔的资金曲线"),
    benchmark_curve: str = Query("", description="逗号分隔的基准曲线"),
    risk_free_rate: float = Query(0.03),
):
    try:
        ec = np.array([float(v) for v in equity_curve.split(",") if v.strip()])
        bc = None
        if benchmark_curve:
            bc = np.array([float(v) for v in benchmark_curve.split(",") if v.strip()])
        request.app.state.tearsheet_gen.risk_free_rate = risk_free_rate
        result = request.app.state.tearsheet_gen.generate(ec, bc)
        return _resp(True, data=result.to_dict())
    except Exception as e:
        return _resp(False, msg=str(e))


@portfolio_router.post("/tearsheet/monthly-returns")
async def get_monthly_returns(request: Request, equity_curve: str = Query(..., description="逗号分隔的资金曲线")):
    try:
        ec = np.array([float(v) for v in equity_curve.split(",") if v.strip()])
        monthly = request.app.state.tearsheet_gen.get_monthly_returns(ec)
        return _resp(True, data=monthly)
    except Exception as e:
        return _resp(False, msg=str(e))


@portfolio_router.post("/tearsheet/export")
async def export_tearsheet(
    request: Request,
    equity_curve: str = Query(..., description="逗号分隔的资金曲线"),
    format: str = Query("json", description="导出格式: json/pdf/excel"),
):
    try:
        ec = np.array([float(v) for v in equity_curve.split(",") if v.strip()])
        result = request.app.state.tearsheet_gen.generate(ec)
        if format == "json":
            return _resp(True, data=result.to_dict())
        elif format == "pdf":
            return _resp(True, data={"message": "PDF导出需要安装reportlab", "data": result.to_dict()})
        elif format == "excel":
            return _resp(True, data={"message": "Excel导出需要安装openpyxl", "data": result.to_dict()})
        return _resp(False, msg=f"不支持的格式: {format}")
    except Exception as e:
        return _resp(False, msg=str(e))


router = portfolio_router