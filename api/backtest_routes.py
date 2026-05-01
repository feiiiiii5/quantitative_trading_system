import logging
from typing import Optional

from fastapi import APIRouter, Query, Request

logger = logging.getLogger(__name__)
backtest_router = APIRouter()


def _json_response(success: bool, data=None, error: str = ""):
    return {"success": success, "data": data, "error": error}


@backtest_router.get("/backtest/strategies")
async def get_backtest_strategies(request: Request):
    try:
        from core.strategies import STRATEGY_REGISTRY
        strategy_info = {}
        seen = set()
        for alias, cls in STRATEGY_REGISTRY.items():
            real_name = cls.__name__
            if real_name in seen:
                continue
            seen.add(real_name)
            try:
                inst = cls()
                info = inst.get_info()
                info["param_space"] = cls.get_param_space()
                strategy_info[real_name] = info
            except Exception:
                strategy_info[real_name] = {"name": real_name, "type": "unknown"}
        strategy_info["AdaptiveEngine"] = {
            "name": "自适应量化策略引擎",
            "type": "adaptive",
            "param_space": {},
        }
        return _json_response(True, data=strategy_info)
    except Exception as e:
        return _json_response(False, error=str(e))


@backtest_router.post("/backtest/run")
async def run_backtest(
    request: Request,
    symbol: str = Query(...),
    strategy_type: str = Query("adaptive"),
    start_date: str = Query("2024-01-01"),
    end_date: str = Query("2025-12-31"),
    initial_capital: float = Query(1000000),
    commission: float = Query(0.0003),
):
    try:
        from core.backtest import run_backtest as run_bt
        fetcher = request.app.state.fetcher
        df = await fetcher.get_history(symbol, period="all", kline_type="daily", adjust="qfq")
        if df is None or df.empty:
            return _json_response(False, error=f"无法获取 {symbol} 的历史数据")

        result = await _run_single_or_adaptive(strategy_type, symbol, start_date, end_date, initial_capital, df)

        if "error" in result:
            return _json_response(False, error=result["error"])

        return _json_response(True, data=result)
    except Exception as e:
        logger.error(f"backtest run error: {e}", exc_info=True)
        return _json_response(False, error=str(e))


@backtest_router.get("/backtest/result/{task_id}")
async def get_backtest_result(request: Request, task_id: str):
    return _json_response(False, error="回测结果查询暂不支持")


@backtest_router.get("/backtest/compare")
async def compare_strategies(
    request: Request,
    symbol: str = Query(...),
    start_date: str = Query("2024-01-01"),
    end_date: str = Query("2025-12-31"),
    period: str = Query("1y"),
):
    try:
        from core.strategies import STRATEGY_REGISTRY
        fetcher = request.app.state.fetcher
        df = await fetcher.get_history(symbol, period="all", kline_type="daily", adjust="qfq")
        if df is None or df.empty:
            return _json_response(False, error="数据不足")

        import pandas as pd
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"], errors="coerce")
            df = df.dropna(subset=["date"])
            df = df[(df["date"] >= start_date) & (df["date"] <= end_date)].reset_index(drop=True)

        if len(df) < 30:
            return _json_response(False, error="指定时间段数据不足")

        engine = request.app.state.backtest_engine
        strategies = request.app.state.composite_strategy.strategies
        results = engine.run_multi(strategies, df)

        comparison = []
        for name, result in results.items():
            comparison.append({
                "strategy_name": result.strategy_name,
                "total_return": result.total_return,
                "annual_return": result.annual_return,
                "sharpe_ratio": result.sharpe_ratio,
                "max_drawdown": result.max_drawdown,
                "win_rate": result.win_rate,
                "profit_factor": result.profit_factor,
                "total_trades": result.total_trades,
            })

        comparison.sort(key=lambda x: x["total_return"], reverse=True)
        return _json_response(True, data=comparison)
    except Exception as e:
        logger.error(f"compare strategies error: {e}", exc_info=True)
        return _json_response(False, error=str(e))


async def _run_single_or_adaptive(strategy_type, symbol, start_date, end_date, initial_capital, df):
    import asyncio
    from core.backtest import run_backtest as run_bt

    if strategy_type == "composite" or strategy_type == "all":
        engine = __import__("core.backtest", fromlist=["BacktestEngine"]).BacktestEngine(initial_capital=initial_capital)
        strategies = __import__("core.strategies", fromlist=["CompositeStrategy"]).CompositeStrategy().strategies
        import pandas as pd
        work_df = df.copy()
        if "date" in work_df.columns:
            work_df["date"] = pd.to_datetime(work_df["date"], errors="coerce")
            work_df = work_df.dropna(subset=["date"])
            work_df = work_df[(work_df["date"] >= start_date) & (work_df["date"] <= end_date)].reset_index(drop=True)
        results = engine.run_multi(strategies, work_df)
        output = {}
        for name, result in results.items():
            output[name] = _serialize_result(result, initial_capital, df)
        return output

    result = await asyncio.to_thread(
        run_bt,
        symbol,
        strategy_type,
        start_date,
        end_date,
        initial_capital,
        None,
        df,
    )
    return result


def _serialize_result(result, initial_capital, df):
    import numpy as np
    equity_curve = []
    if result.equity_curve and result.dates:
        for i in range(min(len(result.dates), len(result.equity_curve))):
            equity_curve.append({"date": result.dates[i], "value": float(result.equity_curve[i])})

    return {
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
        "benchmark_return": result.benchmark_return,
        "alpha": result.alpha,
        "beta": result.beta,
        "equity_curve": equity_curve[-500:] if equity_curve else [],
        "trades": result.trades[-100:] if result.trades else [],
    }
