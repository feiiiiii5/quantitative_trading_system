import logging
from typing import Optional

from fastapi import APIRouter, Query, Request

from core.monitor.heartbeat import StrategyHeartbeatMonitor
from core.monitor.alert_system import SmartAlertSystem, AlertLevel, AlertChannel
from core.monitor.anomaly_detect import AnomalyDetector
from core.monitor.perf_dashboard import PerformanceDashboard

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/monitor", tags=["监控与告警"])


def _resp(success: bool, data=None, msg: str = ""):
    return {"code": 0 if success else 1, "data": data, "msg": msg}


@router.post("/heartbeat/register")
async def register_strategy(
    request: Request,
    strategy_name: str = Query(...),
    timeout_seconds: float = Query(30),
):
    async with request.app.state.write_lock:
        request.app.state.heartbeat.register(strategy_name, timeout_seconds)
    return _resp(True, msg=f"策略{strategy_name}已注册")


@router.post("/heartbeat/report")
async def report_heartbeat(request: Request, strategy_name: str = Query(...)):
    result = request.app.state.heartbeat.report(strategy_name)
    return _resp(result.get("success", False), data=result)


@router.get("/heartbeat/status")
async def get_all_status(request: Request):
    status = request.app.state.heartbeat.get_all_status()
    return _resp(True, data=status)


@router.get("/heartbeat/status/{strategy_name}")
async def get_strategy_status(request: Request, strategy_name: str):
    status = request.app.state.heartbeat.get_status(strategy_name)
    if status:
        return _resp(True, data=status)
    return _resp(False, msg="策略未注册")


@router.get("/heartbeat/history/{strategy_name}")
async def get_heartbeat_history(request: Request, strategy_name: str, limit: int = Query(100)):
    history = request.app.state.heartbeat.get_history(strategy_name, limit)
    return _resp(True, data=history)


@router.post("/alert/send")
async def send_alert(
    request: Request,
    title: str = Query(...),
    message: str = Query(...),
    level: str = Query("WARNING"),
    source: str = Query("system"),
    channels: str = Query("email", description="逗号分隔的通道"),
):
    try:
        alert_level = AlertLevel(level)
    except ValueError:
        return _resp(False, msg=f"不支持的告警级别: {level}")
    ch_list = []
    for ch in channels.split(","):
        try:
            ch_list.append(AlertChannel(ch.strip()))
        except ValueError:
            pass
    if not ch_list:
        ch_list = [AlertChannel.EMAIL]
    async with request.app.state.write_lock:
        result = request.app.state.alert_system.send_alert(title, message, alert_level, source, ch_list)
    return _resp(True, data=result.to_dict())


@router.get("/alert/list")
async def list_alerts(
    request: Request,
    level: str = Query(""),
    acknowledged: Optional[bool] = Query(None),
    limit: int = Query(50),
):
    filters = {}
    if level:
        try:
            filters["level"] = AlertLevel(level)
        except ValueError:
            pass
    if acknowledged is not None:
        filters["acknowledged"] = acknowledged
    alerts = request.app.state.alert_system.get_alerts(filters, limit)
    return _resp(True, data=[a.to_dict() for a in alerts])


@router.post("/alert/acknowledge/{alert_id}")
async def acknowledge_alert(request: Request, alert_id: str):
    async with request.app.state.write_lock:
        result = request.app.state.alert_system.acknowledge(alert_id)
    return _resp(result.get("success", False), data=result)


@router.get("/alert/stats")
async def get_alert_stats(request: Request):
    stats = request.app.state.alert_system.get_stats()
    return _resp(True, data=stats)


@router.post("/alert/config-channels")
async def configure_channels(
    request: Request,
    email: str = Query(""),
    dingtalk_webhook: str = Query(""),
    telegram_token: str = Query(""),
    wechat_webhook: str = Query(""),
):
    config = {
        "email": email,
        "dingtalk_webhook": dingtalk_webhook,
        "telegram_token": telegram_token,
        "wechat_webhook": wechat_webhook,
    }
    async with request.app.state.write_lock:
        request.app.state.alert_system.configure_channels(config)
    return _resp(True, msg="告警通道已配置")


@router.post("/anomaly/check-volume")
async def check_volume_anomaly(
    request: Request,
    symbol: str = Query(...),
    current_volume: float = Query(...),
):
    async with request.app.state.write_lock:
        event = request.app.state.anomaly_detector.check_volume_anomaly(symbol, current_volume)
    if event:
        return _resp(True, data=event.to_dict())
    return _resp(True, data=None, msg="未检测到成交量异常")


@router.post("/anomaly/check-price")
async def check_price_anomaly(
    request: Request,
    symbol: str = Query(...),
    current_return: float = Query(...),
):
    async with request.app.state.write_lock:
        event = request.app.state.anomaly_detector.check_price_anomaly(symbol, current_return)
    if event:
        return _resp(True, data=event.to_dict())
    return _resp(True, data=None, msg="未检测到价格异常")


@router.post("/anomaly/check-large-order")
async def check_large_order(
    request: Request,
    symbol: str = Query(...),
    order_value: float = Query(...),
):
    event = request.app.state.anomaly_detector.check_large_order(symbol, order_value)
    if event:
        return _resp(True, data=event.to_dict())
    return _resp(True, data=None, msg="未检测到大单异常")


@router.post("/anomaly/check-daily-loss")
async def check_daily_loss(
    request: Request,
    symbol: str = Query(...),
    daily_pnl_pct: float = Query(...),
):
    event = request.app.state.anomaly_detector.check_daily_loss(symbol, daily_pnl_pct)
    if event:
        return _resp(True, data=event.to_dict())
    return _resp(True, data=None, msg="未触发日亏损限制")


@router.post("/anomaly/check-frequency")
async def check_trade_frequency(request: Request, symbol: str = Query(...)):
    async with request.app.state.write_lock:
        event = request.app.state.anomaly_detector.check_high_frequency(symbol)
    if event:
        return _resp(True, data=event.to_dict())
    return _resp(True, data=None, msg="未检测到高频交易")


@router.post("/anomaly/check-opening-gap")
async def check_opening_gap(
    request: Request,
    symbol: str = Query(...),
    open_price: float = Query(...),
    prev_close: float = Query(...),
):
    event = request.app.state.anomaly_detector.detect_opening_anomaly(symbol, open_price, prev_close)
    if event:
        return _resp(True, data=event.to_dict())
    return _resp(True, data=None, msg="未检测到开盘跳空")


@router.get("/anomaly/events")
async def get_anomaly_events(request: Request, limit: int = Query(50)):
    events = request.app.state.anomaly_detector.get_recent_anomalies(limit)
    return _resp(True, data=events)


@router.get("/anomaly/stats")
async def get_anomaly_stats(request: Request):
    stats = request.app.state.anomaly_detector.get_anomaly_stats()
    return _resp(True, data=stats)


@router.get("/perf/system")
async def get_system_metrics(request: Request):
    metrics = request.app.state.perf_dashboard.get_system_metrics()
    return _resp(True, data=metrics)


@router.post("/perf/record-api-latency")
async def record_api_latency(
    request: Request,
    endpoint: str = Query(...),
    latency_ms: float = Query(...),
    status_code: int = Query(200),
):
    async with request.app.state.write_lock:
        request.app.state.perf_dashboard.record_api_latency(endpoint, latency_ms, status_code)
    return _resp(True, msg="延迟已记录")


@router.get("/perf/api-latency")
async def get_api_latency_stats(request: Request):
    stats = request.app.state.perf_dashboard.get_api_latency_stats()
    return _resp(True, data=stats)


@router.post("/perf/record-data-latency")
async def record_data_latency(
    request: Request,
    source: str = Query(...),
    symbol: str = Query(...),
    latency_ms: float = Query(...),
):
    async with request.app.state.write_lock:
        request.app.state.perf_dashboard.record_data_latency(source, symbol, latency_ms)
    return _resp(True, msg="数据延迟已记录")


@router.post("/perf/record-connection-status")
async def record_connection_status(
    request: Request,
    source: str = Query(...),
    status: str = Query(...),
    latency_ms: float = Query(0),
):
    async with request.app.state.write_lock:
        request.app.state.perf_dashboard.record_connection_status(source, status, latency_ms)
    return _resp(True, msg="连接状态已记录")


@router.get("/perf/connection-status")
async def get_connection_status(request: Request):
    status = request.app.state.perf_dashboard.get_connection_status()
    return _resp(True, data=status)


@router.get("/perf/health-score")
async def get_health_score(request: Request):
    score = request.app.state.perf_dashboard.get_health_score()
    return _resp(True, data={"health_score": score})


@router.get("/perf/metric-series")
async def get_metric_series(
    request: Request,
    metric_name: str = Query(...),
    limit: int = Query(100),
):
    series = request.app.state.perf_dashboard.get_metric_series(metric_name, limit)
    return _resp(True, data=series)


@router.get("/perf/dashboard")
async def get_perf_dashboard(request: Request):
    dashboard = request.app.state.perf_dashboard.get_dashboard()
    return _resp(True, data=dashboard)


@router.get("/perf/data-latency-heatmap")
async def get_data_latency_heatmap(request: Request):
    heatmap = request.app.state.perf_dashboard.get_data_latency_heatmap()
    return _resp(True, data=heatmap)


@router.get("/perf/summary")
async def get_perf_summary(request: Request):
    summary = request.app.state.perf_dashboard.get_summary()
    return _resp(True, data=summary)


@router.post("/audit/log-signal")
async def log_signal_event(
    request: Request,
    strategy: str = Query(...),
    symbol: str = Query(...),
    signal_type: str = Query(...),
    signal_strength: float = Query(0),
):
    async with request.app.state.write_lock:
        request.app.state.audit_log.log_signal(strategy, symbol, signal_type, signal_strength)
    return _resp(True, msg="信号事件已记录")


@router.post("/audit/log-risk")
async def log_risk_event(
    request: Request,
    risk_model: str = Query(...),
    approved: bool = Query(True),
    details: str = Query("{}"),
):
    import json
    try:
        d = json.loads(details)
    except Exception:
        d = {}
    async with request.app.state.write_lock:
        request.app.state.audit_log.log_risk_check(risk_model, approved, d)
    return _resp(True, msg="风控事件已记录")


@router.post("/audit/log-order")
async def log_order_event(
    request: Request,
    executor: str = Query(...),
    symbol: str = Query(...),
    side: str = Query(...),
    quantity: int = Query(...),
    price: float = Query(0),
):
    async with request.app.state.write_lock:
        request.app.state.audit_log.log_order(executor, symbol, side, quantity, price)
    return _resp(True, msg="订单事件已记录")


@router.post("/audit/log-fill")
async def log_fill_event(
    request: Request,
    broker: str = Query(...),
    symbol: str = Query(...),
    fill_price: float = Query(...),
    fill_qty: int = Query(...),
):
    async with request.app.state.write_lock:
        request.app.state.audit_log.log_fill(broker, symbol, fill_price, fill_qty)
    return _resp(True, msg="成交事件已记录")


@router.post("/audit/log-settlement")
async def log_settlement_event(
    request: Request,
    symbol: str = Query(...),
    pnl: float = Query(0),
    pnl_pct: float = Query(0),
):
    async with request.app.state.write_lock:
        request.app.state.audit_log.log_settlement(symbol, pnl, pnl_pct)
    return _resp(True, msg="结算事件已记录")


@router.get("/audit/query")
async def query_audit_log(
    request: Request,
    event_type: str = Query(""),
    actor: str = Query(""),
    start_time: str = Query(""),
    end_time: str = Query(""),
    limit: int = Query(100),
):
    entries = request.app.state.audit_log.query(
        event_type=event_type or None,
        actor=actor or None,
        start_time=start_time or None,
        end_time=end_time or None,
        limit=limit,
    )
    return _resp(True, data=entries)


@router.get("/audit/compliance-report")
async def get_compliance_report(request: Request, date: str = Query("")):
    report = request.app.state.audit_log.generate_regulatory_report(date or None)
    return _resp(True, data=report)


@router.get("/audit/trace/{event_id}")
async def trace_event_chain(request: Request, event_id: str):
    chain = request.app.state.audit_log.get_full_chain(event_id)
    return _resp(True, data=chain)
