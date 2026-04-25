import logging

from fastapi import APIRouter, Query, Request


logger = logging.getLogger(__name__)
analysis_router = APIRouter(prefix="/analysis", tags=["技术分析与研究增强"])


def _resp(success: bool, data=None, msg: str = ""):
    return {"code": 0 if success else 1, "data": data, "msg": msg}


@analysis_router.get("/ma-alignment")
async def ma_alignment(request: Request, symbol: str = Query(...), period: str = Query("1y")):
    df = await request.app.state.fetcher.get_history(symbol, period=period, adjust="qfq")
    return _resp(True, data=request.app.state.analysis_service.ma_alignment(df))


@analysis_router.get("/relative-strength")
async def relative_strength(
    request: Request,
    symbol: str = Query(...),
    benchmark_symbol: str = Query("000300"),
    period: str = Query("1y"),
):
    df = await request.app.state.fetcher.get_history(symbol, period=period, adjust="qfq")
    benchmark_df = await request.app.state.fetcher.get_history(benchmark_symbol, period=period, instrument_type="index", adjust="qfq")
    return _resp(True, data=request.app.state.analysis_service.relative_strength(df, benchmark_df))


@analysis_router.post("/signal-verify")
async def signal_verify(
    request: Request,
    symbol: str = Query(...),
    signal_type: str = Query("macd_golden_cross"),
    period: str = Query("all"),
):
    df = await request.app.state.fetcher.get_history(symbol, period=period, adjust="qfq")
    result = request.app.state.analysis_service.signal_verify(df, signal_type)
    return _resp(True, data=result.to_dict())


@analysis_router.get("/calendar-effect")
async def calendar_effect(request: Request, symbol: str = Query(...), period: str = Query("all")):
    df = await request.app.state.fetcher.get_history(symbol, period=period, adjust="qfq")
    return _resp(True, data=request.app.state.analysis_service.calendar_effect(df))


@analysis_router.get("/holding-period")
async def holding_period(
    request: Request,
    symbol: str = Query(...),
    entry_condition: str = Query("macd_golden_cross"),
    period: str = Query("all"),
):
    df = await request.app.state.fetcher.get_history(symbol, period=period, adjust="qfq")
    return _resp(True, data=request.app.state.analysis_service.holding_period_analysis(df, entry_condition))


@analysis_router.post("/correlation")
async def correlation(request: Request, symbols: str = Query(...), period: str = Query("1y")):
    datasets = {}
    for symbol in [item.strip() for item in symbols.split(",") if item.strip()]:
        datasets[symbol] = await request.app.state.fetcher.get_history(symbol, period=period, adjust="qfq")
    return _resp(True, data=request.app.state.analysis_service.correlation_matrix(datasets))


@analysis_router.get("/support-resistance")
async def support_resistance(request: Request, symbol: str = Query(...), period: str = Query("1y")):
    df = await request.app.state.fetcher.get_history(symbol, period=period, adjust="qfq")
    return _resp(True, data=request.app.state.analysis_service.support_resistance(df))


@analysis_router.get("/patterns")
async def patterns(request: Request, symbol: str = Query(...), period: str = Query("1y")):
    df = await request.app.state.fetcher.get_history(symbol, period=period, adjust="qfq")
    return _resp(True, data=request.app.state.analysis_service.kline_patterns(df))


@analysis_router.get("/vpvr")
async def vpvr(request: Request, symbol: str = Query(...), period: str = Query("1y"), bins: int = Query(24)):
    df = await request.app.state.fetcher.get_history(symbol, period=period, adjust="qfq")
    return _resp(True, data=request.app.state.analysis_service.vpvr(df, bins=bins))


@analysis_router.get("/trend-lines")
async def trend_lines(request: Request, symbol: str = Query(...), period: str = Query("1y")):
    df = await request.app.state.fetcher.get_history(symbol, period=period, adjust="qfq")
    return _resp(True, data=request.app.state.analysis_service.trend_lines(df))


@analysis_router.get("/volatility-range")
async def volatility_range(request: Request, symbol: str = Query(...), period: str = Query("1y")):
    df = await request.app.state.fetcher.get_history(symbol, period=period, adjust="qfq")
    return _resp(True, data=request.app.state.analysis_service.volatility_range(df))


@analysis_router.get("/rsi-divergence")
async def rsi_divergence(request: Request, symbol: str = Query(...), period: str = Query("1y")):
    df = await request.app.state.fetcher.get_history(symbol, period=period, adjust="qfq")
    return _resp(True, data=request.app.state.analysis_service.rsi_divergence(df))


@analysis_router.get("/volume-price")
async def volume_price(request: Request, symbol: str = Query(...), period: str = Query("1y")):
    df = await request.app.state.fetcher.get_history(symbol, period=period, adjust="qfq")
    return _resp(True, data=request.app.state.analysis_service.volume_price_analysis(df))


@analysis_router.get("/industry-compare")
async def industry_compare(request: Request, symbol: str = Query(...), period: str = Query("1y"), limit: int = Query(10)):
    base_info = request.app.state.db.get_stock_info(symbol)
    if not base_info:
        return _resp(False, msg="未找到股票基本信息")
    sector = base_info.get("sector", "")
    peers = request.app.state.db.fetchall(
        """
        SELECT symbol AS code, market, name, industry AS sector, pe_ttm, pb
        FROM stock_info
        WHERE industry = ? AND symbol <> ? AND market = ?
        ORDER BY market_value DESC
        LIMIT ?
        """,
        (sector, symbol, base_info.get("market", "A"), limit),
    )
    for peer in peers:
        if not peer.get("code"):
            peer["code"] = peer.pop("symbol", "")
    base_df = await request.app.state.fetcher.get_history(symbol, period=period, adjust="qfq")
    return _resp(True, data=request.app.state.analysis_service.industry_comparison(symbol, base_df, peers))
