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

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

BASE_DIR = Path(__file__).parent


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger = logging.getLogger(__name__)
    logger.info("QuantVision starting up...")

    from core.data_fetcher import SmartDataFetcher
    from core.ai.adaptive_params import AdaptiveParamOptimizer
    from core.ai.nl_strategy import NLStrategyGenerator
    from core.ai.pattern_detect import AnomalyPatternDetector
    from core.ai.portfolio_ai import PortfolioAIAdvisor
    from core.ai.prediction_models import PredictionModelPlatform
    from core.monitor.heartbeat import StrategyHeartbeatMonitor
    from core.monitor.alert_system import SmartAlertSystem
    from core.monitor.anomaly_detect import AnomalyDetector
    from core.monitor.perf_dashboard import PerformanceDashboard
    from core.monitor.audit_log import ComplianceAuditLog
    from core.risk.var_monitor import VaRMonitor
    from core.risk.position_manager import DynamicPositionManager
    from core.risk.stop_loss import MultiDimensionStopLoss
    from core.risk.stress_test import RiskStressTest
    from core.risk.risk_attribution import RiskAttribution
    from core.portfolio.capital_allocator import CapitalAllocator
    from core.portfolio.rebalance import RebalanceEngine
    from core.research.fundamental import FundamentalFactorLibrary
    from core.platform.scheduler import TaskScheduler
    from core.platform.env_manager import EnvironmentManager
    from core.platform.auth_security import AuthSecurityManager
    from core.backtest_v2.event_engine import EventBacktestEngine
    from core.backtest_v2.microstructure import MicrostructureSimulator
    from core.backtest_v2.portfolio_backtest import PortfolioBacktester
    from core.backtest_v2.param_optimizer import ParamOptimizer
    from core.backtest_v2.monte_carlo import MonteCarloStressTest
    from core.research.sentiment import MarketSentimentAnalyzer
    from core.research.sector import SectorResearch
    from core.research.report_ai import ReportAIAssistant
    from core.portfolio.attribution import PerformanceAttribution
    from core.portfolio.derivatives import DerivativesManager
    from core.portfolio.tearsheet import TearsheetGenerator
    from core.platform.microservice import MicroserviceManager
    from core.platform.workspace import WorkspaceManager
    from core.execution.order_router import SmartOrderRouter
    from core.execution.algo_engine import AlgoExecutionEngine
    from core.execution.multi_account import MultiAccountManager
    from core.execution.paper_live import PaperLiveSwitch
    from core.strategy_v2.visual_builder import VisualStrategyBuilder
    from core.strategy_v2.signal_execution import SignalExecutionDecoupler
    from core.strategy_v2.ml_strategy import MLStrategyModule
    from core.strategy_v2.factor_research import FactorResearchWorkbench
    from core.strategy_v2.strategy_version import StrategyVersionControl
    from core.backtest import BacktestEngine
    from core.strategies import CompositeStrategy
    from core.simulated_trading import SimulatedTrading
    from core.data_infra.alt_data import AltDataPipeline
    from core.data_infra.tick_store import TickStore
    from core.data_infra.data_adapter import UnifiedDataAdapter
    from core.data_infra.realtime_stream import RealtimeStreamManager
    from core.data_infra.history_manager import HistoryDataManager

    app.state.fetcher = SmartDataFetcher()
    app.state.adaptive_optimizer = AdaptiveParamOptimizer()
    app.state.nl_generator = NLStrategyGenerator()
    app.state.pattern_detector = AnomalyPatternDetector()
    app.state.portfolio_ai = PortfolioAIAdvisor()
    app.state.prediction_platform = PredictionModelPlatform()
    app.state.heartbeat = StrategyHeartbeatMonitor()
    app.state.alert_system = SmartAlertSystem()
    app.state.anomaly_detector = AnomalyDetector()
    app.state.perf_dashboard = PerformanceDashboard()
    app.state.audit_log = ComplianceAuditLog()
    app.state.var_monitor = VaRMonitor()
    app.state.position_mgr = DynamicPositionManager()
    app.state.stop_loss_mgr = MultiDimensionStopLoss()
    app.state.stress_test = RiskStressTest()
    app.state.risk_attr = RiskAttribution()
    app.state.capital_allocator = CapitalAllocator()
    app.state.rebalance_engine = RebalanceEngine()
    app.state.fundamental_lib = FundamentalFactorLibrary()
    app.state.scheduler = TaskScheduler()
    app.state.env_manager = EnvironmentManager()
    app.state.auth_manager = AuthSecurityManager()
    app.state.event_engine = EventBacktestEngine()
    app.state.micro_sim = MicrostructureSimulator()
    app.state.portfolio_bt = PortfolioBacktester()
    app.state.param_optimizer = ParamOptimizer()
    app.state.mc_stress = MonteCarloStressTest()
    app.state.sentiment_analyzer = MarketSentimentAnalyzer()
    app.state.sector_research = SectorResearch()
    app.state.report_ai = ReportAIAssistant()
    app.state.attribution = PerformanceAttribution()
    app.state.derivatives_mgr = DerivativesManager()
    app.state.tearsheet_gen = TearsheetGenerator()
    app.state.microservice_mgr = MicroserviceManager()
    app.state.workspace_mgr = WorkspaceManager()
    app.state.order_router = SmartOrderRouter()
    app.state.algo_engine = AlgoExecutionEngine()
    app.state.account_mgr = MultiAccountManager()
    app.state.paper_live = PaperLiveSwitch()
    app.state.builder = VisualStrategyBuilder()
    app.state.decoupler = SignalExecutionDecoupler()
    app.state.ml_module = MLStrategyModule()
    app.state.factor_wb = FactorResearchWorkbench()
    app.state.version_ctrl = StrategyVersionControl()
    app.state.backtest_engine = BacktestEngine()
    app.state.composite_strategy = CompositeStrategy()
    app.state.sim_trading = SimulatedTrading()
    app.state.alt_pipeline = AltDataPipeline()
    app.state.tick_store = TickStore()
    app.state.data_adapter = UnifiedDataAdapter()
    app.state.stream_manager = RealtimeStreamManager()
    app.state.history_manager = HistoryDataManager()

    app.state.write_lock = asyncio.Lock()

    try:
        from core.stock_search import _build_index
        _build_index()
        logger.info("Stock search index built")
    except Exception as e:
        logger.warning(f"Failed to build search index: {e}")

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
        await fetcher.get_hot_stocks()
        logging.getLogger(__name__).info("Hot stocks cache warmed")
    except Exception as e:
        logging.getLogger(__name__).debug(f"Hot stocks warm-up failed: {e}")


app = FastAPI(title="QuantVision", docs_url=None, redoc_url=None, lifespan=lifespan)

app.add_middleware(GZipMiddleware, minimum_size=500)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

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
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")


@app.get("/")
def index():
    return FileResponse(str(BASE_DIR / "static" / "index.html"))


@app.post("/shutdown")
async def shutdown_server():
    shutdown_event.set()
    return {"success": True, "message": "Server shutting down..."}


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
