import asyncio
import logging
import time
from collections import OrderedDict
from typing import Optional

import numpy as np
import pandas as pd
from fastapi import APIRouter, Query, Request

from core.backtest import BacktestEngine
from core.data_fetcher import SmartDataFetcher
from core.indicators import TechnicalIndicators
from core.market_detector import MarketDetector
from core.market_hours import MarketHours
from core.prediction import PricePredictor
from core.stock_search import search_stocks, get_stock_info
from core.strategies import CompositeStrategy
from core.simulated_trading import SimulatedTrading

logger = logging.getLogger(__name__)
router = APIRouter()

_MAX_ROUTE_CACHE = 100
_cache: OrderedDict = OrderedDict()
_CACHE_TTL = 60


def _cache_get(key: str):
    entry = _cache.get(key)
    if entry and (time.time() - entry["ts"]) < entry.get("ttl", _CACHE_TTL):
        _cache.move_to_end(key)
        return entry["data"]
    if key in _cache:
        del _cache[key]
    return None


def _cache_set(key: str, data, ttl: Optional[int] = None):
    if key in _cache:
        _cache.move_to_end(key)
    _cache[key] = {"data": data, "ts": time.time(), "ttl": ttl or _CACHE_TTL}
    while len(_cache) > _MAX_ROUTE_CACHE:
        _cache.popitem(last=False)


def _json_response(success: bool, data=None, error: str = ""):
    return {"success": success, "data": data, "error": error}


@router.get("/search")
async def search_stock(request: Request, q: str = Query(..., min_length=1, max_length=20)):
    try:
        results = search_stocks(q, limit=10)
        return _json_response(True, data=results)
    except Exception as e:
        logger.error(f"search error: {e}", exc_info=True)
        return _json_response(False, error=str(e))


@router.get("/stock/{symbol}")
async def get_stock_full(request: Request, symbol: str, period: str = Query("1y")):
    try:
        cache_key = f"full:{symbol}:{period}"
        cached = _cache_get(cache_key)
        if cached:
            return _json_response(True, data=cached)

        market_info = MarketDetector.get_config(symbol)
        stock_info = get_stock_info(symbol)

        df, realtime, fundamentals = await asyncio.gather(
            request.app.state.fetcher.get_history(symbol, period),
            request.app.state.fetcher.get_realtime(symbol),
            request.app.state.fetcher.get_fundamentals(symbol, market_info["market"]),
        )

        stock_name = realtime.get("name", "") if realtime else ""
        if not stock_name and stock_info:
            stock_name = stock_info.get("name", "")

        if df.empty:
            if realtime and realtime.get("price"):
                return _json_response(True, data={
                    "symbol": symbol,
                    "name": stock_name,
                    "market": market_info,
                    "history": [],
                    "indicators": {},
                    "prediction": {},
                    "realtime": realtime,
                    "fundamentals": fundamentals,
                    "sector": stock_info.get("sector", "") if stock_info else "",
                    "no_history": True,
                })
            return _json_response(False, error=f"No data for {symbol}")

        indicators = TechnicalIndicators.compute_all(df)
        prediction = PricePredictor.predict(df, symbol)
        history_data = _df_to_chart(df)

        result = {
            "symbol": symbol,
            "name": stock_name,
            "market": market_info,
            "history": history_data,
            "indicators": indicators,
            "prediction": prediction,
            "realtime": realtime,
            "fundamentals": fundamentals,
        }

        if stock_info:
            result["sector"] = stock_info.get("sector", "")

        _cache_set(cache_key, result, ttl=30)
        return _json_response(True, data=result)
    except Exception as e:
        logger.error(f"get_stock_full error: {e}", exc_info=True)
        return _json_response(False, error=str(e))


@router.get("/history")
async def get_history(request: Request, symbol: str = Query(...), period: str = Query("1y")):
    try:
        cache_key = f"hist:{symbol}:{period}"
        cached = _cache_get(cache_key)
        if cached:
            return _json_response(True, data=cached)

        df = await request.app.state.fetcher.get_history(symbol, period)
        if df.empty:
            return _json_response(False, error="No history data")
        data = _df_to_chart(df)
        _cache_set(cache_key, data, ttl=60)
        return _json_response(True, data=data)
    except Exception as e:
        logger.error(f"get_history error: {e}", exc_info=True)
        return _json_response(False, error=str(e))


@router.get("/realtime")
async def get_realtime(request: Request, symbol: str = Query(...)):
    try:
        cache_key = f"rt:{symbol}"
        cached = _cache_get(cache_key)
        if cached:
            return _json_response(True, data=cached)

        data = await request.app.state.fetcher.get_realtime(symbol)
        if not data:
            return _json_response(False, error="No realtime data")
        _cache_set(cache_key, data, ttl=10)
        return _json_response(True, data=data)
    except Exception as e:
        logger.error(f"get_realtime error: {e}", exc_info=True)
        return _json_response(False, error=str(e))


@router.get("/indicators")
async def get_indicators(request: Request, symbol: str = Query(...), period: str = Query("1y")):
    try:
        cache_key = f"ind:{symbol}:{period}"
        cached = _cache_get(cache_key)
        if cached:
            return _json_response(True, data=cached)

        df = await request.app.state.fetcher.get_history(symbol, period)
        if df.empty:
            return _json_response(False, error="No data for indicators")
        indicators = TechnicalIndicators.compute_all(df)
        _cache_set(cache_key, indicators, ttl=30)
        return _json_response(True, data=indicators)
    except Exception as e:
        logger.error(f"get_indicators error: {e}", exc_info=True)
        return _json_response(False, error=str(e))


@router.get("/prediction")
async def get_prediction(request: Request, symbol: str = Query(...), period: str = Query("1y")):
    try:
        cache_key = f"pred:{symbol}:{period}"
        cached = _cache_get(cache_key)
        if cached:
            return _json_response(True, data=cached)

        df = await request.app.state.fetcher.get_history(symbol, period)
        if df.empty:
            return _json_response(False, error="No data for prediction")
        prediction = PricePredictor.predict(df, symbol)
        _cache_set(cache_key, prediction, ttl=30)
        return _json_response(True, data=prediction)
    except Exception as e:
        logger.error(f"get_prediction error: {e}", exc_info=True)
        return _json_response(False, error=str(e))


@router.get("/market/{symbol}")
async def get_market_info(request: Request, symbol: str):
    try:
        info = MarketDetector.get_config(symbol)
        stock_info = get_stock_info(symbol)
        result = {"market_info": info}
        if stock_info:
            result["stock_info"] = stock_info
        return _json_response(True, data=result)
    except Exception as e:
        return _json_response(False, error=str(e))


@router.get("/hot")
async def get_hot_stocks(request: Request):
    try:
        cache_key = "hot:stocks"
        cached = _cache_get(cache_key)
        if cached:
            return _json_response(True, data=cached)

        data = await request.app.state.fetcher.get_hot_stocks()
        _cache_set(cache_key, data, ttl=120)
        return _json_response(True, data=data)
    except Exception as e:
        logger.error(f"get_hot_stocks error: {e}", exc_info=True)
        return _json_response(False, error=str(e))


@router.get("/market-status/{market}")
async def get_market_status(request: Request, market: str):
    try:
        if market not in ("A", "HK", "US"):
            return _json_response(False, error="Invalid market")
        status = MarketHours.get_market_status(market)
        refresh_interval = MarketHours.get_refresh_interval(market)
        status["refresh_interval"] = refresh_interval
        return _json_response(True, data=status)
    except Exception as e:
        return _json_response(False, error=str(e))


@router.get("/strategies")
async def get_strategies(request: Request):
    try:
        info = request.app.state.composite_strategy.get_strategy_info()
        return _json_response(True, data=info)
    except Exception as e:
        return _json_response(False, error=str(e))


@router.get("/strategies/{symbol}")
async def run_strategies(request: Request, symbol: str, period: str = Query("1y")):
    try:
        cache_key = f"strat:{symbol}:{period}"
        cached = _cache_get(cache_key)
        if cached:
            return _json_response(True, data=cached)

        df = await request.app.state.fetcher.get_history(symbol, period)
        if df.empty:
            return _json_response(False, error="No data for strategy analysis")

        results = request.app.state.composite_strategy.run_all(df)
        composite = request.app.state.composite_strategy.composite_score(results)

        output = {
            "composite": composite,
            "strategies": {},
        }
        for name, result in results.items():
            output["strategies"][name] = {
                "name": result.name,
                "description": result.description,
                "score": result.score,
                "params": result.params,
                "current_signal": {
                    "type": result.current_signal.signal_type.value if result.current_signal else "hold",
                    "strength": result.current_signal.strength if result.current_signal else 0,
                    "reason": result.current_signal.reason if result.current_signal else "",
                    "price": result.current_signal.price if result.current_signal else 0,
                    "stop_loss": result.current_signal.stop_loss if result.current_signal else 0,
                    "take_profit": result.current_signal.take_profit if result.current_signal else 0,
                    "position_pct": result.current_signal.position_pct if result.current_signal else 0,
                } if result.current_signal else None,
                "signal_count": len(result.signals),
            }

        _cache_set(cache_key, output, ttl=30)
        return _json_response(True, data=output)
    except Exception as e:
        logger.error(f"run_strategies error: {e}", exc_info=True)
        return _json_response(False, error=str(e))


@router.get("/backtest/{symbol}")
async def run_backtest(request: Request, symbol: str, period: str = Query("1y")):
    try:
        cache_key = f"bt:{symbol}:{period}"
        cached = _cache_get(cache_key)
        if cached:
            return _json_response(True, data=cached)

        df = await request.app.state.fetcher.get_history(symbol, period)
        if df.empty or len(df) < 60:
            return _json_response(False, error="数据不足，至少需要60个交易日")

        results = request.app.state.backtest_engine.run_multi(request.app.state.composite_strategy.strategies, df)

        output = {}
        for name, result in results.items():
            output[name] = {
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
                "avg_hold_days": result.avg_hold_days,
                "benchmark_return": result.benchmark_return,
                "alpha": result.alpha,
                "beta": result.beta,
                "equity_curve": result.equity_curve[-200:] if result.equity_curve else [],
                "drawdown_curve": result.drawdown_curve[-200:] if result.drawdown_curve else [],
                "dates": result.dates[-200:] if result.dates else [],
            }

        _cache_set(cache_key, output, ttl=120)
        return _json_response(True, data=output)
    except Exception as e:
        logger.error(f"backtest error: {e}", exc_info=True)
        return _json_response(False, error=str(e))


@router.get("/sim/account")
async def sim_get_account(request: Request):
    try:
        data = request.app.state.sim_trading.get_account_info()
        return _json_response(True, data=data)
    except Exception as e:
        return _json_response(False, error=str(e))


@router.get("/sim/performance")
async def sim_get_performance(request: Request):
    try:
        data = request.app.state.sim_trading.get_performance()
        return _json_response(True, data=data)
    except Exception as e:
        return _json_response(False, error=str(e))


@router.get("/sim/trades")
async def sim_get_trades(request: Request, limit: int = Query(50)):
    try:
        data = request.app.state.sim_trading.get_trade_history(limit)
        return _json_response(True, data=data)
    except Exception as e:
        return _json_response(False, error=str(e))


@router.post("/sim/buy")
async def sim_buy(request: Request, 
    symbol: str = Query(...),
    name: str = Query(""),
    market: str = Query("A"),
    price: float = Query(...),
    strategy: str = Query("manual"),
    stop_loss: float = Query(0),
    take_profit: float = Query(0),
    order_type: str = Query("market"),
    shares: int = Query(0),
):
    try:
        if not name:
            from core.stock_search import get_stock_name
            name = get_stock_name(symbol) or symbol
        result = request.app.state.sim_trading.execute_buy(
            symbol, name, market, price, strategy, stop_loss, take_profit,
            order_type=order_type, shares=shares,
        )
        if result["success"]:
            return _json_response(True, data=result)
        return _json_response(False, error=result.get("error", "买入失败"))
    except Exception as e:
        return _json_response(False, error=str(e))


@router.post("/sim/sell")
async def sim_sell(request: Request, symbol: str = Query(...), price: float = Query(...), reason: str = Query("manual")):
    try:
        result = request.app.state.sim_trading.execute_sell(symbol, price, reason)
        if result["success"]:
            return _json_response(True, data=result)
        return _json_response(False, error=result.get("error", "卖出失败"))
    except Exception as e:
        return _json_response(False, error=str(e))


@router.post("/sim/reset")
async def sim_reset(request: Request):
    try:
        result = request.app.state.sim_trading.reset_account()
        return _json_response(True, data=result)
    except Exception as e:
        return _json_response(False, error=str(e))


@router.get("/indicator-explain/{indicator}")
async def get_indicator_explanation(request: Request, indicator: str):
    explanations = {
        "macd": {
            "name": "MACD",
            "full_name": "移动平均收敛/发散指标",
            "category": "趋势指标",
            "definition": "MACD是通过计算两条不同周期的指数移动平均线(EMA)之间的差值来判断趋势方向和强度的技术指标。",
            "calculation": "DIF = EMA(12) - EMA(26)\nDEA = EMA(DIF, 9)\nMACD柱 = (DIF - DEA) × 2",
            "interpretation": {
                "golden_cross": "DIF上穿DEA，称为金叉，通常为买入信号",
                "death_cross": "DIF下穿DEA，称为死叉，通常为卖出信号",
                "above_zero": "DIF和DEA在零轴上方，表示多头趋势",
                "below_zero": "DIF和DEA在零轴下方，表示空头趋势",
                "divergence": "价格创新高但MACD未创新高，为顶背离；价格创新低但MACD未创新低，为底背离",
            },
            "tips": "零轴上方的金叉比零轴下方的金叉更可靠；MACD柱状图由绿转红表示动能转多。",
        },
        "rsi": {
            "name": "RSI",
            "full_name": "相对强弱指标",
            "category": "动量指标",
            "definition": "RSI衡量一段时间内价格上涨幅度与下跌幅度的比值，反映市场买卖力量的对比。",
            "calculation": "RSI = 100 - 100/(1+RS)\nRS = N日内平均上涨幅度 / N日内平均下跌幅度\n常用周期: 6、12、24",
            "interpretation": {
                "overbought": "RSI > 70，市场超买，可能面临回调",
                "oversold": "RSI < 30，市场超卖，可能出现反弹",
                "midline": "RSI > 50为多头区域，RSI < 50为空头区域",
                "divergence": "价格与RSI走势相反时，预示趋势可能反转",
            },
            "tips": "在强趋势中RSI可能长期处于超买/超卖区域，需结合其他指标确认。",
        },
        "kdj": {
            "name": "KDJ",
            "full_name": "随机指标",
            "category": "动量指标",
            "definition": "KDJ通过计算一定周期内收盘价在最高价和最低价之间的位置来判断超买超卖状态。",
            "calculation": "RSV = (收盘价-N日最低价)/(N日最高价-N日最低价)×100\nK = 2/3×前日K + 1/3×RSV\nD = 2/3×前日D + 1/3×K\nJ = 3K - 2D",
            "interpretation": {
                "overbought": "K>80, D>80, J>100为超买区域",
                "oversold": "K<20, D<20, J<0为超卖区域",
                "golden_cross": "K线上穿D线为金叉，买入信号",
                "death_cross": "K线下穿D线为死叉，卖出信号",
                "j_extreme": "J值>100或<0时，表示短期过度偏离，反转概率增大",
            },
            "tips": "J值对价格变化最敏感，适合短线操作参考；KDJ在震荡市中效果较好，趋势市中容易钝化。",
        },
        "boll": {
            "name": "BOLL",
            "full_name": "布林带",
            "category": "波动率指标",
            "definition": "布林带由中轨(移动平均线)和上下两条标准差通道组成，反映价格波动的区间和趋势。",
            "calculation": "中轨 = MA(N)\n上轨 = 中轨 + K×标准差\n下轨 = 中轨 - K×标准差\n常用参数: N=20, K=2",
            "interpretation": {
                "squeeze": "布林带收窄，表示波动率降低，可能即将出现大幅突破",
                "breakout": "价格突破上轨为强势，跌破下轨为弱势",
                "walk_band": "价格沿上轨运行为强势上涨，沿下轨运行为强势下跌",
                "mean_reversion": "价格从上下轨回归中轨的概率较大",
            },
            "tips": "布林带收窄后的突破方向通常代表后续趋势方向；带宽指标可用于量化收窄程度。",
        },
        "ma": {
            "name": "MA",
            "full_name": "移动平均线",
            "category": "趋势指标",
            "definition": "移动平均线是将一定周期内的收盘价取平均值连成的线，用于判断趋势方向和支撑压力位。",
            "calculation": "MA(N) = (C1+C2+...+CN)/N\n常用周期: 5、10、20、60、120",
            "interpretation": {
                "golden_cross": "短期均线上穿长期均线，为金叉买入信号",
                "death_cross": "短期均线下穿长期均线，为死叉卖出信号",
                "support": "均线向上时对价格有支撑作用",
                "resistance": "均线向下时对价格有压力作用",
                "alignment": "均线多头排列(5>10>20>60)为强势，空头排列为弱势",
            },
            "tips": "均线周期越长越稳定但越滞后；多条均线配合使用效果更好。",
        },
        "supertrend": {
            "name": "SuperTrend",
            "full_name": "超级趋势指标",
            "category": "趋势指标",
            "definition": "SuperTrend基于ATR计算的趋势跟踪指标，通过价格与趋势线的关系判断多空方向。",
            "calculation": "上轨 = (最高价+最低价)/2 + 乘数×ATR\n下轨 = (最高价+最低价)/2 - 乘数×ATR\n常用参数: 周期=10, 乘数=3",
            "interpretation": {
                "bullish": "价格在SuperTrend上方，趋势线为绿色，为多头",
                "bearish": "价格在SuperTrend下方，趋势线为红色，为空头",
                "flip": "趋势线由红转绿为买入信号，由绿转红为卖出信号",
            },
            "tips": "SuperTrend在趋势市中表现优秀，震荡市中可能频繁发出假信号。",
        },
        "cci": {
            "name": "CCI",
            "full_name": "商品通道指标",
            "category": "动量指标",
            "definition": "CCI衡量价格偏离其统计平均值的程度，用于判断超买超卖和趋势强度。",
            "calculation": "TP = (最高价+最低价+收盘价)/3\nCCI = (TP-MA)/(0.015×MD)\nMA=TP的N日简单平均，MD=平均偏差",
            "interpretation": {
                "above_100": "CCI>100，价格异常偏高，处于强势上涨",
                "below_minus100": "CCI<-100，价格异常偏低，处于强势下跌",
                "normal": "CCI在-100到100之间，价格处于正常波动范围",
            },
            "tips": "CCI没有上限和下限，极端值可能持续较长时间。",
        },
        "atr": {
            "name": "ATR",
            "full_name": "平均真实波幅",
            "category": "波动率指标",
            "definition": "ATR衡量一定周期内价格波动的平均幅度，反映市场的波动性。",
            "calculation": "TR = max(最高价-最低价, |最高价-前收|, |最低价-前收|)\nATR = TR的N日移动平均\n常用周期: 14",
            "interpretation": {
                "high_atr": "ATR较高，市场波动剧烈，风险和机会并存",
                "low_atr": "ATR较低，市场波动平缓，可能酝酿突破",
                "use": "常用于设置止损位(ATR的1.5-3倍)和仓位管理",
            },
            "tips": "ATR不判断方向，只衡量波动幅度；可用于动态调整止损止盈距离。",
        },
        "volume_ratio": {
            "name": "量比",
            "full_name": "成交量比率",
            "category": "成交量指标",
            "definition": "量比是当日即时成交量与过去5日平均成交量的比值，反映当前成交活跃程度。",
            "calculation": "量比 = 当前累计成交量 / (过去5日平均同时段成交量)",
            "interpretation": {
                "high": "量比>1.5，成交活跃，关注度高",
                "low": "量比<0.7，成交清淡，市场关注度低",
                "normal": "量比在0.7-1.5之间，成交正常",
            },
            "tips": "量价配合分析更有效：放量上涨为健康上涨，放量下跌需警惕。",
        },
    }
    data = explanations.get(indicator.lower())
    if data:
        return _json_response(True, data=data)
    return _json_response(False, error=f"未找到指标 {indicator} 的说明")


def _df_to_chart(df) -> list:
    dates = df["date"].values
    times = []
    for d in dates:
        ts = str(pd.Timestamp(d).date())
        times.append(ts)

    opens = df["open"].values.astype(float)
    highs = df["high"].values.astype(float)
    lows = df["low"].values.astype(float)
    closes = df["close"].values.astype(float)

    has_volume = "volume" in df.columns
    volumes = df["volume"].values.astype(float) if has_volume else None

    result = []
    for i in range(len(df)):
        item = {
            "time": times[i],
            "open": round(opens[i], 2),
            "high": round(highs[i], 2),
            "low": round(lows[i], 2),
            "close": round(closes[i], 2),
        }
        if has_volume and volumes is not None:
            vol = volumes[i]
            if not np.isnan(vol):
                item["volume"] = int(vol)
        result.append(item)
    return result
