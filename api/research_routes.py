import logging
from typing import Optional

import numpy as np
from fastapi import APIRouter, Query

from core.research.fundamental import FundamentalFactorLibrary
from core.research.sentiment import MarketSentimentAnalyzer
from core.research.sector import SectorResearch
from core.research.report_ai import ReportAIAssistant

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/research", tags=["研究与分析"])

fundamental_lib = FundamentalFactorLibrary()
sentiment_analyzer = MarketSentimentAnalyzer()
sector_research = SectorResearch()
report_ai = ReportAIAssistant()


def _resp(success: bool, data=None, msg: str = ""):
    return {"code": 0 if success else 1, "data": data, "msg": msg}


# ==================== 36 量化研究Notebook环境 ====================

@router.get("/notebook/status")
async def get_notebook_status():
    return _resp(True, data={
        "available": True,
        "packages": [
            "pandas", "numpy", "scipy", "scikit-learn",
            "matplotlib", "seaborn", "plotly",
            "akshare", "tushare", "yfinance",
        ],
        "kernel": "python3",
        "message": "JupyterLab环境需单独启动: jupyter lab --port=8888",
    })


@router.post("/notebook/generate-template")
async def generate_notebook_template(
    template_type: str = Query("factor_research", description="模板类型"),
    symbol: str = Query("", description="股票代码"),
):
    templates = {
        "factor_research": {
            "cells": [
                {"type": "markdown", "content": "# 因子研究模板\n本模板用于单因子IC/IR分析和分层回测"},
                {"type": "code", "content": "from core.data_infra.data_adapter import UnifiedDataAdapter\nfrom core.strategy_v2.factor_research import FactorResearchWorkbench\nimport numpy as np\n\nadapter = UnifiedDataAdapter()\nworkbench = FactorResearchWorkbench()"},
                {"type": "code", "content": f"# 获取数据\ndf = await adapter.fetch_history('{symbol or '000001'}', 'A', '20200101', '20261231')\nprint(f'数据量: {{len(df)}}')"},
                {"type": "code", "content": "# 计算因子值\nfactor_values = df['close'].pct_change(20)  # 动量因子\nreturns = df['close'].pct_change().shift(-1)  # 未来收益\n\nresult = workbench.research_factor('momentum', factor_values.dropna().values, returns.dropna().values)\nprint(f'IC: {{result.ic:.4f}}, IR: {{result.ir:.4f}}')"},
            ],
        },
        "strategy_backtest": {
            "cells": [
                {"type": "markdown", "content": "# 策略回测模板"},
                {"type": "code", "content": "from core.backtest_v2.event_engine import EventBacktestEngine\nfrom core.strategies import DualMAStrategy\n\nengine = EventBacktestEngine()"},
                {"type": "code", "content": f"strategy = DualMAStrategy()\nresult = engine.run(strategy, df, '{symbol or '000001'}')\nprint(result)"},
            ],
        },
        "ml_prediction": {
            "cells": [
                {"type": "markdown", "content": "# 机器学习预测模板"},
                {"type": "code", "content": "from core.strategy_v2.ml_strategy import MLStrategyModule\nfrom core.ai.prediction_models import PredictionModelPlatform\n\nml = MLStrategyModule()\nplatform = PredictionModelPlatform()"},
            ],
        },
    }
    template = templates.get(template_type)
    if template:
        return _resp(True, data=template)
    return _resp(False, msg=f"不支持的模板类型: {template_type}")


@router.get("/notebook/templates")
async def list_notebook_templates():
    return _resp(True, data=[
        {"id": "factor_research", "name": "因子研究", "description": "IC/IR分析与分层回测"},
        {"id": "strategy_backtest", "name": "策略回测", "description": "事件驱动回测引擎"},
        {"id": "ml_prediction", "name": "机器学习预测", "description": "LightGBM/XGBoost因子模型"},
    ])


# ==================== 37 基本面因子库 ====================

@router.post("/fundamental/valuation")
async def calculate_valuation_factors(
    data: str = Query(..., description="JSON格式财务数据"),
):
    import json
    try:
        financial = json.loads(data)
        result = fundamental_lib.calculate_valuation_factors(financial)
        return _resp(True, data=result)
    except Exception as e:
        return _resp(False, msg=str(e))


@router.post("/fundamental/growth")
async def calculate_growth_factors(
    data: str = Query(..., description="JSON格式财务数据"),
):
    import json
    try:
        financial = json.loads(data)
        result = fundamental_lib.calculate_growth_factors(financial)
        return _resp(True, data=result)
    except Exception as e:
        return _resp(False, msg=str(e))


@router.post("/fundamental/health")
async def calculate_health_factors(
    data: str = Query(..., description="JSON格式财务数据"),
):
    import json
    try:
        financial = json.loads(data)
        result = fundamental_lib.calculate_financial_health_factors(financial)
        return _resp(True, data=result)
    except Exception as e:
        return _resp(False, msg=str(e))


@router.post("/fundamental/all")
async def calculate_all_factors(
    data: str = Query(..., description="JSON格式财务数据"),
):
    import json
    try:
        financial = json.loads(data)
        result = fundamental_lib.calculate_all_factors(financial)
        return _resp(True, data=result)
    except Exception as e:
        return _resp(False, msg=str(e))


@router.post("/fundamental/compare-industry")
async def compare_with_industry(
    factor_name: str = Query(...),
    factor_value: float = Query(...),
    industry: str = Query(...),
    industry_data: str = Query(..., description="JSON格式行业数据"),
):
    import json
    try:
        ind_data = json.loads(industry_data)
        result = fundamental_lib.compare_with_industry(factor_name, factor_value, industry, ind_data)
        return _resp(True, data=result)
    except Exception as e:
        return _resp(False, msg=str(e))


# ==================== 38 市场情绪分析 ====================

@router.get("/sentiment/analyze/{symbol}")
async def analyze_sentiment(symbol: str):
    try:
        result = await sentiment_analyzer.analyze(symbol)
        if result:
            return _resp(True, data=result.to_dict())
        return _resp(False, msg="情绪数据获取失败")
    except Exception as e:
        return _resp(False, msg=str(e))


@router.get("/sentiment/margin-data")
async def get_margin_data(symbol: str = Query("")):
    try:
        result = await sentiment_analyzer._fetch_margin_data(symbol)
        if result:
            return _resp(True, data=result)
        return _resp(False, msg="融资融券数据获取失败")
    except Exception as e:
        return _resp(False, msg=str(e))


@router.get("/sentiment/long-short")
async def get_long_short_data():
    try:
        result = await sentiment_analyzer._fetch_long_short_data()
        if result:
            return _resp(True, data=result)
        return _resp(False, msg="多空数据暂不可用")
    except Exception as e:
        return _resp(False, msg=str(e))


@router.get("/sentiment/dragon-tiger/{symbol}")
async def get_dragon_tiger(symbol: str):
    try:
        result = await sentiment_analyzer._fetch_dragon_tiger(symbol)
        if result:
            return _resp(True, data=result)
        return _resp(False, msg="龙虎榜数据暂不可用")
    except Exception as e:
        return _resp(False, msg=str(e))


# ==================== 39 板块与主题研究 ====================

@router.get("/sector/flows")
async def get_sector_flows():
    try:
        result = await sector_research.get_sector_flows()
        return _resp(True, data=result)
    except Exception as e:
        return _resp(False, msg=str(e))


@router.get("/sector/concept-heat")
async def get_concept_heat():
    try:
        result = await sector_research.get_concept_heat()
        return _resp(True, data=result)
    except Exception as e:
        return _resp(False, msg=str(e))


@router.get("/sector/rotation")
async def get_sector_rotation(period: int = Query(20)):
    try:
        result = await sector_research.analyze_rotation(period)
        return _resp(True, data=result)
    except Exception as e:
        return _resp(False, msg=str(e))


@router.get("/sector/industry-chain")
async def get_industry_chain(industry: str = Query("")):
    try:
        result = sector_research.analyze_industry_chain(industry)
        return _resp(True, data=result)
    except Exception as e:
        return _resp(False, msg=str(e))


# ==================== 40 研报摘要AI助手 ====================

@router.post("/report/upload")
async def upload_report(
    title: str = Query(...),
    content: str = Query(..., description="研报文本内容"),
    source: str = Query(""),
):
    result = report_ai.process_text(title, content, source)
    return _resp(result.get("success", False), data=result)


@router.get("/report/list")
async def list_reports(limit: int = Query(20)):
    reports = report_ai.list_reports(limit)
    return _resp(True, data=reports)


@router.get("/report/summary/{report_id}")
async def get_report_summary(report_id: str):
    summary = report_ai.get_summary(report_id)
    if summary:
        return _resp(True, data=summary.to_dict())
    return _resp(False, msg="研报未找到")


@router.get("/report/aggregation")
async def get_report_aggregation(symbol: str = Query(""), days: int = Query(30)):
    result = report_ai.get_aggregation(symbol, days)
    return _resp(True, data=result)


@router.get("/report/sentiment-trend")
async def get_report_sentiment_trend(days: int = Query(30)):
    result = report_ai.get_sentiment_trend(days)
    return _resp(True, data=result)
