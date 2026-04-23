import logging
from typing import Dict, List, Optional

from fastapi import APIRouter, Query, Request

from core.backtest_v2.event_engine import EventBacktestEngine
from core.backtest_v2.microstructure import MicrostructureSimulator, SlippageModel, OrderBookMechanism, OrderBookLevel
from core.backtest_v2.portfolio_backtest import PortfolioBacktester
from core.backtest_v2.param_optimizer import ParamOptimizer
from core.backtest_v2.monte_carlo import MonteCarloStressTest
from core.strategies import (
    DualMAStrategy, MACDStrategy, RSIMeanReversionStrategy,
    SuperTrendStrategy, KDJStrategy, BollingerBreakoutStrategy,
    CompositeStrategy,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/bt2", tags=["回测引擎V2"])

STRATEGY_MAP = {
    "dual_ma": DualMAStrategy,
    "macd": MACDStrategy,
    "rsi": RSIMeanReversionStrategy,
    "supertrend": SuperTrendStrategy,
    "kdj": KDJStrategy,
    "bollinger": BollingerBreakoutStrategy,
}


def _resp(success: bool, data=None, msg: str = ""):
    return {"code": 0 if success else 1, "data": data, "msg": msg}


@router.get("/event/run/{symbol}")
async def event_backtest(request: Request, symbol: str, strategy: str = Query("dual_ma"), period: str = Query("1y")):
    if strategy not in STRATEGY_MAP:
        return _resp(False, msg=f"不支持的策略: {strategy}")
    try:
        df = await request.app.state.fetcher.get_history(symbol, period)
        if df.empty or len(df) < 60:
            return _resp(False, msg="数据不足")
        strat = STRATEGY_MAP[strategy]()
        result = request.app.state.event_engine.run(strat, df, symbol)
        return _resp(True, data=result)
    except Exception as e:
        return _resp(False, msg=str(e))


@router.post("/micro/fill")
async def simulate_fill(
    request: Request,
    price: float = Query(...),
    quantity: int = Query(...),
    direction: str = Query("buy"),
    avg_volume: float = Query(0),
    volatility: float = Query(0),
):
    fill = request.app.state.micro_sim.simulate_fill(price, quantity, direction, avg_volume, volatility)
    return _resp(True, data=fill.to_dict())


@router.get("/micro/model-info")
async def get_micro_model_info(request: Request):
    return _resp(True, data=request.app.state.micro_sim.get_model_info())


@router.post("/micro/set-model")
async def set_slippage_model(
    request: Request,
    model: str = Query("percentage"),
    fixed_slippage: float = Query(0.01),
    percentage_slippage: float = Query(0.001),
    commission_rate: float = Query(0.0003),
):
    try:
        micro_sim = request.app.state.micro_sim
        async with request.app.state.write_lock:
            micro_sim.slippage_model = SlippageModel(model)
            micro_sim.fixed_slippage = fixed_slippage
            micro_sim.percentage_slippage = percentage_slippage
            micro_sim.commission_rate = commission_rate
        return _resp(True, msg="模型已更新")
    except ValueError:
        return _resp(False, msg=f"不支持的模型: {model}")


@router.post("/portfolio/run")
async def portfolio_backtest(
    request: Request,
    symbols: str = Query(..., description="逗号分隔的股票代码"),
    strategies: str = Query("dual_ma,macd", description="逗号分隔的策略名"),
    period: str = Query("1y"),
    allocations: Optional[str] = Query(None, description="逗号分隔的权重"),
):
    symbol_list = [s.strip() for s in symbols.split(",") if s.strip()]
    strategy_list = [s.strip() for s in strategies.split(",") if s.strip()]

    strat_map = {}
    for name in strategy_list:
        if name in STRATEGY_MAP:
            strat_map[name] = STRATEGY_MAP[name]()

    if not strat_map:
        return _resp(False, msg="无有效策略")

    alloc_map = None
    if allocations:
        weights = [float(w) for w in allocations.split(",")]
        alloc_map = dict(zip(strategy_list, weights))

    data = {}
    for sym in symbol_list:
        try:
            df = await request.app.state.fetcher.get_history(sym, period)
            if not df.empty:
                data[sym] = df
        except Exception:
            pass

    if not data:
        return _resp(False, msg="无有效数据")

    result = request.app.state.portfolio_bt.run(strat_map, data, alloc_map)
    return _resp(True, data=result)


@router.get("/optimize/grid/{symbol}")
async def grid_search(
    request: Request,
    symbol: str,
    strategy: str = Query("dual_ma"),
    period: str = Query("1y"),
    metric: str = Query("sharpe"),
    top_n: int = Query(10),
):
    if strategy not in STRATEGY_MAP:
        return _resp(False, msg=f"不支持的策略: {strategy}")

    try:
        df = await request.app.state.fetcher.get_history(symbol, period)
        if df.empty or len(df) < 60:
            return _resp(False, msg="数据不足")

        param_grid = _get_default_param_grid(strategy)
        results = request.app.state.param_optimizer.grid_search(
            STRATEGY_MAP[strategy], param_grid, df, symbol, metric, top_n
        )
        return _resp(True, data=[r.to_dict() for r in results])
    except Exception as e:
        return _resp(False, msg=str(e))


@router.get("/optimize/bayesian/{symbol}")
async def bayesian_optimize(
    request: Request,
    symbol: str,
    strategy: str = Query("dual_ma"),
    period: str = Query("1y"),
    n_trials: int = Query(30),
    metric: str = Query("sharpe"),
):
    if strategy not in STRATEGY_MAP:
        return _resp(False, msg=f"不支持的策略: {strategy}")

    try:
        df = await request.app.state.fetcher.get_history(symbol, period)
        if df.empty or len(df) < 60:
            return _resp(False, msg="数据不足")

        param_ranges = _get_default_param_ranges(strategy)
        results = request.app.state.param_optimizer.bayesian_optimize(
            STRATEGY_MAP[strategy], param_ranges, df, symbol, n_trials, metric
        )
        return _resp(True, data=[r.to_dict() for r in results])
    except Exception as e:
        return _resp(False, msg=str(e))


@router.get("/optimize/walkforward/{symbol}")
async def walk_forward(
    request: Request,
    symbol: str,
    strategy: str = Query("dual_ma"),
    period: str = Query("1y"),
    n_splits: int = Query(5),
):
    if strategy not in STRATEGY_MAP:
        return _resp(False, msg=f"不支持的策略: {strategy}")

    try:
        df = await request.app.state.fetcher.get_history(symbol, period)
        if df.empty or len(df) < 60:
            return _resp(False, msg="数据不足")

        param_grid = _get_default_param_grid(strategy)
        result = request.app.state.param_optimizer.walk_forward(
            STRATEGY_MAP[strategy], param_grid, df, symbol, n_splits
        )
        return _resp(True, data=result.to_dict())
    except Exception as e:
        return _resp(False, msg=str(e))


@router.get("/optimize/heatmap/{symbol}")
async def generate_heatmap(
    request: Request,
    symbol: str,
    strategy: str = Query("dual_ma"),
    period: str = Query("1y"),
    param_x: str = Query("fast"),
    param_y: str = Query("slow"),
):
    if strategy not in STRATEGY_MAP:
        return _resp(False, msg=f"不支持的策略: {strategy}")

    try:
        df = await request.app.state.fetcher.get_history(symbol, period)
        if df.empty or len(df) < 60:
            return _resp(False, msg="数据不足")

        param_grid = _get_default_param_grid(strategy)
        results = request.app.state.param_optimizer.grid_search(
            STRATEGY_MAP[strategy], param_grid, df, symbol, top_n=50
        )
        heatmap = request.app.state.param_optimizer.generate_heatmap_data(results, param_x, param_y)
        return _resp(True, data=heatmap)
    except Exception as e:
        return _resp(False, msg=str(e))


@router.get("/montecarlo/{symbol}")
async def monte_carlo_test(
    request: Request,
    symbol: str,
    strategy: str = Query("dual_ma"),
    period: str = Query("1y"),
    n_simulations: int = Query(1000),
    method: str = Query("bootstrap"),
):
    if strategy not in STRATEGY_MAP:
        return _resp(False, msg=f"不支持的策略: {strategy}")

    try:
        df = await request.app.state.fetcher.get_history(symbol, period)
        if df.empty or len(df) < 60:
            return _resp(False, msg="数据不足")

        from core.backtest import BacktestEngine
        engine = BacktestEngine()
        strat = STRATEGY_MAP[strategy]()
        bt_result = engine.run(strat, df)

        if not bt_result.equity_curve:
            return _resp(False, msg="回测无结果")

        mc_result = request.app.state.mc_stress.run(bt_result.equity_curve, n_simulations, method)
        return _resp(True, data=mc_result.to_dict())
    except Exception as e:
        return _resp(False, msg=str(e))


@router.get("/montecarlo/stress/{symbol}")
async def stress_scenarios(
    request: Request,
    symbol: str,
    strategy: str = Query("dual_ma"),
    period: str = Query("1y"),
):
    if strategy not in STRATEGY_MAP:
        return _resp(False, msg=f"不支持的策略: {strategy}")

    try:
        df = await request.app.state.fetcher.get_history(symbol, period)
        if df.empty or len(df) < 60:
            return _resp(False, msg="数据不足")

        from core.backtest import BacktestEngine
        engine = BacktestEngine()
        strat = STRATEGY_MAP[strategy]()
        bt_result = engine.run(strat, df)

        if not bt_result.equity_curve:
            return _resp(False, msg="回测无结果")

        results = request.app.state.mc_stress.run_stress_scenarios(bt_result.equity_curve)
        return _resp(True, data={name: r.to_dict() for name, r in results.items()})
    except Exception as e:
        return _resp(False, msg=str(e))


def _get_default_param_grid(strategy: str) -> dict:
    grids = {
        "dual_ma": {"fast": [3, 5, 7, 10], "slow": [15, 20, 30, 40]},
        "macd": {"fast": [8, 10, 12], "slow": [20, 24, 26], "signal": [7, 9, 11]},
        "rsi": {"period": [10, 14, 20], "oversold": [25, 30, 35], "overbought": [65, 70, 75]},
        "supertrend": {"period": [7, 10, 14], "multiplier": [2.0, 3.0, 4.0]},
        "kdj": {"n": [7, 9, 14], "m1": [3, 5], "m2": [3, 5]},
        "bollinger": {"period": [15, 20, 25], "nbdev": [1.5, 2.0, 2.5]},
    }
    return grids.get(strategy, {})


def _get_default_param_ranges(strategy: str) -> dict:
    ranges = {
        "dual_ma": {"fast": (3, 15), "slow": (15, 60)},
        "macd": {"fast": (8, 15), "slow": (20, 30), "signal": (7, 12)},
        "rsi": {"period": (8, 25), "oversold": (20, 35), "overbought": (65, 80)},
        "supertrend": {"period": (5, 20), "multiplier": (1.5, 5.0)},
        "kdj": {"n": (5, 20), "m1": (2, 6), "m2": (2, 6)},
        "bollinger": {"period": (10, 30), "nbdev": (1.0, 3.0)},
    }
    return ranges.get(strategy, {})
