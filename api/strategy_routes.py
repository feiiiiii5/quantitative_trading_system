import logging
from typing import Optional

import numpy as np
from fastapi import APIRouter, Query, Request

from core.strategy_v2.visual_builder import VisualStrategyBuilder
from core.strategy_v2.signal_execution import (
    SignalExecutionDecoupler, MomentumAlpha, MeanReversionAlpha,
    EqualWeightPortfolio, RiskParityPortfolio, BasicRiskModel,
    TWAPExecution, VWAPExecution,
)
from core.strategy_v2.ml_strategy import MLStrategyModule
from core.strategy_v2.factor_research import FactorResearchWorkbench
from core.strategy_v2.strategy_version import StrategyVersionControl

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/strategy", tags=["策略开发框架"])


def _resp(success: bool, data=None, msg: str = ""):
    return {"code": 0 if success else 1, "data": data, "msg": msg}


# ==================== 16 可视化策略构建器 ====================

@router.get("/builder/catalog")
async def get_catalog(request: Request):
    catalog = request.app.state.builder.get_catalog()
    return _resp(True, data=catalog)


@router.post("/builder/create")
async def create_strategy(request: Request, name: str = Query(...), description: str = Query("")):
    strategy = request.app.state.builder.create_strategy(name, description)
    return _resp(True, data=strategy.to_dict())


@router.post("/builder/add-node")
async def add_node(request: Request)
    strategy_name: str = Query(...),
    node_type: str = Query(...),
    node_name: str = Query(...),
    params: str = Query("{}"),
):
    import json
    try:
        p = json.loads(params)
    except Exception:
        p = {}
    node = request.app.state.builder.add_node(strategy_name, node_type, node_name, p)
    if node:
        return _resp(True, data=node.to_dict())
    return _resp(False, msg="添加节点失败")


@router.post("/builder/add-edge")
async def add_edge(request: Request)
    strategy_name: str = Query(...),
    source_id: str = Query(...),
    source_output: str = Query("value"),
    target_id: str = Query(...),
    target_input: str = Query("input"),
):
    edge = request.app.state.builder.add_edge(strategy_name, source_id, source_output, target_id, target_input)
    if edge:
        return _resp(True, data=edge.to_dict())
    return _resp(False, msg="添加边失败")


@router.get("/builder/export/{name}")
async def export_strategy(request: Request, name: str):
    code = request.app.state.builder.export_to_python(name)
    if code:
        return _resp(True, data={"code": code})
    return _resp(False, msg="策略未找到")


@router.get("/builder/list")
async def list_strategies(request: Request):
    strategies = request.app.state.builder.list_strategies()
    return _resp(True, data=strategies)


# ==================== 17 信号执行解耦 ====================

@router.post("/pipeline/run")
async def run_pipeline(request: Request)
    symbols: str = Query(..., description="逗号分隔的股票代码"),
    period: str = Query("1y"),
    alpha_model: str = Query("momentum"),
    portfolio_model: str = Query("equal_weight"),
    execution_model: str = Query("twap"),
):
    from core.data_fetcher import SmartDataFetcher
    fetcher = SmartDataFetcher()

    alpha = MomentumAlpha() if alpha_model == "momentum" else MeanReversionAlpha()
    portfolio = RiskParityPortfolio() if portfolio_model == "risk_parity" else EqualWeightPortfolio()
    execution = VWAPExecution() if execution_model == "vwap" else TWAPExecution()

    dec = SignalExecutionDecoupler(alpha, portfolio, BasicRiskModel(), execution)

    data = {}
    prices = {}
    for sym in symbols.split(","):
        sym = sym.strip()
        try:
            df = await fetcher.get_history(sym, period)
            if not df.empty:
                data[sym] = df
                prices[sym] = float(df["close"].iloc[-1])
        except Exception:
            pass

    if not data:
        return _resp(False, msg="无有效数据")

    result = dec.run_pipeline(data, {}, {}, prices, 100000)
    return _resp(True, data=result)


@router.get("/pipeline/models")
async def get_model_info(request: Request):
    return _resp(True, data={
        "alpha_models": ["momentum", "mean_reversion"],
        "portfolio_models": ["equal_weight", "risk_parity"],
        "risk_models": ["basic"],
        "execution_models": ["twap", "vwap"],
    })


# ==================== 18 ML策略 ====================

@router.get("/ml/models")
async def get_ml_models(request: Request):
    models = request.app.state.ml_module.get_available_models()
    return _resp(True, data=models)


@router.get("/ml/features")
async def get_ml_features(request: Request):
    features = request.app.state.ml_module.get_features_info()
    return _resp(True, data=features)


@router.post("/ml/train")
async def train_ml_model(request: Request, symbol: str = Query(...), period: str = Query("1y"), model_type: str = Query("lightgbm")):
    from core.data_fetcher import SmartDataFetcher
    fetcher = SmartDataFetcher()
    try:
        df = await fetcher.get_history(symbol, period)
        if df.empty:
            return _resp(False, msg="数据不足")
        result = request.app.state.ml_module.train_model(df, model_type)
        return _resp(result.get("success", False), data=result)
    except Exception as e:
        return _resp(False, msg=str(e))


# ==================== 19 因子研究 ====================

@router.post("/factor/research")
async def research_factor(request: Request)
    name: str = Query(...),
    factor_values: str = Query(..., description="逗号分隔的因子值"),
    returns: str = Query(..., description="逗号分隔的收益率"),
    forward_period: int = Query(5),
):
    try:
        fv = np.array([float(v) for v in factor_values.split(",") if v.strip()])
        ret = np.array([float(v) for v in returns.split(",") if v.strip()])
        result = request.app.state.factor_wb.research_factor(name, fv, ret, forward_period)
        return _resp(True, data=result.to_dict())
    except Exception as e:
        return _resp(False, msg=str(e))


@router.post("/factor/composite")
async def composite_factor(request: Request)
    returns: str = Query(..., description="逗号分隔的收益率"),
    method: str = Query("equal_weight"),
):
    try:
        ret = np.array([float(v) for v in returns.split(",") if v.strip()])
        factors = {
            "momentum": np.random.randn(len(ret)),
            "reversal": -np.random.randn(len(ret)),
            "volatility": np.abs(np.random.randn(len(ret))),
        }
        result = request.app.state.factor_wb.multi_factor_composite(factors, ret, method)
        return _resp(True, data=result)
    except Exception as e:
        return _resp(False, msg=str(e))


# ==================== 20 策略版本控制 ====================

@router.post("/version/commit")
async def commit_version(request: Request)
    strategy_name: str = Query(...),
    params: str = Query("{}"),
    commit_message: str = Query(""),
    author: str = Query(""),
):
    import json
    try:
        p = json.loads(params)
    except Exception:
        p = {}
    version = request.app.state.version_ctrl.commit(strategy_name, p, commit_message, author)
    return _resp(True, data=version.to_dict())


@router.get("/version/list/{strategy_name}")
async def list_versions(request: Request, strategy_name: str):
    versions = request.app.state.version_ctrl.get_versions(strategy_name)
    return _resp(True, data=versions)


@router.get("/version/latest/{strategy_name}")
async def get_latest_version(request: Request, strategy_name: str):
    version = request.app.state.version_ctrl.get_latest(strategy_name)
    if version:
        return _resp(True, data=version)
    return _resp(False, msg="未找到版本")


@router.get("/version/diff/{strategy_name}")
async def diff_versions(request: Request, strategy_name: str, v1: str = Query(...), v2: str = Query(...)):
    result = request.app.state.version_ctrl.diff_versions(strategy_name, v1, v2)
    return _resp(True, data=result)


@router.post("/version/promote/{strategy_name}")
async def promote_version(request: Request, strategy_name: str, version_id: str = Query(...)):
    result = request.app.state.version_ctrl.promote(strategy_name, version_id)
    return _resp(result.get("success", False), data=result)


@router.get("/version/strategies")
async def list_all_strategies(request: Request):
    strategies = request.app.state.version_ctrl.list_strategies()
    return _resp(True, data=strategies)
