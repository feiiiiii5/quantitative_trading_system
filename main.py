"""
QuantCore - 量化交易系统
简洁高效，一键启动
"""
import asyncio
import gc
import logging
import multiprocessing
import os
import subprocess
import threading
import time
import traceback
import webbrowser
from contextlib import asynccontextmanager
from pathlib import Path

try:
    import uvloop
    uvloop.install()
    _has_uvloop = True
except ImportError:
    _has_uvloop = False

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from api.routes import router, push_realtime_data
from core.logger import setup_logger

import sys
try:
    if sys.platform == "darwin":
        multiprocessing.set_start_method("spawn")
    else:
        multiprocessing.set_start_method("fork")
except RuntimeError:
    pass

setup_logger(logging.INFO)
logger = logging.getLogger(__name__)
gc.set_threshold(700, 10, 10)

BASE_DIR = Path(__file__).parent
PORT = 8080
_preload_done = threading.Event()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("QuantCore 启动中...")

    from core.database import get_db, get_cache_manager
    from core.data_fetcher import SmartDataFetcher
    from core.backtest import BacktestEngine
    from core.strategies import CompositeStrategy
    from core.simulated_trading import SimulatedTrading

    app.state.db = get_db()
    app.state.fetcher = SmartDataFetcher()
    app.state.composite_strategy = CompositeStrategy()
    app.state.backtest_engine = BacktestEngine()
    app.state.trading = SimulatedTrading()
    app.state.start_time = time.time()
    app.state._request_count = 0
    app.state._total_response_time = 0.0
    app.state._start_time = time.time()

    try:
        from core.data_fetcher import get_aiohttp_session
        await get_aiohttp_session()
        logger.info("aiohttp session 预创建完成")
    except Exception as e:
        logger.debug(f"aiohttp session pre-create failed: {e}")

    try:
        from core.stock_search import _STOCK_INDEX
        logger.info(f"股票搜索索引: {len(_STOCK_INDEX)} 条")
    except Exception:
        pass

    try:
        from core.stock_search import build_search_index_async
        count = await build_search_index_async()
        logger.info(f"搜索倒排索引构建完成: {count} 只股票")
    except Exception as e:
        logger.debug(f"搜索索引构建失败: {e}")

    try:
        asyncio.create_task(_preload_data(app.state.fetcher))
    except Exception as e:
        logger.debug(f"Preload task start failed: {e}")

    try:
        asyncio.create_task(push_realtime_data(app.state.fetcher))
    except Exception as e:
        logger.debug(f"WS push task start failed: {e}")

    try:
        asyncio.create_task(_scheduler_loop(app))
    except Exception as e:
        logger.debug(f"Scheduler task start failed: {e}")

    try:
        from core.market_data import start_background_refresh
        start_background_refresh()
    except Exception:
        pass

    os.makedirs(BASE_DIR / "data", exist_ok=True)
    os.makedirs(BASE_DIR / "static", exist_ok=True)

    logger.info(f"QuantCore 启动完成 -> http://localhost:{PORT}")
    yield

    logger.info("QuantCore 正在关闭...")

    try:
        from core.data_fetcher import _aiohttp_session
        if _aiohttp_session is not None and not _aiohttp_session.closed:
            await _aiohttp_session.close()
            logger.info("aiohttp session 已关闭")
    except Exception as e:
        logger.debug(f"aiohttp session close failed: {e}")

    try:
        from core.market_data import stop_background_refresh
        stop_background_refresh()
    except Exception:
        pass

    try:
        cm = get_cache_manager()
        cm.flush()
    except Exception as e:
        logger.debug(f"Cache flush on shutdown failed: {e}")

    try:
        trading: SimulatedTrading = app.state.trading
        db = get_db()
        db.set_config("portfolio_snapshot", trading.get_account_info())
        logger.info("Portfolio snapshot saved")
    except Exception as e:
        logger.debug(f"Portfolio snapshot failed: {e}")

    logger.info("QuantCore 已关闭")


async def _preload_data(fetcher):
    await asyncio.sleep(2)
    try:
        await fetcher.preload_all()
        logger.info("预加载数据完成")
    except Exception as e:
        logger.debug(f"Preload data failed: {e}")
    finally:
        _preload_done.set()


async def _scheduler_loop(app):
    await asyncio.sleep(5)
    ws_rt_interval = 5
    hot_refresh_interval = 60
    temperature_interval = 300
    fundamental_interval = 3600
    cleanup_hour = 2

    last_ws_rt = 0
    last_hot = 0
    last_temp = 0
    last_fundamental = 0
    last_cleanup_date = ""

    while True:
        try:
            now = time.time()
            from core.data_fetcher import SmartDataFetcher
            fetcher: SmartDataFetcher = app.state.fetcher

            if now - last_ws_rt >= ws_rt_interval:
                try:
                    from api.routes import _manager, _is_trading_hours
                    if _is_trading_hours() and _manager.connections:
                        subscribed = _manager.get_all_subscribed_symbols()
                        for symbol in list(subscribed)[:30]:
                            try:
                                await asyncio.wait_for(fetcher.get_realtime(symbol), timeout=3)
                            except (asyncio.TimeoutError, Exception):
                                pass
                    last_ws_rt = now
                except Exception as e:
                    logger.warning("WS realtime refresh error: %s", e, exc_info=True)

            if now - last_hot >= hot_refresh_interval:
                try:
                    await fetcher.refresh_hot_symbols_cache()
                    last_hot = now
                except Exception as e:
                    logger.warning("Hot symbols refresh error: %s", e, exc_info=True)

            if now - last_temp >= temperature_interval:
                try:
                    await fetcher.get_market_temperature()
                    last_temp = now
                except Exception as e:
                    logger.warning("Temperature refresh error: %s", e, exc_info=True)

            if now - last_fundamental >= fundamental_interval:
                try:
                    from core.database import get_db
                    db = get_db()
                    watchlist = db.get_config("watchlist", [])
                    if isinstance(watchlist, list):
                        for symbol in watchlist[:10]:
                            try:
                                from core.market_detector import MarketDetector
                                market = MarketDetector.detect(symbol)
                                await fetcher.get_fundamentals(symbol, market)
                            except Exception:
                                pass
                    last_fundamental = now
                except Exception as e:
                    logger.warning("Fundamental refresh error: %s", e, exc_info=True)

            try:
                from datetime import datetime
                current_hour = datetime.now().hour
                current_date = datetime.now().strftime("%Y-%m-%d")
                if current_hour == cleanup_hour and current_date != last_cleanup_date:
                    try:
                        from core.database import get_db
                        db = get_db()
                        result = db.cleanup_stale_data(days=30)
                        logger.info(f"DB cleanup: {result}")
                        last_cleanup_date = current_date
                    except Exception as e:
                        logger.warning("DB cleanup error: %s", e, exc_info=True)
            except Exception as e:
                logger.warning("Cleanup check error: %s", e, exc_info=True)

            await asyncio.sleep(1)
        except Exception as e:
            logger.error(f"Scheduler loop error: {e}")
            await asyncio.sleep(10)


app = FastAPI(title="QuantCore", version="3.0.0", lifespan=lifespan)


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    return JSONResponse(status_code=400, content={"success": False, "error": str(exc)})


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {type(exc).__name__}: {exc}\n{traceback.format_exc()}")
    return JSONResponse(
        status_code=500,
        content={"success": False, "error": "服务器内部错误，请稍后重试", "error_type": type(exc).__name__},
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    elapsed = (time.time() - start) * 1000
    try:
        app.state._request_count = getattr(app.state, "_request_count", 0) + 1
        app.state._total_response_time = getattr(app.state, "_total_response_time", 0.0) + elapsed
    except Exception:
        pass
    return response

app.include_router(router, prefix="/api")

from api.backtest_routes import backtest_router
app.include_router(backtest_router, prefix="/api")


@app.get("/")
def index():
    index_file = BASE_DIR / "static" / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return {"name": "QuantCore", "version": "3.0.0", "status": "running", "docs": "/docs"}


@app.get("/health")
async def health_check(request: Request):
    checks = {}
    try:
        db = request.app.state.db
        db.fetchone("SELECT 1")
        checks["database"] = {"status": "ok"}
    except Exception as e:
        checks["database"] = {"status": "error", "message": str(e)}

    try:
        from core.data_fetcher import get_aiohttp_session
        session = await get_aiohttp_session()
        checks["network"] = {"status": "ok" if session and not session.closed else "error"}
    except Exception as e:
        checks["network"] = {"status": "error", "message": str(e)}

    try:
        import psutil
        process = psutil.Process()
        mem = process.memory_info()
        checks["memory"] = {
            "rss_mb": round(mem.rss / 1024 ** 2, 1),
            "status": "ok" if mem.rss < 512 * 1024 * 1024 else "warning",
        }
    except Exception as e:
        checks["memory"] = {"status": "warning", "message": str(e)}

    try:
        from core.data_fetcher import _history_cache, _realtime_cache
        checks["cache"] = {
            "status": "ok",
            "realtime_entries": len(_realtime_cache),
            "history_entries": len(_history_cache),
        }
    except Exception as e:
        checks["cache"] = {"status": "warning", "message": str(e)}

    uptime = time.time() - getattr(request.app.state, "start_time", time.time())
    all_ok = all(v.get("status") == "ok" for v in checks.values())
    return {
        "status": "healthy" if all_ok else "degraded",
        "uptime_seconds": round(uptime),
        "checks": checks,
        "version": "3.0.0",
    }


assets_dir = BASE_DIR / "static" / "assets"
if assets_dir.exists():
    app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")


@app.middleware("http")
async def api_metrics_middleware(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    elapsed = time.time() - start
    path = request.url.path
    if path.startswith("/api"):
        try:
            from core.metrics import metrics
            metrics.increment("api_requests_total", tags={"path": path.split("/")[2] if len(path.split("/")) > 2 else "other"})
            metrics.timer("api_request_duration", elapsed, tags={"path": path.split("/")[2] if len(path.split("/")) > 2 else "other"})
        except Exception:
            pass
    return response


@app.middleware("http")
async def spa_fallback(request, call_next):
    response = await call_next(request)
    path = request.url.path
    if response.status_code == 404 and not path.startswith("/api") and not path.startswith("/docs"):
        if "text/html" in request.headers.get("accept", ""):
            index_file = BASE_DIR / "static" / "index.html"
            if index_file.exists():
                return FileResponse(str(index_file))
    return response


def _build_frontend():
    frontend_dir = BASE_DIR / "frontend"
    if not frontend_dir.exists():
        return False
    static_dir = BASE_DIR / "static"
    if (static_dir / "index.html").exists():
        return True

    import shutil
    npm_path = shutil.which("npm")
    if not npm_path:
        logger.warning("未找到 npm，请先安装 Node.js: https://nodejs.org/")
        return False

    node_modules = frontend_dir / "node_modules"
    if not node_modules.exists():
        logger.info("安装前端依赖...")
        try:
            result = subprocess.run(
                [npm_path, "install"],
                cwd=str(frontend_dir),
                capture_output=True, text=True, timeout=300,
            )
            if result.returncode != 0:
                logger.warning(f"npm install 失败: {result.stderr[:200]}")
                return False
            logger.info("前端依赖安装完成")
        except Exception as e:
            logger.warning(f"npm install 异常: {e}")
            return False

    logger.info("构建前端...")
    try:
        npx_path = shutil.which("npx") or "npx"
        result = subprocess.run(
            [npx_path, "vite", "build", "--outDir", str(static_dir)],
            cwd=str(frontend_dir),
            capture_output=True, text=True, timeout=120,
        )
        if result.returncode == 0:
            logger.info("前端构建完成")
            return True
        logger.warning(f"前端构建失败: {result.stderr[:200]}")
    except Exception as e:
        logger.warning(f"前端构建异常: {e}")
    return False


if __name__ == "__main__":
    _build_frontend()

    def open_browser():
        _preload_done.wait(timeout=30)
        webbrowser.open(f"http://localhost:{PORT}")

    threading.Thread(target=open_browser, daemon=True).start()

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=PORT,
        log_level="warning",
        workers=1,
        loop="uvloop" if _has_uvloop else "asyncio",
        http="httptools",
        limit_concurrency=200,
        limit_max_requests=10000,
        backlog=2048,
        timeout_keep_alive=30,
        access_log=False,
    )
