"""
QuantCore 量化交易系统 - 主入口
高性能异步量化交易平台，支持A股/港股/美股全品种
"""
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
from api.data_routes import data_router
from api.backtest_routes import backtest_router
from api.risk_routes import risk_router
from api.strategy_routes import strategy_router
from api.execution_routes import execution_router
from api.portfolio_routes import portfolio_router
from api.monitor_routes import monitor_router
from api.research_routes import research_router
from api.ai_routes import ai_router
from api.platform_routes import platform_router
from api.analysis_routes import analysis_router

from core.logger import setup_logger

setup_logger(logging.INFO)
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).parent

# 懒加载注册表 - 避免启动时加载所有模块
_lazy_registry = {}


def _lazy_state(app, attr, module_path, class_name, *args, **kwargs):
    """懒加载状态对象，按需初始化"""
    if not hasattr(app.state, attr) or getattr(app.state, attr) is None:
        key = f"{module_path}.{class_name}"
        if key not in _lazy_registry:
            mod = __import__(module_path, fromlist=[class_name])
            _lazy_registry[key] = getattr(mod, class_name)
        setattr(app.state, attr, _lazy_registry[key](*args, **kwargs))
    return getattr(app.state, attr)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    logger.info("🚀 QuantCore 启动中...")

    # 核心依赖 - 启动时必须初始化
    from core.database import get_db
    from core.data_fetcher import SmartDataFetcher
    from core.analysis_service import AnalysisService
    from core.backtest import BacktestEngine
    from core.strategies import CompositeStrategy
    from core.simulated_trading import SimulatedTrading
    from core.market_detector import MarketDetector as MarketRegimeDetector
    from core.prediction import PricePredictor as ModelPredictionEngine
    from core.indicators import TechnicalIndicators as TechnicalIndicator

    app.state.db = get_db()
    app.state.fetcher = SmartDataFetcher()
    app.state.analysis_service = AnalysisService()
    app.state.backtest_engine = BacktestEngine()
    app.state.composite_strategy = CompositeStrategy()
    app.state.sim_trading = SimulatedTrading()
    app.state.market_detector = MarketRegimeDetector()
    app.state.prediction_engine = ModelPredictionEngine()
    app.state.indicator_engine = TechnicalIndicator()
    app.state.start_time = time.time()
    app.state.write_lock = asyncio.Lock()

    # 加载股票搜索索引
    try:
        from core.stock_search import _STOCK_INDEX
        logger.info(f"📊 股票搜索索引已加载: {len(_STOCK_INDEX)} 条记录")
    except Exception as e:
        logger.warning(f"⚠️ 搜索索引加载失败: {e}")

    # 预热缓存
    try:
        asyncio.create_task(_warm_cache(app.state.fetcher))
    except Exception as e:
        logger.warning(f"⚠️ 缓存预热失败: {e}")

    # 确保数据目录存在
    try:
        os.makedirs(os.path.join(BASE_DIR, "data"), exist_ok=True)
        os.makedirs(os.path.join(BASE_DIR, "static"), exist_ok=True)
    except Exception:
        pass

    logger.info("✅ QuantCore 启动完成")
    yield

    logger.info("🛑 QuantCore 关闭中...")


async def _warm_cache(fetcher):
    """预热热门数据缓存"""
    await asyncio.sleep(2)
    try:
        await fetcher.refresh_stock_info()
        await fetcher.get_hot_stocks()
        logger.info("🔥 热门股票缓存已预热")
    except Exception as e:
        logger.debug(f"缓存预热失败: {e}")


# ==================== FastAPI 应用实例 ====================
app = FastAPI(
    title="QuantCore",
    description="高性能量化交易平台 - 支持A股/港股/美股",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# GZip压缩
app.add_middleware(GZipMiddleware, minimum_size=500)

# CORS跨域
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "DELETE", "OPTIONS", "PUT"],
    allow_headers=["*"],
    allow_credentials=True,
)


# ==================== 懒加载中间件 ====================
@app.middleware("http")
async def lazy_state_middleware(request, call_next):
    """按需懒加载各模块实例"""
    state = request.app.state
    if not hasattr(state, "write_lock"):
        state.write_lock = asyncio.Lock()

    # 模块路径映射表
    lazy_map = {
        # 监控模块
        "heartbeat": ("core.monitor.heartbeat", "StrategyHeartbeatMonitor"),
        "alert_system": ("core.monitor.alert_system", "SmartAlertSystem"),
        "anomaly_detector": ("core.monitor.anomaly_detect", "AnomalyDetector"),
        "perf_dashboard": ("core.monitor.perf_dashboard", "PerformanceDashboard"),
        "audit_log": ("core.monitor.audit_log", "ComplianceAuditLog"),
        # 风控模块
        "var_monitor": ("core.risk.var_monitor", "VaRMonitor"),
        "position_mgr": ("core.risk.position_manager", "DynamicPositionManager"),
        "stop_loss_mgr": ("core.risk.stop_loss", "MultiDimensionStopLoss"),
        "circuit_breaker": ("core.risk.circuit_breaker", "RiskCircuitBreaker"),
        "risk_attr": ("core.risk.risk_attribution", "RiskAttribution"),
        # 组合模块
        "capital_allocator": ("core.portfolio.capital_allocator", "CapitalAllocator"),
        "rebalance_engine": ("core.portfolio.rebalance", "RebalanceEngine"),
        "attribution": ("core.portfolio.attribution", "PerformanceAttribution"),
        "derivatives_mgr": ("core.portfolio.derivatives", "DerivativesManager"),
        "tearsheet_gen": ("core.portfolio.tearsheet", "TearsheetGenerator"),
        # 研究模块
        "fundamental_lib": ("core.research.fundamental", "FundamentalFactorLibrary"),
        "sentiment_analyzer": ("core.research.sentiment", "MarketSentimentAnalyzer"),
        "sector_research": ("core.research.sector", "SectorResearch"),
        "report_ai": ("core.research.report_ai", "ReportAIAssistant"),
        # 平台模块
        "scheduler": ("core.platform.scheduler", "TaskScheduler"),
        "env_manager": ("core.platform.env_manager", "EnvironmentManager"),
        "auth_manager": ("core.platform.auth_security", "AuthSecurityManager"),
        "microservice_mgr": ("core.platform.microservice", "MicroserviceManager"),
        "workspace_mgr": ("core.platform.workspace", "WorkspaceManager"),
        # 回测V2模块
        "event_engine": ("core.backtest_v2.event_engine", "EventBacktestEngine"),
        "micro_sim": ("core.backtest_v2.microstructure", "MicrostructureSimulator"),
        "portfolio_bt": ("core.backtest_v2.portfolio_backtest", "PortfolioBacktester"),
        "param_optimizer": ("core.backtest_v2.param_optimizer", "ParamOptimizer"),
        "mc_stress": ("core.backtest_v2.monte_carlo", "MonteCarloStressTest"),
        # 执行模块
        "order_router": ("core.execution.order_router", "SmartOrderRouter"),
        "algo_engine": ("core.execution.algo_engine", "AlgoExecutionEngine"),
        "account_mgr": ("core.execution.multi_account", "MultiAccountManager"),
        "paper_live": ("core.execution.paper_live", "PaperLiveSwitch"),
        # 策略V2模块
        "builder": ("core.strategy_v2.visual_builder", "VisualStrategyBuilder"),
        "decoupler": ("core.strategy_v2.signal_execution", "SignalExecutionDecoupler"),
        "ml_module": ("core.strategy_v2.ml_strategy", "MLStrategyModule"),
        "factor_wb": ("core.strategy_v2.factor_research", "FactorResearchWorkbench"),
        "version_ctrl": ("core.strategy_v2.strategy_version", "StrategyVersionControl"),
        # AI模块
        "adaptive_optimizer": ("core.ai.adaptive_params", "AdaptiveParamOptimizer"),
        "nl_generator": ("core.ai.nl_strategy", "NLStrategyGenerator"),
        "pattern_detector": ("core.ai.pattern_detect", "AnomalyPatternDetector"),
        "portfolio_ai": ("core.ai.portfolio_ai", "PortfolioAIAdvisor"),
        "prediction_platform": ("core.ai.prediction_models", "PredictionModelPlatform"),
        # 数据基础设施
        "alt_pipeline": ("core.data_infra.alt_data", "AltDataPipeline"),
        "tick_store": ("core.data_infra.tick_store", "TickStore"),
        "data_adapter": ("core.data_infra.data_adapter", "UnifiedDataAdapter"),
        "stream_manager": ("core.data_infra.realtime_stream", "RealtimeStreamManager"),
        "history_manager": ("core.data_infra.history_manager", "HistoryDataManager"),
    }

    path = request.url.path
    for attr, (mod_path, cls_name) in lazy_map.items():
        if not hasattr(state, attr) or getattr(state, attr) is None:
            # 根据URL路径判断是否加载对应模块
            path_prefix = f"/{attr.replace('_', '-')}"
            if path_prefix in path or f"/{attr.split('_')[0]}" in path:
                _lazy_state(request.app, attr, mod_path, cls_name)

    return await call_next(request)


# ==================== 路由注册 ====================
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

# 静态文件
static_dir = BASE_DIR / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


# ==================== 根路由 ====================
@app.get("/")
def index():
    """返回前端首页"""
    index_file = BASE_DIR / "static" / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return {
        "name": "QuantCore",
        "version": "2.0.0",
        "status": "running",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """健康检查端点"""
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "version": "2.0.0"
    }


@app.post("/shutdown")
async def shutdown_server():
    """关闭服务器"""
    shutdown_event.set()
    return {"success": True, "message": "Server shutting down..."}


@app.post("/client-disconnect")
async def client_disconnect():
    """客户端断开连接"""
    shutdown_event.set()
    return {"success": True, "message": "Shutdown initiated"}


# ==================== 关闭事件管理 ====================
shutdown_event = threading.Event()


def _watch_shutdown():
    """监听关闭事件"""
    shutdown_event.wait()
    time.sleep(0.5)
    os.kill(os.getpid(), signal.SIGTERM)


# ==================== 入口 ====================
if __name__ == "__main__":
    import subprocess

    _fp = [None]

    def start_frontend():
        """启动前端开发服务器"""
        frontend_dir = BASE_DIR / "frontend"
        if not frontend_dir.exists():
            logger.warning("frontend 目录不存在，跳过前端启动")
            return
        try:
            _fp[0] = subprocess.Popen(
                ["npx", "vite", "--host", "0.0.0.0"],
                cwd=str(frontend_dir),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            logger.info("前端开发服务器已启动 (http://localhost:3000)")
        except Exception as e:
            logger.warning(f"启动前端失败: {e}")

    def open_browser():
        """自动打开浏览器"""
        time.sleep(3)
        webbrowser.open("http://localhost:3000")

    def stop_frontend():
        """关闭前端服务器"""
        if _fp[0]:
            _fp[0].terminate()
            _fp[0].wait(timeout=5)

    threading.Thread(target=start_frontend, daemon=True).start()
    threading.Thread(target=open_browser, daemon=True).start()
    threading.Thread(target=_watch_shutdown, daemon=True).start()

    try:
        uvicorn.run(app, host="0.0.0.0", port=8080, reload=False, log_level="warning")
    finally:
        stop_frontend()
