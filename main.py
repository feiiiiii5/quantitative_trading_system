import asyncio
import logging
import os
import signal
import threading
import time
import webbrowser
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.gzip import GZipMiddleware

from api.routes import router
from api.websocket import ws_router
from api.data_routes import router as data_router
from api.backtest_routes import router as backtest_router
from api.risk_routes import router as risk_router
from api.strategy_routes import router as strategy_router
from api.execution_routes import router as execution_router
from api.portfolio_routes import router as portfolio_router
from api.monitor_routes import router as monitor_router
from api.research_routes import router as research_router
from api.ai_routes import router as ai_router
from api.platform_routes import router as platform_router
from api.analysis_routes import router as analysis_router
from core.logger import setup_logger

setup_logger(logging.INFO)

BASE_DIR = Path(__file__).parent

logger = logging.getLogger(__name__)

_lazy_registry = {}


def _lazy_state(app, attr, module_path, class_name, *args, **kwargs):
    if not hasattr(app.state, attr) or getattr(app.state, attr) is None:
        key = f"{module_path}.{class_name}"
        if key not in _lazy_registry:
            mod = __import__(module_path, fromlist=[class_name])
            _lazy_registry[key] = getattr(mod, class_name)
        setattr(app.state, attr, _lazy_registry[key](*args, **kwargs))
    return getattr(app.state, attr)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("QuantVision starting up...")

    from core.database import get_db
    from core.data_fetcher import SmartDataFetcher
    from core.analysis_service import AnalysisService
    from core.backtest import BacktestEngine
    from core.strategies import CompositeStrategy
    from core.simulated_trading import SimulatedTrading

    app.state.db = get_db()
    app.state.fetcher = SmartDataFetcher()
    app.state.analysis_service = AnalysisService()
    app.state.backtest_engine = BacktestEngine()
    app.state.composite_strategy = CompositeStrategy()
    app.state.sim_trading = SimulatedTrading()
    app.state.start_time = time.time()
    app.state.write_lock = asyncio.Lock()

    try:
        from core.stock_search import _STOCK_INDEX
        logger.info(f"Stock search index loaded with {len(_STOCK_INDEX)} entries")
    except Exception as e:
        logger.warning(f"Failed to load search index: {e}")

    try:
        asyncio.create_task(_warm_cache(app.state.fetcher))
    except Exception as e:
        logger.warning(f"Cache warm-up failed: {e}")

    try:
        os.makedirs(os.path.join(BASE_DIR, "data"), exist_ok=True)
    except Exception:
        pass

    yield

    logger.info("QuantVision shutting down...")


async def _warm_cache(fetcher):
    await asyncio.sleep(2)
    try:
        await fetcher.refresh_stock_info()
        await fetcher.get_hot_stocks()
        logging.getLogger(__name__).info("Hot stocks cache warmed")
    except Exception as e:
        logging.getLogger(__name__).debug(f"Hot stocks warm-up failed: {e}")


app = FastAPI(title="QuantVision", docs_url=None, redoc_url=None, lifespan=lifespan)

app.add_middleware(GZipMiddleware, minimum_size=500)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


@app.middleware("http")
async def lazy_state_middleware(request, call_next):
    state = request.app.state
    if not hasattr(state, "write_lock"):
        state.write_lock = asyncio.Lock()

    lazy_map = {
        "heartbeat": ("core.monitor.heartbeat", "StrategyHeartbeatMonitor"),
        "alert_system": ("core.monitor.alert_system", "SmartAlertSystem"),
        "anomaly_detector": ("core.monitor.anomaly_detect", "AnomalyDetector"),
        "perf_dashboard": ("core.monitor.perf_dashboard", "PerformanceDashboard"),
        "audit_log": ("core.monitor.audit_log", "ComplianceAuditLog"),
        "var_monitor": ("core.risk.var_monitor", "VaRMonitor"),
        "position_mgr": ("core.risk.position_manager", "DynamicPositionManager"),
        "stop_loss_mgr": ("core.risk.stop_loss", "MultiDimensionStopLoss"),
        "stress_test": ("core.risk.stress_test", "RiskStressTest"),
        "risk_attr": ("core.risk.risk_attribution", "RiskAttribution"),
        "capital_allocator": ("core.portfolio.capital_allocator", "CapitalAllocator"),
        "rebalance_engine": ("core.portfolio.rebalance", "RebalanceEngine"),
        "fundamental_lib": ("core.research.fundamental", "FundamentalFactorLibrary"),
        "scheduler": ("core.platform.scheduler", "TaskScheduler"),
        "env_manager": ("core.platform.env_manager", "EnvironmentManager"),
        "auth_manager": ("core.platform.auth_security", "AuthSecurityManager"),
        "event_engine": ("core.backtest_v2.event_engine", "EventBacktestEngine"),
        "micro_sim": ("core.backtest_v2.microstructure", "MicrostructureSimulator"),
        "portfolio_bt": ("core.backtest_v2.portfolio_backtest", "PortfolioBacktester"),
        "param_optimizer": ("core.backtest_v2.param_optimizer", "ParamOptimizer"),
        "mc_stress": ("core.backtest_v2.monte_carlo", "MonteCarloStressTest"),
        "sentiment_analyzer": ("core.research.sentiment", "MarketSentimentAnalyzer"),
        "sector_research": ("core.research.sector", "SectorResearch"),
        "report_ai": ("core.research.report_ai", "ReportAIAssistant"),
        "attribution": ("core.portfolio.attribution", "PerformanceAttribution"),
        "derivatives_mgr": ("core.portfolio.derivatives", "DerivativesManager"),
        "tearsheet_gen": ("core.portfolio.tearsheet", "TearsheetGenerator"),
        "microservice_mgr": ("core.platform.microservice", "MicroserviceManager"),
        "workspace_mgr": ("core.platform.workspace", "WorkspaceManager"),
        "order_router": ("core.execution.order_router", "SmartOrderRouter"),
        "algo_engine": ("core.execution.algo_engine", "AlgoExecutionEngine"),
        "account_mgr": ("core.execution.multi_account", "MultiAccountManager"),
        "paper_live": ("core.execution.paper_live", "PaperLiveSwitch"),
        "builder": ("core.strategy_v2.visual_builder", "VisualStrategyBuilder"),
        "decoupler": ("core.strategy_v2.signal_execution", "SignalExecutionDecoupler"),
        "ml_module": ("core.strategy_v2.ml_strategy", "MLStrategyModule"),
        "factor_wb": ("core.strategy_v2.factor_research", "FactorResearchWorkbench"),
        "version_ctrl": ("core.strategy_v2.strategy_version", "StrategyVersionControl"),
        "adaptive_optimizer": ("core.ai.adaptive_params", "AdaptiveParamOptimizer"),
        "nl_generator": ("core.ai.nl_strategy", "NLStrategyGenerator"),
        "pattern_detector": ("core.ai.pattern_detect", "AnomalyPatternDetector"),
        "portfolio_ai": ("core.ai.portfolio_ai", "PortfolioAIAdvisor"),
        "prediction_platform": ("core.ai.prediction_models", "PredictionModelPlatform"),
        "alt_pipeline": ("core.data_infra.alt_data", "AltDataPipeline"),
        "tick_store": ("core.data_infra.tick_store", "TickStore"),
        "data_adapter": ("core.data_infra.data_adapter", "UnifiedDataAdapter"),
        "stream_manager": ("core.data_infra.realtime_stream", "RealtimeStreamManager"),
        "history_manager": ("core.data_infra.history_manager", "HistoryDataManager"),
    }

    path = request.url.path
    for attr, (mod_path, cls_name) in lazy_map.items():
        if not hasattr(state, attr) or getattr(state, attr) is None:
            if attr in path or any(attr in seg for seg in path.split("/")):
                _lazy_state(request.app, attr, mod_path, cls_name)

    return await call_next(request)


app.include_router(router, prefix="/api")
app.include_router(ws_router)
app.include_router(data_router, prefix="/api")
app.include_router(backtest_router, prefix="/api")
app.include_router(risk_router, prefix="/api")
app.include_router(strategy_router, prefix="/api")
app.include_router(execution_router, prefix="/api")
app.include_router(portfolio_router, prefix="/api")
app.include_router(monitor_router, prefix="/api")
app.include_router(research_router, prefix="/api")
app.include_router(ai_router, prefix="/api")
app.include_router(platform_router, prefix="/api")
app.include_router(analysis_router, prefix="/api")
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")


@app.get("/")
def index():
    return FileResponse(str(BASE_DIR / "static" / "index.html"))


@app.post("/shutdown")
async def shutdown_server():
    shutdown_event.set()
    return {"success": True, "message": "Server shutting down..."}


@app.post("/client-disconnect")
async def client_disconnect():
    shutdown_event.set()
    return {"success": True, "message": "Shutdown initiated"}


shutdown_event = threading.Event()


def _watch_shutdown():
    shutdown_event.wait()
    time.sleep(0.5)
    os.kill(os.getpid(), signal.SIGTERM)


if __name__ == "__main__":
    def open_browser():
        time.sleep(1.5)
        webbrowser.open("http://localhost:8080")

    threading.Thread(target=open_browser, daemon=True).start()
    threading.Thread(target=_watch_shutdown, daemon=True).start()
    uvicorn.run(app, host="0.0.0.0", port=8080, reload=False, log_level="warning")
