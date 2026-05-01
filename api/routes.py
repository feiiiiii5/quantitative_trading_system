"""
QuantCore API路由模块
提供REST API和WebSocket实时推送
"""
import asyncio
import json
import logging
import time
import uuid
from datetime import datetime
from functools import wraps
from typing import Optional, Set

from fastapi import APIRouter, Query, Request, WebSocket, WebSocketDisconnect
import numpy as np
import pandas as pd

from core.data_fetcher import SmartDataFetcher
from core.database import ThreadSafeLRU
from core.market_detector import MarketDetector
from core.market_hours import MarketHours

logger = logging.getLogger(__name__)

router = APIRouter()


class ConnectionManager:
    """WebSocket连接管理器"""

    def __init__(self):
        self.connections: list[WebSocket] = []
        self._subscriptions: dict[WebSocket, Set[str]] = {}

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.connections.append(ws)
        self._subscriptions[ws] = set()

    def disconnect(self, ws: WebSocket):
        if ws in self.connections:
            self.connections.remove(ws)
        self._subscriptions.pop(ws, None)

    def subscribe(self, ws: WebSocket, symbols: list[str]):
        if ws in self._subscriptions:
            self._subscriptions[ws].update(symbols)

    def unsubscribe(self, ws: WebSocket, symbols: list[str]):
        if ws in self._subscriptions:
            self._subscriptions[ws] -= set(symbols)

    def get_all_subscribed_symbols(self) -> Set[str]:
        all_symbols: Set[str] = set()
        for symbols in self._subscriptions.values():
            all_symbols.update(symbols)
        return all_symbols


_manager = ConnectionManager()
_api_response_cache = ThreadSafeLRU(maxsize=300, ttl=30)


def _is_trading_hours() -> bool:
    try:
        for market in ["A", "HK", "US"]:
            status = MarketHours.get_market_status(market)
            if status.get("is_open"):
                return True
    except Exception:
        pass
    return False


def _sanitize(obj):
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        return float(obj)
    if isinstance(obj, (np.bool_,)):
        return bool(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, dict):
        return {k: _sanitize(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_sanitize(v) for v in obj]
    return obj


def _json_response(success: bool, data=None, error: str = ""):
    return {"success": success, "data": _sanitize(data), "error": error}


def cache_response(ttl_seconds: int):
    def decorator(func):
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            cache_key = f"api:{func.__name__}:{request.url.path}:{request.url.query}"
            cached = _api_response_cache.get(cache_key)
            if cached is not None:
                return cached
            result = await func(request, *args, **kwargs)
            _api_response_cache.set(cache_key, result, ttl=ttl_seconds)
            return result
        return wrapper
    return decorator


@router.get("/market/overview")
@cache_response(5)
async def get_market_overview(request: Request):
    try:
        fetcher: SmartDataFetcher = request.app.state.fetcher
        data = await fetcher.get_market_overview()
        return _json_response(True, data=data)
    except Exception as e:
        logger.error(f"Market overview error: {e}")
        return _json_response(False, error=str(e))


@router.get("/market/status")
@cache_response(60)
async def get_market_status(request: Request):
    try:
        statuses = {}
        for market in ["A", "HK", "US"]:
            statuses[market] = MarketHours.get_market_status(market)
        return _json_response(True, data=statuses)
    except Exception as e:
        return _json_response(False, error=str(e))


@router.get("/stock/realtime/{symbol}")
async def get_stock_realtime(request: Request, symbol: str):
    try:
        fetcher: SmartDataFetcher = request.app.state.fetcher
        data = await fetcher.get_realtime(symbol)
        if data:
            return _json_response(True, data=data)
        return _json_response(False, error="未获取到数据")
    except Exception as e:
        return _json_response(False, error=str(e))


@router.get("/stock/history/{symbol}")
async def get_stock_history(
    request: Request,
    symbol: str,
    period: str = Query("1y"),
    kline_type: str = Query("daily"),
    adjust: str = Query(""),
):
    try:
        fetcher: SmartDataFetcher = request.app.state.fetcher
        df = await fetcher.get_history(symbol, period, kline_type, adjust)
        if df.empty:
            return _json_response(False, error="无历史数据")
        result = df.to_dict("records")
        return _json_response(True, data=result)
    except Exception as e:
        return _json_response(False, error=str(e))


@router.get("/stock/fundamentals/{symbol}")
@cache_response(3600)
async def get_stock_fundamentals(request: Request, symbol: str):
    try:
        fetcher: SmartDataFetcher = request.app.state.fetcher
        market = MarketDetector.detect(symbol)
        data = await fetcher.get_fundamentals(symbol, market)
        if data:
            return _json_response(True, data=data)
        return _json_response(False, error="无基本面数据")
    except Exception as e:
        return _json_response(False, error=str(e))


@router.get("/stock/indicators/{symbol}")
async def get_stock_indicators(
    request: Request,
    symbol: str,
    period: str = Query("1y"),
    kline_type: str = Query("daily"),
):
    try:
        fetcher: SmartDataFetcher = request.app.state.fetcher
        df = await fetcher.get_history(symbol, period, kline_type)
        if df.empty or len(df) < 30:
            return _json_response(False, error="数据不足")
        from core.indicators import calc_all_indicators
        kline_data = df.to_dict("records")
        result = calc_all_indicators(kline_data)
        return _json_response(True, data=result)
    except Exception as e:
        logger.error(f"Indicators error: {e}")
        return _json_response(False, error=str(e))


def _period_to_history(period: str) -> str:
    period = (period or "1y").lower()
    if period in {"3m", "6m"}:
        return "1y"
    if period in {"3y", "5y", "all"}:
        return "all"
    return "1y"


@router.get("/stock/analysis/{symbol}")
async def get_deep_analysis(request: Request, symbol: str, period: str = Query("1y")):
    try:
        from core.indicators import IndicatorAnalysis, KLinePatternRecognizer, TechnicalIndicators
        fetcher: SmartDataFetcher = request.app.state.fetcher
        df = await fetcher.get_history(symbol, _period_to_history(period), "daily", "qfq")
        if df.empty or len(df) < 60:
            return _json_response(False, error="数据不足，至少需要60个交易日")

        df = df.tail(260).copy().reset_index(drop=True)
        c = df["close"].astype(float)
        h = df["high"].astype(float)
        l = df["low"].astype(float)
        v = df["volume"].astype(float) if "volume" in df.columns else None
        indicators = TechnicalIndicators.compute_all(df, symbol=symbol, period=period)
        ma = indicators.get("ma", {})
        ma20 = ma.get(20, [])
        ma60 = ma.get(60, [])
        last_close = float(c.iloc[-1])
        trend_slope = 0.0
        if len(ma20) >= 20:
            trend_slope = float(ma20[-1] - ma20[-20]) / max(abs(float(ma20[-20])), 1e-9)
        direction = "up" if trend_slope > 0.02 else "down" if trend_slope < -0.02 else "sideways"
        strength = min(100, abs(trend_slope) * 1200 + abs(indicators.get("trend_score", 0)) * 0.5)
        support_resistance = IndicatorAnalysis.support_resistance(df)
        volume_analysis = IndicatorAnalysis.volume_price_analysis(df)
        patterns = KLinePatternRecognizer.recognize(df.tail(80))

        rsi_data = indicators.get("rsi", {}).get(12, [])
        rsi_val = float(rsi_data[-1]) if rsi_data else 50.0
        macd = indicators.get("macd", {})
        dif = macd.get("dif", [0])[-1] if macd.get("dif") else 0
        dea = macd.get("dea", [0])[-1] if macd.get("dea") else 0
        kdj = indicators.get("kdj", {})
        k_val = kdj.get("k", [50])[-1] if kdj.get("k") else 50
        d_val = kdj.get("d", [50])[-1] if kdj.get("d") else 50

        low_120 = float(l.tail(120).min())
        high_120 = float(h.tail(120).max())
        fib_ratios = [0.236, 0.382, 0.5, 0.618, 0.786]
        fib = [round(high_120 - (high_120 - low_120) * r, 4) for r in fib_ratios]
        composite_score = float(indicators.get("trend_score", 0))
        signal = indicators.get("signal", "neutral")
        confidence = min(100, abs(composite_score) + 35)

        result = {
            "trend": {
                "direction": direction,
                "strength": round(float(strength), 2),
                "duration_days": int(min(len(df), 260)),
                "key_levels": {
                    "support": support_resistance.get("supports", []),
                    "resistance": support_resistance.get("resistances", []),
                },
            },
            "momentum": {
                "rsi_signal": "overbought" if rsi_val > 70 else "oversold" if rsi_val < 30 else "neutral",
                "macd_signal": "bullish" if dif > dea else "bearish" if dif < dea else "neutral",
                "kdj_signal": "bullish" if k_val > d_val else "bearish" if k_val < d_val else "neutral",
                "composite_momentum": round(float(composite_score / 100), 4),
            },
            "volume": {
                "trend": "accumulation" if volume_analysis.get("obv_trend", 0) > 0 else "distribution" if volume_analysis.get("obv_trend", 0) < 0 else "neutral",
                "obv_divergence": bool(indicators.get("rsi_divergence", {}).get("top_divergence")),
                "volume_ratio_5d": volume_analysis.get("volume_ratio", 0),
            },
            "patterns": patterns[-10:],
            "ichimoku": indicators.get("ichimoku", {}),
            "fibonacci_levels": [{"ratio": r, "price": p} for r, p in zip(fib_ratios, fib)],
            "composite_score": round(composite_score, 2),
            "signal": signal,
            "signal_confidence": round(float(confidence), 2),
            "last_price": round(last_close, 4),
        }
        return _json_response(True, data=result)
    except Exception as e:
        logger.error(f"Deep analysis error for {symbol}: {e}", exc_info=True)
        return _json_response(False, error=str(e))


@router.get("/stock/correlation/{symbol}")
async def get_correlation_analysis(
    request: Request,
    symbol: str,
    benchmark: str = Query("sh000300"),
    period: str = Query("1y"),
):
    try:
        fetcher: SmartDataFetcher = request.app.state.fetcher
        df = await fetcher.get_history(symbol, _period_to_history(period), "daily", "qfq")
        bench_df = await fetcher.get_history(benchmark, _period_to_history(period), "daily", "qfq")
        if df.empty or bench_df.empty:
            return _json_response(False, error="数据不足")
        left = df[["date", "close"]].rename(columns={"close": "asset_close"})
        right = bench_df[["date", "close"]].rename(columns={"close": "benchmark_close"})
        merged = left.merge(right, on="date", how="inner").tail(260)
        if len(merged) < 30:
            return _json_response(False, error="重叠数据不足")
        ar = merged["asset_close"].astype(float).pct_change()
        br = merged["benchmark_close"].astype(float).pct_change()
        rolling_corr = ar.rolling(60).corr(br).fillna(0)
        beta = float(np.cov(ar.dropna().tail(120), br.dropna().tail(120))[0][1] / np.var(br.dropna().tail(120))) if np.var(br.dropna().tail(120)) > 0 else 1.0
        asset_ret = merged["asset_close"].iloc[-1] / merged["asset_close"].iloc[0] - 1
        bench_ret = merged["benchmark_close"].iloc[-1] / merged["benchmark_close"].iloc[0] - 1
        return _json_response(True, data={
            "rolling_correlation": [{"date": str(d)[:10], "value": round(float(v), 4)} for d, v in zip(merged["date"], rolling_corr)],
            "beta": round(beta, 4),
            "alpha": round(float(asset_ret - beta * bench_ret), 4),
            "relative_strength": round(float(asset_ret - bench_ret), 4),
            "stability_score": round(float(100 - rolling_corr.tail(120).std() * 100), 2),
        })
    except Exception as e:
        return _json_response(False, error=str(e))


@router.get("/stock/prediction/{symbol}")
@cache_response(120)
async def get_stock_prediction(request: Request, symbol: str, period: str = Query("1y")):
    """AI预测接口 - 基于技术指标和统计模型"""
    try:
        from core.indicators import TechnicalIndicators
        fetcher: SmartDataFetcher = request.app.state.fetcher
        df = await fetcher.get_history(symbol, _period_to_history(period), "daily", "qfq")
        if df.empty or len(df) < 60:
            return _json_response(False, error="数据不足")
        df = df.tail(260).copy().reset_index(drop=True)
        c = df["close"].astype(float).values
        h = df["high"].astype(float).values
        l = df["low"].astype(float).values
        v = df["volume"].astype(float).values

        indicators = TechnicalIndicators.compute_all(df, symbol=symbol, period=period)
        trend_score = indicators.get("trend_score", 0)
        signal = indicators.get("signal", "neutral")

        # 简单统计预测：基于近期趋势+波动率
        returns = np.diff(c) / np.where(c[:-1] > 0, c[:-1], 1)
        returns = returns[np.isfinite(returns)]
        if len(returns) < 20:
            return _json_response(False, error="数据不足")
        recent_ret = returns[-20:]
        avg_ret = float(np.mean(recent_ret))
        std_ret = float(np.std(recent_ret))
        last_price = float(c[-1])

        # 5日/10日/20日预测
        predictions = {}
        for days, label in [(5, "5d"), (10, "10d"), (20, "20d")]:
            drift = avg_ret * days
            vol = std_ret * np.sqrt(days)
            pred_price = last_price * (1 + drift)
            pred_upper = last_price * (1 + drift + 1.96 * vol)
            pred_lower = last_price * (1 + drift - 1.96 * vol)
            confidence = max(0.1, min(0.9, 1.0 - vol / max(abs(drift), 0.01)))
            predictions[label] = {
                "price": round(pred_price, 2),
                "upper": round(pred_upper, 2),
                "lower": round(pred_lower, 2),
                "confidence": round(confidence, 2),
                "direction": "up" if drift > 0 else "down",
            }

        # 综合信号
        composite_signal = "bullish" if trend_score > 20 else "bearish" if trend_score < -20 else "neutral"
        composite_confidence = min(0.95, abs(trend_score) / 100 + 0.3)

        return _json_response(True, data={
            "symbol": symbol,
            "last_price": round(last_price, 2),
            "predictions": predictions,
            "composite_signal": composite_signal,
            "composite_confidence": round(composite_confidence, 2),
            "trend_score": round(float(trend_score), 2),
            "technical_signal": signal,
            "volatility_annual": round(float(std_ret * np.sqrt(252)), 4),
            "timestamp": time.time(),
        })
    except Exception as e:
        logger.error(f"Prediction error for {symbol}: {e}")
        return _json_response(False, error=str(e))


@router.get("/stock/signals/{symbol}")
async def get_stock_signals(
    request: Request,
    symbol: str,
    period: str = Query("1y"),
    strategy: str = Query("all"),
):
    """获取股票策略信号历史"""
    try:
        from core.strategies import STRATEGY_REGISTRY, CompositeStrategy
        fetcher: SmartDataFetcher = request.app.state.fetcher
        df = await fetcher.get_history(symbol, _period_to_history(period), "daily", "qfq")
        if df.empty or len(df) < 30:
            return _json_response(False, error="数据不足")

        composite = CompositeStrategy()
        signals = []
        step = max(1, len(df) // 50)

        for i in range(30, len(df), step):
            segment = df.iloc[:i + 1]
            date_str = str(df["date"].iloc[i])[:10] if "date" in df.columns else ""
            bar_signals = []
            for s in composite.strategies:
                if strategy != "all" and type(s).__name__ != strategy:
                    continue
                try:
                    sig = s.generate_signal(segment)
                    if sig.signal_type.value != "hold":
                        bar_signals.append({
                            "strategy": type(s).__name__,
                            "signal": sig.signal_type.value,
                            "confidence": round(sig.strength, 2),
                            "reason": sig.reason,
                        })
                except Exception:
                    pass
            if bar_signals:
                signals.append({
                    "date": date_str,
                    "price": round(float(df["close"].iloc[i]), 2),
                    "signals": bar_signals,
                })

        return _json_response(True, data={"symbol": symbol, "signals": signals})
    except Exception as e:
        return _json_response(False, error=str(e))


@router.get("/portfolio/risk_analysis")
async def get_portfolio_risk_analysis(
    request: Request,
    symbols: str = Query(..., description="逗号分隔的股票代码"),
    period: str = Query("1y"),
):
    """组合风险分析 - CVaR/VaR/相关性矩阵"""
    try:
        fetcher: SmartDataFetcher = request.app.state.fetcher
        symbol_list = [s.strip() for s in symbols.split(",") if s.strip()]
        if not symbol_list:
            return _json_response(False, error="请提供股票代码")

        all_returns = {}
        for sym in symbol_list[:10]:
            try:
                df = await fetcher.get_history(sym, _period_to_history(period), "daily", "qfq")
                if df.empty or len(df) < 30:
                    continue
                c = df["close"].astype(float)
                ret = c.pct_change().dropna()
                ret = ret[np.isfinite(ret)]
                all_returns[sym] = ret.values[-120:]
            except Exception:
                continue

        if len(all_returns) < 2:
            return _json_response(False, error="有效数据不足")

        min_len = min(len(v) for v in all_returns.values())
        ret_matrix = np.column_stack([v[-min_len:] for v in all_returns.values()])
        sym_list = list(all_returns.keys())

        # 相关性矩阵
        corr_matrix = np.corrcoef(ret_matrix.T)
        correlation = {}
        for i, s1 in enumerate(sym_list):
            correlation[s1] = {}
            for j, s2 in enumerate(sym_list):
                correlation[s1][s2] = round(float(corr_matrix[i][j]), 4)

        # 等权组合VaR/CVaR
        weights = np.ones(len(sym_list)) / len(sym_list)
        port_returns = ret_matrix @ weights
        var_95 = float(np.percentile(port_returns, 5))
        cvar_95 = float(np.mean(port_returns[port_returns <= var_95]))
        port_vol = float(np.std(port_returns) * np.sqrt(252))
        port_sharpe = float(np.mean(port_returns) * 252 / (port_vol)) if port_vol > 0 else 0

        # 个股风险贡献
        risk_contribution = {}
        for i, sym in enumerate(sym_list):
            marginal = float(np.cov(ret_matrix[:, i], port_returns)[0][1] / np.var(port_returns)) if np.var(port_returns) > 0 else 0
            risk_contribution[sym] = round(float(weights[i] * marginal * port_vol), 4)

        return _json_response(True, data={
            "symbols": sym_list,
            "correlation_matrix": correlation,
            "portfolio_var_95": round(var_95, 4),
            "portfolio_cvar_95": round(cvar_95, 4),
            "portfolio_volatility": round(port_vol, 4),
            "portfolio_sharpe": round(port_sharpe, 2),
            "risk_contribution": risk_contribution,
        })
    except Exception as e:
        logger.error(f"Portfolio risk analysis error: {e}")
        return _json_response(False, error=str(e))


@router.get("/portfolio/attribution")
async def get_portfolio_attribution(
    request: Request,
    symbols: str = Query(..., description="逗号分隔的股票代码"),
    benchmark: str = Query("sh000300"),
    period: str = Query("1y"),
):
    """组合收益归因分析"""
    try:
        fetcher: SmartDataFetcher = request.app.state.fetcher
        symbol_list = [s.strip() for s in symbols.split(",") if s.strip()]
        if not symbol_list:
            return _json_response(False, error="请提供股票代码")

        bench_df = await fetcher.get_history(benchmark, _period_to_history(period), "daily", "qfq")
        if bench_df.empty:
            return _json_response(False, error="基准数据不足")
        bench_ret = bench_df["close"].astype(float).pct_change().dropna().values[-120:]

        attribution = {}
        for sym in symbol_list[:10]:
            try:
                df = await fetcher.get_history(sym, _period_to_history(period), "daily", "qfq")
                if df.empty or len(df) < 30:
                    continue
                c = df["close"].astype(float)
                ret = c.pct_change().dropna().values[-120:]
                min_len = min(len(ret), len(bench_ret))
                if min_len < 20:
                    continue
                r = ret[-min_len:]
                b = bench_ret[-min_len:]
                total_ret = float(np.prod(1 + r) - 1)
                bench_total = float(np.prod(1 + b) - 1)
                beta = float(np.cov(r, b)[0][1] / np.var(b)) if np.var(b) > 0 else 1.0
                alpha = total_ret - beta * bench_total
                systematic = beta * bench_total
                idiosyncratic = total_ret - systematic
                attribution[sym] = {
                    "total_return": round(total_ret, 4),
                    "systematic_return": round(systematic, 4),
                    "idiosyncratic_return": round(idiosyncratic, 4),
                    "alpha": round(alpha, 4),
                    "beta": round(beta, 4),
                }
            except Exception:
                continue

        return _json_response(True, data={
            "benchmark": benchmark,
            "benchmark_return": round(float(np.prod(1 + bench_ret) - 1), 4),
            "attribution": attribution,
        })
    except Exception as e:
        return _json_response(False, error=str(e))


@router.get("/report/weekly")
@cache_response(3600)
async def get_weekly_report(request: Request):
    """周报生成接口"""
    try:
        fetcher: SmartDataFetcher = request.app.state.fetcher
        overview = await fetcher.get_market_overview()
        cn = overview.get("cn_indices", {})

        # 市场概况
        market_summary = {}
        for name, info in cn.items():
            if isinstance(info, dict):
                market_summary[name] = {
                    "price": info.get("price", 0),
                    "change_pct": info.get("change_pct", 0),
                }

        # 板块表现
        heatmap_data = {}
        try:
            import akshare as ak
            df = await asyncio.to_thread(ak.stock_board_industry_name_em)
            if df is not None and not df.empty:
                top_gainers = []
                top_losers = []
                for _, row in df.iterrows():
                    name = str(row.get("板块名称", row.get("名称", "")))
                    pct = float(row.get("涨跌幅", 0) or 0)
                    if pct > 0:
                        top_gainers.append({"name": name, "change_pct": round(pct, 2)})
                    else:
                        top_losers.append({"name": name, "change_pct": round(pct, 2)})
                top_gainers.sort(key=lambda x: x["change_pct"], reverse=True)
                top_losers.sort(key=lambda x: x["change_pct"])
                heatmap_data = {
                    "top_gainers": top_gainers[:5],
                    "top_losers": top_losers[:5],
                }
        except Exception:
            heatmap_data = {"top_gainers": [], "top_losers": []}

        # 北向资金
        northbound = {}
        try:
            northbound = await fetcher.fetch_north_bound_flow()
        except Exception:
            pass

        report_date = datetime.now().strftime("%Y-%m-%d")
        return _json_response(True, data={
            "report_date": report_date,
            "market_summary": market_summary,
            "sector_performance": heatmap_data,
            "northbound_flow": northbound,
            "generated_at": time.time(),
        })
    except Exception as e:
        logger.error(f"Weekly report error: {e}")
        return _json_response(False, error=str(e))


@router.get("/market/stocks")
@cache_response(30)
async def get_market_stocks(request: Request, market: str = Query("A"), limit: int = Query(5000)):
    try:
        from core.market_data import fetch_all_a_stocks_async
        stocks = await fetch_all_a_stocks_async()
        if stocks:
            df_data = stocks
            if market == "sh":
                df_data = [s for s in df_data if s.get("symbol", "").startswith("6") and not s.get("symbol", "").startswith("688")]
            elif market == "sz":
                df_data = [s for s in df_data if s.get("symbol", "").startswith("0")]
            elif market == "cy":
                df_data = [s for s in df_data if s.get("symbol", "").startswith("3")]
            elif market == "kc":
                df_data = [s for s in df_data if s.get("symbol", "").startswith("688")]
            result = df_data[:limit]
            return _json_response(True, data=result)
    except Exception as e:
        logger.debug(f"Market stocks EastMoney error: {e}")
    try:
        import akshare as ak
        df = await asyncio.to_thread(ak.stock_zh_a_spot_em)
        if df is None or df.empty:
            return _json_response(True, data=[])
        col_map = {
            "代码": "symbol", "名称": "name", "最新价": "price",
            "涨跌幅": "change_pct", "成交量": "volume", "成交额": "amount",
            "换手率": "turnover_rate",
        }
        rename = {k: v for k, v in col_map.items() if k in df.columns}
        df = df.rename(columns=rename)
        if market == "sh":
            df = df[df["symbol"].str.startswith("6")]
        elif market == "sz":
            df = df[df["symbol"].str.startswith("0")]
        elif market == "cy":
            df = df[df["symbol"].str.startswith("3")]
        elif market == "kc":
            df = df[df["symbol"].str.startswith("688")]
        if "amount" in df.columns:
            df = df.sort_values("amount", ascending=False)
        df = df.head(limit)
        keep_cols = [c for c in ["symbol", "name", "price", "change_pct", "volume", "amount", "turnover_rate"] if c in df.columns]
        result = df[keep_cols].fillna(0).to_dict("records")
        return _json_response(True, data=result)
    except Exception as e:
        logger.debug(f"Market stocks fallback: {e}")
        return _json_response(True, data=[])


@router.get("/market/anomaly")
@cache_response(30)
async def get_market_anomaly(request: Request):
    try:
        from core.market_data import fetch_all_a_stocks_async
        stocks = await fetch_all_a_stocks_async()
        if not stocks:
            return _json_response(True, data=[])
        anomalies = []
        for s in stocks:
            change_pct = float(s.get("change_pct", 0) or 0)
            volume_ratio = float(s.get("volume_ratio", 0) or 0)
            reason = ""
            if change_pct > 9.8:
                reason = "涨停"
            elif change_pct < -9.8:
                reason = "跌停"
            elif change_pct > 8 and volume_ratio > 3:
                reason = "大涨放量"
            elif change_pct < -8 and volume_ratio > 3:
                reason = "大跌放量"
            elif change_pct > 5 and volume_ratio > 5:
                reason = "放量拉升"
            elif change_pct < -5 and volume_ratio > 5:
                reason = "放量下跌"
            if reason:
                anomalies.append({
                    "symbol": s.get("symbol", ""),
                    "name": s.get("name", ""),
                    "price": round(float(s.get("price", 0) or 0), 2),
                    "change_pct": round(change_pct, 2),
                    "volume_ratio": round(volume_ratio, 2),
                    "reason": reason,
                })
        anomalies.sort(key=lambda x: abs(x["change_pct"]), reverse=True)
        return _json_response(True, data=anomalies[:80])
    except Exception as e:
        logger.debug(f"Market anomaly error: {e}")
        return _json_response(True, data=[])


@router.get("/market/heatmap")
@cache_response(30)
async def get_market_heatmap(request: Request, market: str = Query("A")):
    try:
        import akshare as ak
        df = await asyncio.to_thread(ak.stock_board_industry_name_em)
        items = []
        if df is not None and not df.empty:
            for _, row in df.iterrows():
                name = str(row.get("板块名称", row.get("名称", "")))
                pct = float(row.get("涨跌幅", 0) or 0)
                amount = float(row.get("成交额", row.get("总市值", 0)) or 0)
                lead = str(row.get("领涨股票", ""))
                items.append({
                    "name": name,
                    "change_pct": round(pct, 2),
                    "amount": amount,
                    "value": max(amount, 1),
                    "leader": lead,
                })
        return _json_response(True, data={"market": market, "items": items, "timestamp": time.time()})
    except Exception as e:
        logger.debug(f"Market heatmap fallback: {e}")
        fallback = [
            {"name": "银行", "change_pct": 0, "amount": 1, "value": 1, "leader": ""},
            {"name": "科技", "change_pct": 0, "amount": 1, "value": 1, "leader": ""},
            {"name": "医药", "change_pct": 0, "amount": 1, "value": 1, "leader": ""},
            {"name": "消费", "change_pct": 0, "amount": 1, "value": 1, "leader": ""},
        ]
        return _json_response(True, data={"market": market, "items": fallback, "timestamp": time.time()})


@router.get("/market/northbound/detail")
@cache_response(60)
async def get_northbound_detail(request: Request):
    try:
        fetcher: SmartDataFetcher = request.app.state.fetcher
        data = await fetcher.fetch_north_bound_flow()
        if data:
            sh_buy = data.get("sh_buy", 0)
            sh_sell = data.get("sh_sell", 0)
            sz_buy = data.get("sz_buy", 0)
            sz_sell = data.get("sz_sell", 0)
            sh_inflow = sh_buy - sh_sell
            sz_inflow = sz_buy - sz_sell
            data["sh_inflow"] = sh_inflow
            data["sz_inflow"] = sz_inflow
            data["net_inflow"] = data.get("total_net", sh_inflow + sz_inflow)
        return _json_response(True, data=data)
    except Exception as e:
        return _json_response(False, error=str(e))


@router.get("/market/limit_up")
@cache_response(60)
async def get_limit_up_pool(request: Request):
    try:
        fetcher: SmartDataFetcher = request.app.state.fetcher
        return _json_response(True, data=await fetcher.fetch_limit_up_pool())
    except Exception as e:
        return _json_response(False, error=str(e))


@router.get("/market/dragon_tiger")
@cache_response(300)
async def get_dragon_tiger(request: Request, date: Optional[str] = None):
    try:
        fetcher: SmartDataFetcher = request.app.state.fetcher
        return _json_response(True, data=await fetcher.fetch_dragon_tiger_list(date))
    except Exception as e:
        return _json_response(False, error=str(e))


@router.get("/factor/analysis/{symbol}")
async def get_factor_analysis(request: Request, symbol: str, period: str = Query("1y")):
    try:
        from core.indicators import (
            calc_composite_score,
            calc_factor_efficiency_ratio,
            calc_factor_money_flow_index,
            calc_factor_momentum_quality,
            calc_factor_relative_volume,
            calc_factor_volume_price_trend,
        )
        fetcher: SmartDataFetcher = request.app.state.fetcher
        df = await fetcher.get_history(symbol, _period_to_history(period), "daily", "qfq")
        if df.empty or len(df) < 80:
            return _json_response(False, error="数据不足")
        h = df["high"].astype(float).values
        l = df["low"].astype(float).values
        c = df["close"].astype(float).values
        v = df["volume"].astype(float).values
        factors = {
            "momentum_quality": calc_factor_momentum_quality(c, v),
            "efficiency_ratio": calc_factor_efficiency_ratio(c),
            "relative_volume": calc_factor_relative_volume(v),
            "money_flow_index": calc_factor_money_flow_index(h, l, c, v),
            "volume_price_trend": calc_factor_volume_price_trend(c, v),
        }
        composite = calc_composite_score(factors)
        current = {}
        for name, arr in factors.items():
            valid = arr[np.isfinite(arr)]
            value = float(valid[-1]) if len(valid) else 0.0
            pct_rank = float((valid < value).mean()) if len(valid) else 0.5
            current[name] = {"value": round(value, 4), "percentile": round(pct_rank, 4), "direction": "bullish" if pct_rank >= 0.55 else "bearish" if pct_rank <= 0.45 else "neutral"}
        return _json_response(True, data={
            "factors": current,
            "composite_score": round(float(composite[-1]), 4) if len(composite) else 0,
        })
    except Exception as e:
        return _json_response(False, error=str(e))


@router.post("/backtest/advanced")
async def run_advanced_backtest(
    request: Request,
    symbol: str = Query(...),
    strategy_name: str = Query("adaptive"),
    start_date: str = Query("2022-01-01"),
    end_date: str = Query("2024-12-31"),
    initial_capital: float = Query(1000000),
    enable_short: bool = Query(False),
    leverage: float = Query(1.0),
    monte_carlo: bool = Query(False),
    n_simulations: int = Query(500),
    sensitivity: bool = Query(False),
    walk_forward: bool = Query(False),
):
    try:
        from core.backtest import BacktestEngine, BacktestResult, run_backtest as run_bt
        fetcher: SmartDataFetcher = request.app.state.fetcher
        df = await fetcher.get_history(symbol, period="all", kline_type="daily", adjust="qfq")
        result = await asyncio.to_thread(
            run_bt,
            symbol,
            strategy_name,
            start_date,
            end_date,
            initial_capital * max(leverage, 0.1),
            None,
            df,
        )
        if "error" in result:
            return _json_response(False, error=result["error"])
        result["enable_short"] = enable_short
        result["leverage"] = leverage
        if monte_carlo:
            engine = BacktestEngine(initial_capital=initial_capital)
            bt_result = BacktestResult(
                strategy_name=result.get("strategy_name", strategy_name),
                trades=result.get("trades", []),
                sharpe_ratio=result.get("sharpe_ratio", 0),
            )
            result["monte_carlo"] = engine.monte_carlo_analysis(bt_result, n_simulations=n_simulations)
        if sensitivity and strategy_name != "adaptive":
            from core.strategies import STRATEGY_REGISTRY
            strategy_cls = STRATEGY_REGISTRY.get(strategy_name)
            if strategy_cls:
                fetcher: SmartDataFetcher = request.app.state.fetcher
                df = await fetcher.get_history(symbol, "all", "daily", "qfq")
                if df is not None and not df.empty:
                    df["date"] = pd.to_datetime(df["date"], errors="coerce")
                    df = df.dropna(subset=["date"])
                    df = df[(df["date"] >= start_date) & (df["date"] <= end_date)].reset_index(drop=True)
                    result["sensitivity"] = engine.sensitivity_analysis(strategy_cls, df, {})
        if walk_forward:
            from core.backtest import run_walk_forward
            wf_result = await asyncio.to_thread(
                run_walk_forward, symbol, strategy_name, start_date, end_date,
                252, 63, initial_capital, None,
            )
            if "error" not in wf_result:
                result["walk_forward"] = wf_result
        db = getattr(request.app.state, "db", None)
        if db and hasattr(db, "save_backtest_result"):
            result["id"] = db.save_backtest_result(strategy_name, symbol, start_date, end_date, {}, result)
        return _json_response(True, data=result)
    except Exception as e:
        logger.error(f"Advanced backtest error: {e}", exc_info=True)
        return _json_response(False, error=str(e))


@router.post("/backtest/optimize")
async def optimize_strategy(
    request: Request,
    symbol: str = Query(...),
    strategy_name: str = Query("ma_cross"),
    start_date: str = Query("2023-01-01"),
    end_date: str = Query("2024-12-31"),
    metric: str = Query("sharpe_ratio"),
    max_combinations: int = Query(100),
):
    try:
        from core.backtest import grid_search_params
        from core.strategies import STRATEGY_REGISTRY
        if strategy_name not in STRATEGY_REGISTRY:
            return _json_response(False, error=f"未知策略: {strategy_name}")
        fetcher: SmartDataFetcher = request.app.state.fetcher
        df = await fetcher.get_history(symbol, "all", "daily", "qfq")
        if df.empty:
            return _json_response(False, error="无历史数据")
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df = df.dropna(subset=["date"])
        df = df[(df["date"] >= start_date) & (df["date"] <= end_date)].reset_index(drop=True)
        if len(df) < 60:
            return _json_response(False, error="优化数据不足")
        results = await asyncio.to_thread(grid_search_params, STRATEGY_REGISTRY[strategy_name], df, max_combinations)
        results.sort(key=lambda x: x.get(metric, 0), reverse=True)
        return _json_response(True, data={"metric": metric, "top": results[:10]})
    except Exception as e:
        return _json_response(False, error=str(e))


@router.get("/backtest/history")
async def get_backtest_history(request: Request, symbol: Optional[str] = None, limit: int = Query(20)):
    try:
        db = getattr(request.app.state, "db", None)
        if db and hasattr(db, "get_backtest_history"):
            return _json_response(True, data=db.get_backtest_history(symbol=symbol, limit=limit))
        return _json_response(True, data=[])
    except Exception as e:
        return _json_response(False, error=str(e))


@router.get("/portfolio/equity")
async def get_portfolio_equity(
    request: Request,
    symbols: str = Query(..., description="逗号分隔的股票代码"),
    period: str = Query("1y"),
):
    """组合权益曲线"""
    try:
        fetcher: SmartDataFetcher = request.app.state.fetcher
        symbol_list = [s.strip() for s in symbols.split(",") if s.strip()]
        if not symbol_list:
            return _json_response(False, error="请提供股票代码")

        all_close = {}
        for sym in symbol_list[:10]:
            try:
                df = await fetcher.get_history(sym, _period_to_history(period), "daily", "qfq")
                if df.empty or len(df) < 30:
                    continue
                all_close[sym] = df[["date", "close"]].copy()
            except Exception:
                continue

        if not all_close:
            return _json_response(False, error="有效数据不足")

        merged = None
        for sym, sdf in all_close.items():
            sdf = sdf.rename(columns={"close": sym})
            if merged is None:
                merged = sdf
            else:
                merged = merged.merge(sdf, on="date", how="inner")

        if merged is None or len(merged) < 10:
            return _json_response(False, error="重叠数据不足")

        merged = merged.tail(260).reset_index(drop=True)
        sym_cols = [c for c in merged.columns if c != "date"]
        weights = np.ones(len(sym_cols)) / len(sym_cols)
        prices = merged[sym_cols].astype(float)
        norm = prices / prices.iloc[0]
        port_equity = (norm * weights).sum(axis=1)
        port_returns = port_equity.pct_change().dropna()

        equity_curve = []
        for i, row in merged.iterrows():
            equity_curve.append({
                "date": str(row["date"])[:10],
                "equity": round(float(port_equity.iloc[i]), 4),
            })

        cumulative_return = float(port_equity.iloc[-1] / port_equity.iloc[0] - 1)
        max_drawdown = float((port_equity / port_equity.cummax() - 1).min())
        annual_return = float(port_returns.mean() * 252)
        annual_vol = float(port_returns.std() * np.sqrt(252))
        sharpe = annual_return / annual_vol if annual_vol > 0 else 0

        return _json_response(True, data={
            "symbols": sym_cols,
            "weights": {s: round(float(w), 4) for s, w in zip(sym_cols, weights)},
            "equity_curve": equity_curve,
            "cumulative_return": round(cumulative_return, 4),
            "max_drawdown": round(max_drawdown, 4),
            "annual_return": round(annual_return, 4),
            "annual_volatility": round(annual_vol, 4),
            "sharpe_ratio": round(sharpe, 2),
        })
    except Exception as e:
        logger.error(f"Portfolio equity error: {e}")
        return _json_response(False, error=str(e))


@router.get("/watchlist")
async def get_watchlist(request: Request):
    try:
        from core.database import get_db
        db = get_db()
        watchlist = db.get_config("watchlist", [])
        if not isinstance(watchlist, list):
            watchlist = []

        fetcher: SmartDataFetcher = request.app.state.fetcher

        a_symbols = []
        other_symbols = []
        for symbol in watchlist:
            market = MarketDetector.detect(symbol)
            if market == "A":
                a_symbols.append(symbol)
            else:
                other_symbols.append(symbol)

        results = {}
        if a_symbols:
            batch_results = await fetcher.get_realtime_batch(a_symbols)
            results.update(batch_results)

        if other_symbols:
            tasks = [fetcher.get_realtime(s) for s in other_symbols]
            other_results = await asyncio.gather(*tasks, return_exceptions=True)
            for symbol, result in zip(other_symbols, other_results):
                if isinstance(result, dict):
                    results[symbol] = result

        return _json_response(True, data={"symbols": watchlist, "quotes": results})
    except Exception as e:
        logger.error(f"Watchlist error: {e}")
        return _json_response(False, error=str(e))


@router.post("/watchlist/add")
async def add_to_watchlist(request: Request, symbol: str = Query(...)):
    try:
        from core.database import get_db
        db = get_db()
        watchlist = db.get_config("watchlist", [])
        if not isinstance(watchlist, list):
            watchlist = []
        if symbol not in watchlist:
            watchlist.append(symbol)
            db.set_config("watchlist", watchlist)
        return _json_response(True, data=watchlist)
    except Exception as e:
        return _json_response(False, error=str(e))


@router.post("/watchlist/remove")
async def remove_from_watchlist(request: Request, symbol: str = Query(...)):
    try:
        from core.database import get_db
        db = get_db()
        watchlist = db.get_config("watchlist", [])
        if not isinstance(watchlist, list):
            watchlist = []
        if symbol in watchlist:
            watchlist.remove(symbol)
            db.set_config("watchlist", watchlist)
        return _json_response(True, data=watchlist)
    except Exception as e:
        return _json_response(False, error=str(e))


@router.post("/watchlist/reorder")
async def reorder_watchlist(request: Request, symbols: str = Query(..., description="逗号分隔的新排序股票代码")):
    """重新排序自选股列表"""
    try:
        from core.database import get_db
        db = get_db()
        watchlist = db.get_config("watchlist", [])
        if not isinstance(watchlist, list):
            watchlist = []
        new_order = [s.strip() for s in symbols.split(",") if s.strip()]
        reordered = [s for s in new_order if s in watchlist]
        remaining = [s for s in watchlist if s not in set(new_order)]
        watchlist = reordered + remaining
        db.set_config("watchlist", watchlist)
        return _json_response(True, data=watchlist)
    except Exception as e:
        return _json_response(False, error=str(e))


@router.post("/watchlist/alert/add")
async def add_price_alert(
    request: Request,
    symbol: str = Query(...),
    alert_type: str = Query(..., description="price_above|price_below|pct_change_above"),
    value: float = Query(..., description="目标价格或涨跌幅百分比"),
):
    """添加价格预警"""
    try:
        from core.database import get_db
        db = get_db()
        alerts = db.get_config("price_alerts", [])
        if not isinstance(alerts, list):
            alerts = []

        alert = {
            "id": str(uuid.uuid4())[:8],
            "symbol": symbol,
            "alert_type": alert_type,
            "value": value,
            "triggered": False,
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        alerts.append(alert)
        db.set_config("price_alerts", alerts)
        return _json_response(True, data=alert)
    except Exception as e:
        return _json_response(False, error=str(e))


@router.get("/watchlist/alert/list")
async def get_price_alerts(request: Request, symbol: str = Query(None)):
    """获取价格预警列表"""
    try:
        from core.database import get_db
        db = get_db()
        alerts = db.get_config("price_alerts", [])
        if not isinstance(alerts, list):
            alerts = []
        if symbol:
            alerts = [a for a in alerts if a.get("symbol") == symbol]
        return _json_response(True, data=alerts)
    except Exception as e:
        return _json_response(False, error=str(e))


@router.post("/watchlist/alert/remove")
async def remove_price_alert(request: Request, alert_id: str = Query(...)):
    """删除价格预警"""
    try:
        from core.database import get_db
        db = get_db()
        alerts = db.get_config("price_alerts", [])
        if not isinstance(alerts, list):
            alerts = []
        alerts = [a for a in alerts if a.get("id") != alert_id]
        db.set_config("price_alerts", alerts)
        return _json_response(True, data={"removed": alert_id})
    except Exception as e:
        return _json_response(False, error=str(e))


@router.get("/search")
async def search_stocks(request: Request, q: str = Query(...), limit: int = Query(10)):
    try:
        from core.stock_search import search_stocks as do_search
        results = do_search(q, limit=limit)
        return _json_response(True, data=results)
    except Exception as e:
        return _json_response(False, error=str(e))


@router.get("/trading/account")
async def get_trading_account(request: Request):
    try:
        trading = request.app.state.trading
        return _json_response(True, data=trading.get_account_info())
    except Exception as e:
        return _json_response(False, error=str(e))


@router.post("/trading/buy")
async def trading_buy(
    request: Request,
    symbol: str = Query(...),
    name: str = Query(""),
    market: str = Query(""),
    price: float = Query(...),
    shares: int = Query(...),
    stop_loss: float = Query(0),
    take_profit: float = Query(0),
    strategy: str = Query("manual"),
):
    try:
        if not market:
            market = MarketDetector.detect(symbol)
        if not name:
            from core.stock_search import get_stock_name
            name = get_stock_name(symbol) or symbol
        trading = request.app.state.trading
        fetcher: SmartDataFetcher = request.app.state.fetcher
        rt = await fetcher.get_realtime(symbol, market)
        market_price = rt.get("price", 0) if rt else 0
        result = trading.execute_buy(
            symbol=symbol, name=name, market=market, price=price,
            shares=shares, stop_loss=stop_loss, take_profit=take_profit,
            strategy=strategy, market_price=market_price,
        )
        return _json_response(result.get("success", False), data=result)
    except Exception as e:
        return _json_response(False, error=str(e))


@router.post("/trading/sell")
async def trading_sell(
    request: Request,
    symbol: str = Query(...),
    price: float = Query(...),
    shares: Optional[int] = Query(None),
    reason: str = Query("manual"),
):
    try:
        trading = request.app.state.trading
        fetcher: SmartDataFetcher = request.app.state.fetcher
        market = MarketDetector.detect(symbol)
        rt = await fetcher.get_realtime(symbol, market)
        market_price = rt.get("price", 0) if rt else 0
        result = trading.execute_sell(
            symbol=symbol, price=price, reason=reason,
            shares=shares, market_price=market_price,
        )
        return _json_response(result.get("success", False), data=result)
    except Exception as e:
        return _json_response(False, error=str(e))


@router.get("/trading/history")
async def get_trading_history(request: Request, limit: int = Query(100)):
    try:
        trading = request.app.state.trading
        return _json_response(True, data=trading.get_trade_history(limit))
    except Exception as e:
        return _json_response(False, error=str(e))


@router.get("/system/metrics")
async def get_system_metrics(request: Request):
    try:
        import psutil
        import os
        process = psutil.Process(os.getpid())
        mem_info = process.memory_info()
        req_count = getattr(request.app.state, "_request_count", 0)
        total_rt = getattr(request.app.state, "_total_response_time", 0.0)
        avg_rt = total_rt / max(req_count, 1)
        metrics = {
            "uptime_seconds": time.time() - getattr(request.app.state, "_start_time", time.time()),
            "memory_mb": round(mem_info.rss / 1024 / 1024, 1),
            "cpu_percent": process.cpu_percent(interval=0.1),
            "threads": process.num_threads(),
            "api_requests_total": req_count,
            "avg_response_time": round(avg_rt, 1),
            "ws_connections": len(_manager.connections),
            "cache_size": len(getattr(request.app.state, "_cache", {})),
        }
        return _json_response(True, data=metrics)
    except ImportError:
        req_count = getattr(request.app.state, "_request_count", 0)
        total_rt = getattr(request.app.state, "_total_response_time", 0.0)
        avg_rt = total_rt / max(req_count, 1)
        metrics = {
            "uptime_seconds": time.time() - getattr(request.app.state, "_start_time", time.time()),
            "api_requests_total": req_count,
            "avg_response_time": round(avg_rt, 1),
            "ws_connections": len(_manager.connections),
        }
        return _json_response(True, data=metrics)
    except Exception as e:
        return _json_response(False, error=str(e))


@router.get("/config/{key}")
async def get_config(request: Request, key: str):
    try:
        from core.database import get_db
        db = get_db()
        value = db.get_config(key)
        return _json_response(True, data=value)
    except Exception as e:
        return _json_response(False, error=str(e))


@router.post("/config/{key}")
async def set_config(request: Request, key: str, value: str = Query(...)):
    try:
        from core.database import get_db
        db = get_db()
        db.set_config(key, value)
        return _json_response(True)
    except Exception as e:
        return _json_response(False, error=str(e))


@router.get("/stock/ai_summary/{symbol}")
@cache_response(300)
async def get_stock_ai_summary(request: Request, symbol: str, period: str = Query("1y")):
    """AI分析摘要 - 基于规则引擎生成综合分析"""
    try:
        fetcher: SmartDataFetcher = request.app.state.fetcher
        df = await fetcher.get_history(symbol, _period_to_history(period), "daily", "qfq")
        if df is None or df.empty:
            return _json_response(False, error="无数据")

        from core.indicators import TechnicalIndicators, IndicatorAnalysis
        from core.strategies import CompositeStrategy

        close = df["close"].values
        high = df["high"].values
        low = df["low"].values
        volume = df["volume"].values if "volume" in df.columns else None

        summary_points = []

        pct_5d = ((close[-1] / close[-6]) - 1) * 100 if len(close) > 5 else 0
        pct_20d = ((close[-1] / close[-21]) - 1) * 100 if len(close) > 20 else 0
        pct_60d = ((close[-1] / close[-61]) - 1) * 100 if len(close) > 60 else 0

        if pct_5d > 5:
            summary_points.append(f"近5日涨幅{pct_5d:.1f}%，短期强势")
        elif pct_5d < -5:
            summary_points.append(f"近5日跌幅{pct_5d:.1f}%，短期承压")
        else:
            summary_points.append(f"近5日变动{pct_5d:.1f}%，短期震荡")

        if pct_20d > 15:
            summary_points.append("月线级别强势上涨趋势")
        elif pct_20d < -15:
            summary_points.append("月线级别下跌趋势明显")

        close_series = pd.Series(close)
        ma5 = close_series.rolling(5).mean().values
        ma20 = close_series.rolling(20).mean().values
        ma60 = close_series.rolling(60).mean().values
        if not np.isnan(ma5[-1]) and not np.isnan(ma20[-1]):
            if ma5[-1] > ma20[-1] > (ma60[-1] if not np.isnan(ma60[-1]) else 0):
                summary_points.append("均线多头排列，趋势向好")
            elif ma5[-1] < ma20[-1]:
                summary_points.append("短期均线下穿中期均线，注意风险")

        if volume is not None and len(volume) > 10:
            avg_vol = np.mean(volume[-20:])
            recent_vol = np.mean(volume[-5:])
            if recent_vol > avg_vol * 1.5:
                summary_points.append("近期放量明显，关注资金动向")
            elif recent_vol < avg_vol * 0.5:
                summary_points.append("近期缩量，市场观望情绪浓厚")

        try:
            composite = CompositeStrategy()
            signal = composite.generate_signal(df)
            signal_map = {"buy": "买入", "sell": "卖出", "hold": "中性"}
            summary_points.append(f"综合策略信号：{signal_map.get(signal.signal_type.value, '中性')}（强度{signal.strength:.2f}）")
        except Exception:
            pass

        try:
            analysis = IndicatorAnalysis.comprehensive_analysis(df)
            if analysis.get("volatility", {}).get("current") == "high":
                summary_points.append("当前波动率较高，注意风险控制")
            if analysis.get("volume_price", {}).get("divergence"):
                summary_points.append("量价出现背离信号")
        except Exception:
            pass

        overall = "中性"
        bullish_count = sum(1 for p in summary_points if any(k in p for k in ["强势", "上涨", "向好", "买入"]))
        bearish_count = sum(1 for p in summary_points if any(k in p for k in ["承压", "下跌", "风险", "卖出"]))
        if bullish_count >= 3:
            overall = "偏多"
        elif bearish_count >= 3:
            overall = "偏空"

        return _json_response(True, data={
            "symbol": symbol,
            "overall": overall,
            "points": summary_points,
            "price_change": {"5d": round(pct_5d, 2), "20d": round(pct_20d, 2), "60d": round(pct_60d, 2)},
            "generated_at": time.time(),
        })
    except Exception as e:
        logger.error(f"AI summary error: {e}")
        return _json_response(False, error=str(e))


@router.websocket("/ws/realtime")
async def websocket_realtime(ws: WebSocket):
    await _manager.connect(ws)
    try:
        while True:
            data = await ws.receive_text()
            try:
                msg = json.loads(data)
                msg_type = msg.get("type", msg.get("action", ""))
                symbols = msg.get("symbols", [])
                if msg_type == "subscribe" and symbols:
                    _manager.subscribe(ws, symbols)
                elif msg_type == "unsubscribe" and symbols:
                    _manager.unsubscribe(ws, symbols)
                elif msg_type == "ping":
                    await ws.send_json({"type": "pong", "ts": time.time()})
            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        _manager.disconnect(ws)
    except Exception:
        _manager.disconnect(ws)


_last_indices_hash = ""
_last_quote_hash: dict[str, str] = {}
_last_push_state: dict[str, dict] = {}
_push_seq = 0


def _diff_push(old: dict, new: dict) -> dict:
    if not old:
        return dict(new)
    diff = {}
    for k, v in new.items():
        if k not in old or old[k] != v:
            diff[k] = v
    return diff


def _build_message(msg_type: str, data: dict) -> str:
    global _push_seq
    _push_seq += 1
    return json.dumps({
        "type": msg_type,
        "ts": time.time(),
        "data": data,
        "seq": _push_seq,
    }, ensure_ascii=False)


async def push_realtime_data(fetcher: SmartDataFetcher):
    global _last_indices_hash, _last_quote_hash, _last_push_state

    while True:
        try:
            if not _manager.connections:
                await asyncio.sleep(5)
                continue

            if not _is_trading_hours():
                await asyncio.sleep(30)
                continue

            indices_data = {}
            try:
                overview = await fetcher.get_market_overview()
                cn = overview.get("cn_indices", {})
                hk = overview.get("hk_indices", {})
                us = overview.get("us_indices", {})
                indices_data = {**cn, **hk, **us}
            except Exception:
                pass

            indices_hash = json.dumps(indices_data, sort_keys=True)[:64]
            should_push_indices = indices_hash != _last_indices_hash
            if should_push_indices:
                _last_indices_hash = indices_hash

            subscribed = _manager.get_all_subscribed_symbols()
            quotes_data = {}
            for symbol in list(subscribed)[:30]:
                try:
                    rt = await fetcher.get_realtime(symbol)
                    if rt:
                        price_str = f"{rt.get('price', 0)}_{rt.get('change_pct', 0)}"
                        last_hash = _last_quote_hash.get(symbol, "")
                        if price_str != last_hash:
                            quotes_data[symbol] = rt
                            _last_quote_hash[symbol] = price_str
                except Exception:
                    pass

            if should_push_indices or quotes_data:
                msg_data: dict = {}
                if should_push_indices:
                    old_indices = _last_push_state.get("indices", {})
                    diff = _diff_push(old_indices, indices_data)
                    if diff:
                        msg_data["indices"] = diff
                        _last_push_state["indices"] = dict(indices_data)
                if quotes_data:
                    old_quotes = _last_push_state.get("quotes", {})
                    diff = _diff_push(old_quotes, quotes_data)
                    if diff:
                        msg_data["quotes"] = diff
                        _last_push_state["quotes"] = dict(quotes_data)

                if msg_data:
                    msg_str = _build_message("quote_update", msg_data)
                    disconnected = []
                    for ws in _manager.connections:
                        try:
                            await ws.send_text(msg_str)
                        except Exception:
                            disconnected.append(ws)
                    for ws in disconnected:
                        _manager.disconnect(ws)

            await asyncio.sleep(5)
        except Exception as e:
            logger.debug(f"Push realtime error: {e}")
            await asyncio.sleep(10)


async def push_signal_event(symbol: str, strategy: str, signal_type: str, score: float, price: float):
    if not _manager.connections:
        return
    msg_str = _build_message("signal", {
        "symbol": symbol, "strategy": strategy,
        "signal_type": signal_type, "score": score, "price": price,
    })
    disconnected = []
    for ws in _manager.connections:
        subs = _manager._subscriptions.get(ws, set())
        if not subs or symbol in subs:
            try:
                await ws.send_text(msg_str)
            except Exception:
                disconnected.append(ws)
    for ws in disconnected:
        _manager.disconnect(ws)


async def push_alert_event(symbol: str, alert_type: str, value: float, current_price: float):
    if not _manager.connections:
        return
    msg_str = _build_message("alert", {
        "symbol": symbol, "alert_type": alert_type,
        "value": value, "current_price": current_price,
    })
    disconnected = []
    for ws in _manager.connections:
        subs = _manager._subscriptions.get(ws, set())
        if not subs or symbol in subs:
            try:
                await ws.send_text(msg_str)
            except Exception:
                disconnected.append(ws)
    for ws in disconnected:
        _manager.disconnect(ws)


async def push_market_event(event_type: str, data: dict):
    if not _manager.connections:
        return
    msg_str = _build_message("market_event", data)
    disconnected = []
    for ws in _manager.connections:
        try:
            await ws.send_text(msg_str)
        except Exception:
            disconnected.append(ws)
    for ws in disconnected:
        _manager.disconnect(ws)
