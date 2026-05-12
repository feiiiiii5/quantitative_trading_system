from __future__ import annotations

import asyncio
import logging
import time

from fastapi import APIRouter, Query, Request
from pydantic import BaseModel, Field

from api.utils import json_response as _json_response
from api.utils import safe_error

logger = logging.getLogger(__name__)
router = APIRouter()


class StrategyParseRequest(BaseModel):
    strategy_name: str = Field(..., min_length=1, max_length=100)
    strategy_version: str = Field("1.0.0", max_length=20)
    asset_class: str = Field("spot", pattern=r"^(spot|futures|options|forex|crypto)$")
    timeframe: str = Field("1d", pattern=r"^(tick|1m|5m|15m|1h|4h|1d)$")
    market_type: str = Field("trend", pattern=r"^(trend|mean_reversion|momentum|arbitrage|market_making|ml_driven)$")
    parameters: dict = Field(default_factory=dict)
    indicators: list[dict] = Field(default_factory=list)
    signal_logic: dict = Field(default_factory=dict)
    risk_management: dict = Field(default_factory=dict)
    execution_model: dict = Field(default_factory=dict)


@router.post("/quantlab/parse-strategy")
async def parse_strategy(request: Request, body: StrategyParseRequest):
    try:
        from core.strategy_schema import (
            AssetClass,
            Timeframe,
            MarketType,
            StrategyDefinition,
            StrategyMeta,
            ParameterSpec,
            IndicatorSpec,
            SignalLogic,
            RiskManagement,
            ExecutionModel,
        )
        meta = StrategyMeta(
            name=body.strategy_name,
            version=body.strategy_version,
            asset_class=AssetClass(body.asset_class),
            timeframe=Timeframe(body.timeframe),
            market_type=MarketType(body.market_type),
        )
        params = {k: ParameterSpec(**v) for k, v in body.parameters.items()} if body.parameters else {}
        indicators = [IndicatorSpec(**ind) for ind in body.indicators] if body.indicators else []
        signals = SignalLogic(**body.signal_logic) if body.signal_logic else SignalLogic()
        risk = RiskManagement(**body.risk_management) if body.risk_management else RiskManagement()
        execution = ExecutionModel(**body.execution_model) if body.execution_model else ExecutionModel()

        definition = StrategyDefinition(
            strategy_meta=meta,
            parameters=params,
            indicators=indicators,
            signal_logic=signals,
            risk_management=risk,
            execution_model=execution,
        )
        return _json_response(True, data={
            "summary_card": definition.summary_card(),
            "min_bars_required": definition.min_bars_required(),
            "definition": definition.model_dump(),
        })
    except Exception as e:
        logger.error("Strategy parse error: %s", e)
        return _json_response(False, error=safe_error(e))


@router.post("/quantlab/diagnose")
async def diagnose_strategy(request: Request, body: dict):
    try:
        from core.backtest import BacktestEngine
        from core.backtest.enhanced_metrics import compute_comprehensive_metrics
        from core.strategy_schema import (
            AssetClass,
            Timeframe,
            MarketType,
            StrategyDefinition,
            StrategyMeta,
            ParameterSpec,
            IndicatorSpec,
            SignalLogic,
            RiskManagement,
            ExecutionModel,
        )
        from core.strategy_analyzer import analyze_backtest_result
        from core.strategies import STRATEGY_REGISTRY
        from core.data_fetcher import get_fetcher

        strategy_name = body.get("strategy", "")
        symbol = body.get("symbol", "")
        if strategy_name not in STRATEGY_REGISTRY:
            return _json_response(False, error=f"策略{strategy_name}不存在")

        fetcher = request.app.state.fetcher
        df = await fetcher.get_history(symbol, period="all", kline_type="daily", adjust="qfq")
        if df is None or len(df) < 60:
            return _json_response(False, error="数据不足")

        strategy_cls = STRATEGY_REGISTRY[strategy_name]
        strategy_instance = strategy_cls()
        n_params = len(strategy_instance.get_param_space()) if hasattr(strategy_instance, "get_param_space") else 0

        engine = BacktestEngine()
        result = await asyncio.to_thread(engine.run, strategy_instance, df, symbol)

        metrics = compute_comprehensive_metrics(
            equity_curve=result.equity_curve,
            dates=result.dates,
            trades=result.trades,
            initial_capital=1_000_000,
            n_params=n_params,
        )

        definition = StrategyDefinition(
            strategy_meta=StrategyMeta(
                name=strategy_name,
                market_type=MarketType.TREND,
            ),
        )
        analysis = analyze_backtest_result(definition, result.to_dict())

        quick_stats = {
            "total_return_pct": round(result.total_return, 2),
            "cagr_pct": round(result.annual_return, 2),
            "sharpe": round(result.sharpe_ratio, 2),
            "max_dd_pct": round(result.max_drawdown * 100, 2),
            "win_rate_pct": round(result.win_rate, 1),
        }

        return _json_response(True, data={
            "quick_stats": quick_stats,
            "comprehensive_metrics": {
                "returns": {k: v for k, v in metrics.returns.__dict__.items()},
                "risk": {k: v for k, v in metrics.risk.__dict__.items()},
                "risk_adjusted": {k: v for k, v in metrics.risk_adjusted.__dict__.items()},
                "trades": {k: v for k, v in metrics.trades.__dict__.items()},
                "distribution": {
                    "skewness": metrics.distribution.skewness,
                    "kurtosis": metrics.distribution.kurtosis,
                    "tail_ratio": metrics.distribution.tail_ratio,
                },
                "guardrail_warnings": metrics.guardrail_warnings,
            },
            "strategy_analysis": analysis,
            "disclaimer": "Past backtest results do not guarantee future performance. All metrics are subject to estimation error.",
        })
    except Exception as e:
        logger.error("Diagnose strategy error: %s", e)
        return _json_response(False, error=safe_error(e))


@router.post("/quantlab/analyze-strategy")
async def analyze_strategy_endpoint(request: Request, body: StrategyParseRequest):
    try:
        from core.strategy_schema import (
            AssetClass,
            Timeframe,
            MarketType,
            StrategyDefinition,
            StrategyMeta,
            ParameterSpec,
            IndicatorSpec,
            SignalLogic,
            RiskManagement,
            ExecutionModel,
        )
        from core.strategy_analyzer import analyze_strategy
        meta = StrategyMeta(
            name=body.strategy_name,
            version=body.strategy_version,
            asset_class=AssetClass(body.asset_class),
            timeframe=Timeframe(body.timeframe),
            market_type=MarketType(body.market_type),
        )
        params = {k: ParameterSpec(**v) for k, v in body.parameters.items()} if body.parameters else {}
        indicators = [IndicatorSpec(**v) for v in body.indicators] if body.indicators else []
        signals = SignalLogic(**body.signal_logic) if body.signal_logic else SignalLogic()
        risk = RiskManagement(**body.risk_management) if body.risk_management else RiskManagement()
        execution = ExecutionModel(**body.execution_model) if body.execution_model else ExecutionModel()
        definition = StrategyDefinition(
            strategy_meta=meta,
            parameters=params,
            indicators=indicators,
            signal_logic=signals,
            risk_management=risk,
            execution_model=execution,
        )
        analysis = analyze_strategy(definition)
        return _json_response(True, data={
            "edge_analysis": {
                "alpha_source": analysis.edge.alpha_source,
                "optimal_regime": analysis.edge.optimal_regime,
                "lookahead_bias_risks": analysis.edge.lookahead_bias_risks,
                "survivorship_bias_risks": analysis.edge.survivorship_bias_risks,
                "overfitting_risk": analysis.edge.overfitting_risk,
            },
            "indicator_dependencies": [
                {"name": d.name, "lookback": d.lookback, "min_bars_before_signal": d.min_bars_before_signal}
                for d in analysis.indicator_dependencies
            ],
            "regime_sensitivity": [
                {"regime": r.regime.value, "expected_sharpe": r.expected_sharpe,
                 "expected_return_pct": r.expected_return_pct, "expected_max_dd_pct": r.expected_max_dd_pct,
                 "confidence": r.confidence}
                for r in analysis.regime_sensitivity
            ],
            "weaknesses": [
                {"title": w.title, "description": w.description, "severity": w.severity, "mitigation": w.mitigation}
                for w in analysis.weaknesses
            ],
            "improvements": [
                {"title": i.title, "description": i.description, "expected_impact": i.expected_impact, "effort": i.implementation_effort}
                for i in analysis.improvements
            ],
        })
    except Exception as e:
        logger.error("Strategy analyze error: %s", e)
        return _json_response(False, error=safe_error(e))


@router.post("/quantlab/analyze-backtest")
async def analyze_backtest_endpoint(request: Request, body: dict):
    try:
        from core.strategy_schema import (
            AssetClass,
            Timeframe,
            MarketType,
            StrategyDefinition,
            StrategyMeta,
            ParameterSpec,
            IndicatorSpec,
            SignalLogic,
            RiskManagement,
            ExecutionModel,
        )
        from core.strategy_analyzer import analyze_backtest_result

        strategy_data = body.get("strategy", {})
        result_data = body.get("result", {})
        meta = StrategyMeta(
            name=strategy_data.get("name", "unknown"),
            asset_class=AssetClass(strategy_data.get("asset_class", "spot")),
            timeframe=Timeframe(strategy_data.get("timeframe", "1d")),
            market_type=MarketType(strategy_data.get("market_type", "trend")),
        )
        params = {k: ParameterSpec(**v) for k, v in strategy_data.get("parameters", {}).items()}
        indicators = [IndicatorSpec(**v) for v in strategy_data.get("indicators", [])]
        definition = StrategyDefinition(
            strategy_meta=meta,
            parameters=params,
            indicators=indicators,
            signal_logic=SignalLogic(**strategy_data.get("signal_logic", {})),
            risk_management=RiskManagement(**strategy_data.get("risk_management", {})),
            execution_model=ExecutionModel(**strategy_data.get("execution_model", {})),
        )
        analysis = analyze_backtest_result(definition, result_data)
        return _json_response(True, data=analysis)
    except Exception as e:
        logger.error("Backtest analysis error: %s", e)
        return _json_response(False, error=safe_error(e))


@router.get("/quantlab/comprehensive-metrics")
async def get_comprehensive_metrics(
    request: Request,
    symbol: str = Query(..., max_length=20),
    strategy: str = Query(..., max_length=50),
):
    try:
        from core.backtest import BacktestEngine
        from core.backtest.enhanced_metrics import compute_comprehensive_metrics
        from core.strategies import STRATEGY_REGISTRY
        from core.data_fetcher import get_fetcher

        if strategy not in STRATEGY_REGISTRY:
            return _json_response(False, error=f"策略{strategy}不存在")

        fetcher = request.app.state.fetcher
        df = await fetcher.get_history(symbol, period="all", kline_type="daily", adjust="qfq")
        if df is None or len(df) < 60:
            return _json_response(False, error="数据不足")

        engine = BacktestEngine()
        result = await asyncio.to_thread(engine.run, STRATEGY_REGISTRY[strategy](), df, symbol)
        metrics = compute_comprehensive_metrics(
            equity_curve=result.equity_curve,
            dates=result.dates,
            trades=result.trades,
            initial_capital=1_000_000,
        )
        return _json_response(True, data={
            "returns": {
                "total_return": metrics.returns.total_return,
                "cagr": metrics.returns.cagr,
                "buy_hold_return": metrics.returns.buy_hold_return,
                "alpha": metrics.returns.alpha,
                "exposure_time_pct": metrics.returns.exposure_time_pct,
            },
            "risk": {
                "max_drawdown": metrics.risk.max_drawdown,
                "max_drawdown_duration_days": metrics.risk.max_drawdown_duration_days,
                "avg_drawdown": metrics.risk.avg_drawdown,
                "annual_volatility": metrics.risk.annual_volatility,
                "downside_deviation": metrics.risk.downside_deviation,
                "var_95": metrics.risk.var_95,
                "cvar_95": metrics.risk.cvar_95,
            },
            "risk_adjusted": {
                "sharpe_ratio": metrics.risk_adjusted.sharpe_ratio,
                "sortino_ratio": metrics.risk_adjusted.sortino_ratio,
                "calmar_ratio": metrics.risk_adjusted.calmar_ratio,
                "omega_ratio": metrics.risk_adjusted.omega_ratio,
                "profit_factor": metrics.risk_adjusted.profit_factor,
            },
            "trades": {
                "total_trades": metrics.trades.total_trades,
                "win_rate": metrics.trades.win_rate,
                "avg_win_avg_loss": metrics.trades.avg_win_avg_loss,
                "expectancy": metrics.trades.expectancy,
                "avg_trade_duration": metrics.trades.avg_trade_duration,
                "max_consecutive_wins": metrics.trades.max_consecutive_wins,
                "max_consecutive_losses": metrics.trades.max_consecutive_losses,
                "trades_per_year": metrics.trades.trades_per_year,
            },
            "distribution": {
                "skewness": metrics.distribution.skewness,
                "kurtosis": metrics.distribution.kurtosis,
                "tail_ratio": metrics.distribution.tail_ratio,
                "monthly_return_heatmap": metrics.distribution.monthly_return_heatmap,
                "return_histogram": metrics.distribution.return_histogram,
            },
            "guardrail_warnings": metrics.guardrail_warnings,
            "disclaimer": "Past backtest results do not guarantee future performance. All metrics are subject to estimation error.",
        })
    except Exception as e:
        logger.error("Comprehensive metrics error: %s", e)
        return _json_response(False, error=safe_error(e))


@router.post("/quantlab/walk-forward")
async def walk_forward_analysis_endpoint(request: Request, body: dict):
    try:
        from core.backtest import BacktestEngine
        from core.backtest.optimization import walk_forward_analysis
        from core.strategies import STRATEGY_REGISTRY
        from core.data_fetcher import get_fetcher

        strategy_name = body.get("strategy", "")
        symbol = body.get("symbol", "")
        is_window = body.get("is_window", 252)
        oos_window = body.get("oos_window", 63)

        if strategy_name not in STRATEGY_REGISTRY:
            return _json_response(False, error=f"策略{strategy_name}不存在")

        fetcher = request.app.state.fetcher
        df = await fetcher.get_history(symbol, period="all", kline_type="daily", adjust="qfq")
        if df is None or len(df) < is_window + oos_window:
            return _json_response(False, error="数据不足")

        engine = BacktestEngine()
        result = await asyncio.to_thread(
            walk_forward_analysis,
            engine, STRATEGY_REGISTRY[strategy_name], df,
            is_window=is_window, oos_window=oos_window,
        )
        return _json_response(True, data=result)
    except Exception as e:
        logger.error("Walk-forward analysis error: %s", e)
        return _json_response(False, error=safe_error(e))


@router.post("/quantlab/compare-strategies")
async def compare_strategies(request: Request, body: dict):
    try:
        from core.backtest import BacktestEngine
        from core.strategies import STRATEGY_REGISTRY
        from core.data_fetcher import get_fetcher

        symbol = body.get("symbol", "")
        strategy_names = body.get("strategies", [])
        if not strategy_names:
            return _json_response(False, error="请提供策略列表")

        fetcher = request.app.state.fetcher
        df = await fetcher.get_history(symbol, period="all", kline_type="daily", adjust="qfq")
        if df is None or len(df) < 60:
            return _json_response(False, error="数据不足")

        results = []
        for name in strategy_names[:10]:
            if name not in STRATEGY_REGISTRY:
                continue
            try:
                engine = BacktestEngine()
                result = await asyncio.to_thread(engine.run, STRATEGY_REGISTRY[name](), df, symbol)
                summary = result.get_performance_summary()
                summary["sharpe_per_dd"] = round(result.sharpe_ratio / max(result.max_drawdown, 1e-9), 2)
                results.append(summary)
            except Exception as e:
                logger.debug("Compare strategy %s failed: %s", name, e)

        results.sort(key=lambda x: x.get("sharpe", 0), reverse=True)
        pareto = min(results, key=lambda x: -x.get("sharpe_per_dd", 0)) if results else None
        return _json_response(True, data={
            "comparison": results,
            "pareto_optimal": pareto,
            "ranked_by": "sharpe_ratio",
        })
    except Exception as e:
        logger.error("Strategy comparison error: %s", e)
        return _json_response(False, error=safe_error(e))
