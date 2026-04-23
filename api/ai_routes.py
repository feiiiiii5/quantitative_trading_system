import logging
from typing import Optional

import numpy as np
from fastapi import APIRouter, Query

from core.ai.adaptive_params import AdaptiveParamOptimizer
from core.ai.nl_strategy import NLStrategyGenerator
from core.ai.pattern_detect import AnomalyPatternDetector
from core.ai.portfolio_ai import PortfolioAIAdvisor
from core.ai.prediction_models import PredictionModelPlatform

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ai", tags=["AI增强功能"])

adaptive_optimizer = AdaptiveParamOptimizer()
nl_generator = NLStrategyGenerator()
pattern_detector = AnomalyPatternDetector()
portfolio_ai = PortfolioAIAdvisor()
prediction_platform = PredictionModelPlatform()


def _resp(success: bool, data=None, msg: str = ""):
    return {"code": 0 if success else 1, "data": data, "msg": msg}


# ==================== 41 自适应参数优化 ====================

@router.post("/adaptive/detect-regime")
async def detect_market_regime(
    returns: str = Query(..., description="逗号分隔的收益率序列"),
    window: int = Query(60),
):
    try:
        ret = np.array([float(r) for r in returns.split(",") if r.strip()])
        result = adaptive_optimizer.detect_regime(ret, window)
        return _resp(True, data=result.to_dict())
    except Exception as e:
        return _resp(False, msg=str(e))


@router.post("/adaptive/optimize-params")
async def optimize_params_adaptive(
    strategy_name: str = Query(...),
    returns: str = Query(..., description="逗号分隔的收益率序列"),
    current_regime: str = Query(""),
):
    try:
        ret = np.array([float(r) for r in returns.split(",") if r.strip()])
        if not current_regime:
            regime = adaptive_optimizer.detect_regime(ret)
            current_regime = regime.regime
        result = adaptive_optimizer.get_optimal_params(strategy_name, current_regime)
        return _resp(True, data=result)
    except Exception as e:
        return _resp(False, msg=str(e))


@router.post("/adaptive/rolling-optimize")
async def rolling_optimize(
    strategy_name: str = Query(...),
    returns: str = Query(..., description="逗号分隔的收益率序列"),
    window: int = Query(60),
    step: int = Query(20),
):
    try:
        ret = np.array([float(r) for r in returns.split(",") if r.strip()])
        result = adaptive_optimizer.rolling_optimize(strategy_name, ret, window, step)
        return _resp(True, data=result)
    except Exception as e:
        return _resp(False, msg=str(e))


@router.get("/adaptive/regime-params")
async def get_regime_params(strategy_name: str = Query("")):
    result = adaptive_optimizer.get_regime_param_map(strategy_name)
    return _resp(True, data=result)


# ==================== 42 自然语言策略生成 ====================

@router.post("/nl/generate")
async def generate_strategy_from_nl(description: str = Query(..., description="自然语言策略描述")):
    try:
        result = nl_generator.generate(description)
        return _resp(result.get("success", False), data=result)
    except Exception as e:
        return _resp(False, msg=str(e))


@router.get("/nl/templates")
async def get_nl_templates():
    templates = nl_generator.get_templates()
    return _resp(True, data=templates)


@router.post("/nl/validate")
async def validate_strategy_code(code: str = Query(..., description="策略代码")):
    try:
        result = nl_generator.validate_code(code)
        return _resp(result.get("valid", False), data=result)
    except Exception as e:
        return _resp(False, msg=str(e))


# ==================== 43 异常市场模式识别 ====================

@router.post("/pattern/detect")
async def detect_patterns(
    prices: str = Query(..., description="逗号分隔的价格序列"),
    volumes: str = Query("", description="逗号分隔的成交量序列"),
    timestamps: str = Query("", description="逗号分隔的时间戳"),
):
    try:
        price_arr = np.array([float(p) for p in prices.split(",") if p.strip()])
        vol_arr = None
        if volumes:
            vol_arr = np.array([float(v) for v in volumes.split(",") if v.strip()])
        ts_list = None
        if timestamps:
            ts_list = [t.strip() for t in timestamps.split(",")]
        result = pattern_detector.detect(price_arr, vol_arr, ts_list)
        return _resp(True, data=[r.to_dict() for r in result])
    except Exception as e:
        return _resp(False, msg=str(e))


@router.post("/pattern/check-volume-anomaly")
async def check_volume_anomaly(
    symbol: str = Query(...),
    current_volume: float = Query(...),
    avg_volume: float = Query(...),
    current_price: float = Query(...),
    prev_price: float = Query(0),
):
    result = pattern_detector.check_volume_price_anomaly(
        symbol, current_volume, avg_volume, current_price, prev_price,
    )
    return _resp(True, data=result)


@router.post("/pattern/check-manipulation")
async def check_manipulation(
    symbol: str = Query(...),
    close_prices: str = Query(..., description="逗号分隔的收盘价"),
    volumes: str = Query(..., description="逗号分隔的成交量"),
    timestamps: str = Query("", description="逗号分隔的时间戳"),
):
    try:
        prices = np.array([float(p) for p in close_prices.split(",") if p.strip()])
        vols = np.array([float(v) for v in volumes.split(",") if v.strip()])
        ts = [t.strip() for t in timestamps.split(",")] if timestamps else None
        result = pattern_detector.detect_manipulation(symbol, prices, vols, ts)
        return _resp(True, data=[r.to_dict() for r in result])
    except Exception as e:
        return _resp(False, msg=str(e))


@router.get("/pattern/historical-similars")
async def find_historical_similars(
    pattern_type: str = Query(...),
    symbol: str = Query(""),
    limit: int = Query(10),
):
    result = pattern_detector.find_similar_historical(pattern_type, symbol, limit)
    return _resp(True, data=result)


# ==================== 44 组合优化AI建议 ====================

@router.post("/portfolio/suggest-rebalance")
async def suggest_rebalance(
    positions: str = Query(..., description="JSON格式持仓数据"),
    returns_data: str = Query(..., description="JSON格式收益率数据"),
):
    try:
        import json
        pos = json.loads(positions)
        ret_data = json.loads(returns_data)
        ret_arrays = {k: np.array(v) for k, v in ret_data.items()}
        suggestions = portfolio_ai.suggest_rebalance(pos, ret_arrays)
        return _resp(True, data=[s.to_dict() for s in suggestions])
    except Exception as e:
        return _resp(False, msg=str(e))


@router.post("/portfolio/optimal-rebalance")
async def optimal_rebalance_plan(
    positions: str = Query(..., description="JSON格式持仓数据"),
    returns_data: str = Query(..., description="JSON格式收益率数据"),
    transaction_cost: float = Query(0.001),
):
    try:
        import json
        pos = json.loads(positions)
        ret_data = json.loads(returns_data)
        ret_arrays = {k: np.array(v) for k, v in ret_data.items()}
        plan = portfolio_ai.generate_rebalance_plan(pos, ret_arrays, transaction_cost)
        return _resp(True, data=plan)
    except Exception as e:
        return _resp(False, msg=str(e))


@router.post("/portfolio/daily-summary")
async def get_daily_summary(
    positions: str = Query(..., description="JSON格式持仓数据"),
    returns_data: str = Query(..., description="JSON格式收益率数据"),
):
    try:
        import json
        pos = json.loads(positions)
        ret_data = json.loads(returns_data)
        ret_arrays = {k: np.array(v) for k, v in ret_data.items()}
        summary = portfolio_ai.generate_daily_summary(pos, ret_arrays)
        return _resp(True, data=summary.to_dict())
    except Exception as e:
        return _resp(False, msg=str(e))


# ==================== 45 预测模型集成平台 ====================

@router.get("/prediction/models")
async def get_prediction_models():
    models = prediction_platform.get_available_models()
    return _resp(True, data=models)


@router.post("/prediction/train-lstm")
async def train_lstm(
    prices: str = Query(..., description="逗号分隔的价格序列"),
    lookback: int = Query(20),
):
    try:
        price_arr = np.array([float(p) for p in prices.split(",") if p.strip()])
        result = prediction_platform.train_model("lstm", price_arr, lookback=lookback)
        return _resp(result.get("success", False), data=result)
    except Exception as e:
        return _resp(False, msg=str(e))


@router.post("/prediction/train-garch")
async def train_garch(
    returns: str = Query(..., description="逗号分隔的收益率序列"),
    p: int = Query(1),
    q: int = Query(1),
):
    try:
        ret = np.array([float(r) for r in returns.split(",") if r.strip()])
        result = prediction_platform.train_model("garch", ret, p=p, q=q)
        return _resp(result.get("success", False), data=result)
    except Exception as e:
        return _resp(False, msg=str(e))


@router.post("/prediction/predict")
async def predict(
    model_name: str = Query(...),
    data: str = Query(..., description="逗号分隔的输入数据"),
    horizon: int = Query(5),
):
    try:
        input_data = np.array([float(d) for d in data.split(",") if d.strip()])
        result = prediction_platform.predict(model_name, input_data, horizon)
        return _resp(result.get("success", False), data=result)
    except Exception as e:
        return _resp(False, msg=str(e))


@router.post("/prediction/ab-test")
async def run_ab_test(
    model_a: str = Query(...),
    model_b: str = Query(...),
    test_data: str = Query(..., description="逗号分隔的测试数据"),
):
    try:
        data = np.array([float(d) for d in test_data.split(",") if d.strip()])
        result = prediction_platform.run_ab_test(model_a, model_b, data)
        return _resp(result.get("success", False), data=result)
    except Exception as e:
        return _resp(False, msg=str(e))


@router.get("/prediction/ab-results")
async def get_ab_results():
    result = prediction_platform.get_ab_results()
    return _resp(True, data=result)
