import logging
from typing import Optional

import numpy as np
from fastapi import APIRouter, Query, Request

from core.research.fundamental import FundamentalFactorLibrary
from core.research.sentiment import MarketSentimentAnalyzer
from core.research.sector import SectorResearch
from core.research.report_ai import ReportAIAssistant

logger = logging.getLogger(__name__)
research_router = APIRouter(prefix="/research", tags=["研究与分析"])


def _resp(success: bool, data=None, msg: str = ""):
    return {"code": 0 if success else 1, "data": data, "msg": msg}


@research_router.get("/notebook/status")
async def get_notebook_status():
    return _resp(True, data={
        "available": True,
        "packages": ["pandas", "numpy", "scipy", "scikit-learn", "matplotlib", "seaborn", "plotly", "akshare", "tushare", "yfinance"],
        "kernel": "python3",
        "message": "JupyterLab环境需单独启动: jupyter lab --port=8888",
    })


@research_router.post("/notebook/generate-template")
async def generate_notebook_template(
    template_type: str = Query("factor_research", description="模板类型"),
    symbol: str = Query("", description="股票代码"),
):
    templates = {
        "factor_research": {"cells": [
            {"type": "markdown", "content": "# 因子研究模板"},
            {"type": "code", "content": "from core.strategy_v2.factor_research import FactorResearchWorkbench\nworkbench = FactorResearchWorkbench()"},
        ]},
        "strategy_backtest": {"cells": [
            {"type": "markdown", "content": "# 策略回测模板"},
            {"type": "code", "content": "from core.backtest_v2.event_engine import EventBacktestEngine\nfrom core.strategies import DualMAStrategy"},
        ]},
        "ml_prediction": {"cells": [
            {"type": "markdown", "content": "# 机器学习预测模板"},
            {"type": "code", "content": "from core.ai.prediction_models import PredictionModelPlatform\nplatform = PredictionModelPlatform()"},
        ]},
    }
    template = templates.get(template_type)
    if template:
        return _resp(True, data=template)
    return _resp(False, msg=f"不支持的模板类型: {template_type}")


@research_router.get("/notebook/templates")
async def list_notebook_templates():
    return _resp(True, data=[
        {"id": "factor_research", "name": "因子研究", "description": "IC/IR分析与分层回测"},
        {"id": "strategy_backtest", "name": "策略回测", "description": "事件驱动回测引擎"},
        {"id": "ml_prediction", "name": "机器学习预测", "description": "LightGBM/XGBoost因子模型"},
    ])


@research_router.post("/fundamental/valuation")
async def calculate_valuation_factors(request: Request, data: str = Query(..., description="JSON格式财务数据")):
    import json
    try:
        financial = json.loads(data)
        result = request.app.state.fundamental_lib.calculate_valuation_factors(financial)
        return _resp(True, data=[f.to_dict() for f in result])
    except Exception as e:
        return _resp(False, msg=str(e))


@research_router.post("/fundamental/growth")
async def calculate_growth_factors(request: Request, data: str = Query(..., description="JSON格式财务数据")):
    import json
    try:
        financial = json.loads(data)
        result = request.app.state.fundamental_lib.calculate_growth_factors(financial)
        return _resp(True, data=[f.to_dict() for f in result])
    except Exception as e:
        return _resp(False, msg=str(e))


@research_router.post("/fundamental/health")
async def calculate_health_factors(request: Request, data: str = Query(..., description="JSON格式财务数据")):
    import json
    try:
        financial = json.loads(data)
        result = request.app.state.fundamental_lib.calculate_financial_health_factors(financial)
        return _resp(True, data=[f.to_dict() for f in result])
    except Exception as e:
        return _resp(False, msg=str(e))


@research_router.post("/fundamental/all")
async def calculate_all_factors(request: Request, data: str = Query(..., description="JSON格式财务数据")):
    import json
    try:
        financial = json.loads(data)
        result = request.app.state.fundamental_lib.calculate_all_factors(financial)
        return _resp(True, data=result)
    except Exception as e:
        return _resp(False, msg=str(e))


@research_router.post("/fundamental/compare-industry")
async def compare_with_industry(
    request: Request,
    factor_name: str = Query(...),
    factor_value: float = Query(...),
    industry: str = Query(...),
    industry_data: str = Query(..., description="JSON格式行业数据"),
):
    import json
    try:
        ind_data = json.loads(industry_data)
        result = request.app.state.fundamental_lib.compare_with_industry(factor_name, factor_value, industry, ind_data)
        return _resp(True, data=result)
    except Exception as e:
        return _resp(False, msg=str(e))


@research_router.get("/sentiment/analyze/{symbol}")
async def analyze_sentiment(request: Request, symbol: str):
    try:
        result = await request.app.state.sentiment_analyzer.analyze(symbol)
        if result:
            return _resp(True, data=result.to_dict())
        return _resp(False, msg="情绪数据获取失败")
    except Exception as e:
        return _resp(False, msg=str(e))


@research_router.get("/sentiment/margin-data")
async def get_margin_data(request: Request, symbol: str = Query("")):
    try:
        result = await request.app.state.sentiment_analyzer._fetch_margin_data(symbol)
        if result:
            return _resp(True, data=result)
        return _resp(False, msg="融资融券数据获取失败")
    except Exception as e:
        return _resp(False, msg=str(e))


@research_router.get("/sentiment/long-short")
async def get_long_short_data(request: Request):
    try:
        result = await request.app.state.sentiment_analyzer._fetch_long_short_data()
        if result:
            return _resp(True, data=result)
        return _resp(False, msg="多空数据暂不可用")
    except Exception as e:
        return _resp(False, msg=str(e))


@research_router.get("/sentiment/dragon-tiger/{symbol}")
async def get_dragon_tiger(request: Request, symbol: str):
    try:
        result = await request.app.state.sentiment_analyzer._fetch_dragon_tiger(symbol)
        if result:
            return _resp(True, data=result)
        return _resp(False, msg="龙虎榜数据暂不可用")
    except Exception as e:
        return _resp(False, msg=str(e))


@research_router.get("/sector/flows")
async def get_sector_flows(request: Request):
    try:
        result = await request.app.state.sector_research.get_sector_flows()
        return _resp(True, data=result)
    except Exception as e:
        return _resp(False, msg=str(e))


@research_router.get("/sector/concept-heat")
async def get_concept_heat(request: Request):
    try:
        result = await request.app.state.sector_research.get_concept_heat()
        return _resp(True, data=result)
    except Exception as e:
        return _resp(False, msg=str(e))


@research_router.get("/sector/rotation")
async def get_sector_rotation(request: Request, period: int = Query(20)):
    try:
        result = await request.app.state.sector_research.analyze_rotation(period)
        return _resp(True, data=result)
    except Exception as e:
        return _resp(False, msg=str(e))


@research_router.get("/sector/industry-chain")
async def get_industry_chain(request: Request, industry: str = Query("")):
    try:
        result = request.app.state.sector_research.analyze_industry_chain(industry)
        return _resp(True, data=result)
    except Exception as e:
        return _resp(False, msg=str(e))


@research_router.post("/report/upload")
async def upload_report(
    request: Request,
    title: str = Query(...),
    content: str = Query(..., description="研报文本内容"),
    source: str = Query(""),
):
    result = request.app.state.report_ai.process_text(title, content, source)
    return _resp(result.get("success", False), data=result)


@research_router.get("/report/list")
async def list_reports(request: Request, limit: int = Query(20)):
    reports = request.app.state.report_ai.list_reports(limit)
    return _resp(True, data=reports)


@research_router.get("/report/summary/{report_id}")
async def get_report_summary(request: Request, report_id: str):
    summary = request.app.state.report_ai.get_summary(report_id)
    if summary:
        return _resp(True, data=summary.to_dict())
    return _resp(False, msg="研报未找到")


@research_router.get("/report/aggregation")
async def get_report_aggregation(request: Request, symbol: str = Query(""), days: int = Query(30)):
    result = request.app.state.report_ai.get_aggregation(symbol, days)
    return _resp(True, data=result)


@research_router.get("/report/sentiment-trend")
async def get_report_sentiment_trend(request: Request, days: int = Query(30)):
    result = request.app.state.report_ai.get_sentiment_trend(days)
    return _resp(True, data=result)
