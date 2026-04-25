import logging

import numpy as np
from fastapi import APIRouter, Query, Request

from core.risk.position_manager import PositionMode, PositionConstraint
from core.risk.stop_loss import StopLossType

logger = logging.getLogger(__name__)
risk_router = APIRouter(prefix="/risk", tags=["风险管理"])


def _resp(success: bool, data=None, msg: str = ""):
    return {"code": 0 if success else 1, "data": data, "msg": msg}


@risk_router.post("/var/calculate")
async def calculate_var(
    request: Request,
    returns: str = Query(..., description="逗号分隔的收益率序列"),
    portfolio_value: float = Query(100000),
    confidence: float = Query(0.95),
):
    try:
        ret_array = np.array([float(r) for r in returns.split(",") if r.strip()])
        var_monitor = request.app.state.var_monitor
        var_monitor.confidence_level = confidence
        result = var_monitor.calculate_var(ret_array, portfolio_value)
        return _resp(True, data=result.to_dict())
    except Exception as e:
        return _resp(False, msg=str(e))


@risk_router.post("/var/portfolio")
async def calculate_portfolio_var(
    request: Request,
    symbols: str = Query(..., description="逗号分隔的股票代码"),
    values: str = Query(..., description="逗号分隔的持仓市值"),
    returns_data: str = Query(..., description="JSON格式的收益率数据"),
):
    try:
        import json
        sym_list = [s.strip() for s in symbols.split(",")]
        val_list = [float(v) for v in values.split(",")]
        positions = dict(zip(sym_list, val_list))
        ret_data = json.loads(returns_data)
        ret_arrays = {k: np.array(v) for k, v in ret_data.items()}
        result = request.app.state.var_monitor.calculate_portfolio_var(positions, ret_arrays)
        return _resp(True, data=result.to_dict())
    except Exception as e:
        return _resp(False, msg=str(e))


@risk_router.post("/var/greeks")
async def calculate_greeks(
    request: Request,
    symbol: str = Query(...),
    S: float = Query(...),
    K: float = Query(...),
    T: float = Query(...),
    r: float = Query(0.03),
    sigma: float = Query(0.3),
    option_type: str = Query("call"),
):
    result = request.app.state.var_monitor.calculate_option_greeks(symbol, S, K, T, r, sigma, option_type)
    return _resp(True, data=result.to_dict())


@risk_router.post("/position/calculate")
async def calculate_position(
    request: Request,
    symbol: str = Query(...),
    capital: float = Query(100000),
    price: float = Query(...),
    atr: float = Query(0),
    volatility: float = Query(0),
    win_rate: float = Query(0.5),
    mode: str = Query("half_kelly"),
):
    try:
        position_mgr = request.app.state.position_mgr
        position_mgr.mode = PositionMode(mode)
        result = position_mgr.calculate_position(symbol, capital, price, atr, volatility, win_rate)
        return _resp(True, data=result.to_dict())
    except ValueError:
        return _resp(False, msg=f"不支持的仓位模式: {mode}")


@risk_router.get("/position/mode-info")
async def get_position_mode_info(request: Request):
    return _resp(True, data=request.app.state.position_mgr.get_mode_info())


@risk_router.post("/position/set-constraints")
async def set_position_constraints(
    request: Request,
    max_single_pct: float = Query(0.3),
    max_industry_pct: float = Query(0.5),
    max_market_cap_pct: float = Query(0.6),
    max_total_exposure: float = Query(1.0),
):
    async with request.app.state.write_lock:
        request.app.state.position_mgr.constraints = PositionConstraint(
            max_single_pct=max_single_pct,
            max_industry_pct=max_industry_pct,
            max_market_cap_pct=max_market_cap_pct,
            max_total_exposure=max_total_exposure,
        )
    return _resp(True, msg="约束已更新")


@risk_router.post("/position/portfolio-risk")
async def get_portfolio_risk(request: Request, positions: str = Query(..., description="JSON格式的持仓数据")):
    try:
        import json
        pos_data = json.loads(positions)
        result = request.app.state.position_mgr.get_portfolio_risk(pos_data)
        return _resp(True, data=result)
    except Exception as e:
        return _resp(False, msg=str(e))


@risk_router.post("/stoploss/set")
async def set_stop_loss(
    request: Request,
    symbol: str = Query(...),
    entry_price: float = Query(...),
    entry_date: str = Query(""),
    stop_type: str = Query("percentage"),
    percentage: float = Query(0.05),
    amount: float = Query(0),
    atr: float = Query(0),
):
    try:
        st = StopLossType(stop_type)
        params = {"percentage": percentage, "amount": amount, "atr": atr}
        async with request.app.state.write_lock:
            order = request.app.state.stop_loss_mgr.set_stop_loss(symbol, entry_price, entry_date, st, params)
        return _resp(True, data=order.to_dict())
    except ValueError:
        return _resp(False, msg=f"不支持的止损类型: {stop_type}")


@risk_router.post("/stoploss/set-take-profit")
async def set_take_profit(
    request: Request,
    symbol: str = Query(...),
    entry_price: float = Query(...),
    take_profit_pct: float = Query(0.10),
):
    async with request.app.state.write_lock:
        order = request.app.state.stop_loss_mgr.set_take_profit(symbol, entry_price, take_profit_pct)
    return _resp(True, data=order.to_dict())


@risk_router.post("/stoploss/check")
async def check_stop_loss(
    request: Request,
    symbol: str = Query(...),
    current_price: float = Query(...),
    current_date: str = Query(""),
):
    sl_result = request.app.state.stop_loss_mgr.check_stop_loss(symbol, current_price, current_date)
    tp_result = request.app.state.stop_loss_mgr.check_take_profit(symbol, current_price)
    return _resp(True, data={"stop_loss": sl_result, "take_profit": tp_result})


@risk_router.post("/stoploss/circuit-breaker")
async def check_circuit_breaker(
    request: Request,
    current_equity: float = Query(...),
    trade_pnl: float = Query(0),
):
    result = request.app.state.stop_loss_mgr.check_circuit_breaker(current_equity, trade_pnl)
    return _resp(True, data=result)


@risk_router.get("/stoploss/orders")
async def get_active_orders(request: Request):
    orders = request.app.state.stop_loss_mgr.get_active_orders()
    return _resp(True, data=orders)


@risk_router.get("/stress/scenarios")
async def get_stress_scenarios(request: Request):
    scenarios = request.app.state.stress_test.get_scenarios()
    return _resp(True, data=scenarios)


@risk_router.post("/stress/run")
async def run_stress_test(
    request: Request,
    scenario_name: str = Query(...),
    positions: str = Query(..., description="JSON格式的持仓数据"),
):
    try:
        import json
        pos_data = json.loads(positions)
        result = request.app.state.stress_test.run_scenario(scenario_name, pos_data)
        return _resp(True, data=result.to_dict())
    except Exception as e:
        return _resp(False, msg=str(e))


@risk_router.post("/stress/run-all")
async def run_all_stress_tests(request: Request, positions: str = Query(..., description="JSON格式的持仓数据")):
    try:
        import json
        pos_data = json.loads(positions)
        results = request.app.state.stress_test.run_all_scenarios(pos_data)
        return _resp(True, data={k: v.to_dict() for k, v in results.items()})
    except Exception as e:
        return _resp(False, msg=str(e))


@risk_router.post("/stress/custom")
async def run_custom_stress(
    request: Request,
    positions: str = Query(..., description="JSON格式的持仓数据"),
    shock_pct: float = Query(-0.20),
    volatility_mult: float = Query(2.0),
    liquidity_shock: float = Query(0.1),
):
    try:
        import json
        pos_data = json.loads(positions)
        result = request.app.state.stress_test.run_custom_shock(pos_data, shock_pct, volatility_mult, liquidity_shock)
        return _resp(True, data=result.to_dict())
    except Exception as e:
        return _resp(False, msg=str(e))


@risk_router.post("/attribution/brinson")
async def brinson_attribution(
    request: Request,
    portfolio_returns: str = Query(..., description="JSON"),
    benchmark_returns: str = Query(..., description="JSON"),
    portfolio_weights: str = Query(..., description="JSON"),
    benchmark_weights: str = Query(..., description="JSON"),
):
    try:
        import json
        pr = json.loads(portfolio_returns)
        br = json.loads(benchmark_returns)
        pw = json.loads(portfolio_weights)
        bw = json.loads(benchmark_weights)
        result = request.app.state.risk_attr.brinson_attribution(pr, br, pw, bw)
        return _resp(True, data=result.to_dict())
    except Exception as e:
        return _resp(False, msg=str(e))


@risk_router.post("/attribution/barra")
async def barra_exposures(request: Request, returns: str = Query(..., description="逗号分隔的收益率序列")):
    try:
        ret_array = np.array([float(r) for r in returns.split(",") if r.strip()])
        exposures = request.app.state.risk_attr.calculate_barra_exposures(ret_array)
        return _resp(True, data=[e.to_dict() for e in exposures])
    except Exception as e:
        return _resp(False, msg=str(e))


@risk_router.post("/attribution/report")
async def generate_risk_report(request: Request, returns: str = Query(..., description="逗号分隔的收益率序列")):
    try:
        ret_array = np.array([float(r) for r in returns.split(",") if r.strip()])
        report = request.app.state.risk_attr.generate_risk_report(ret_array)
        return _resp(True, data=report.to_dict())
    except Exception as e:
        return _resp(False, msg=str(e))
