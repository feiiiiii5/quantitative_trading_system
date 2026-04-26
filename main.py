"""
QuantCore - 量化交易系统
简洁高效，一键启动
"""
import asyncio
import logging
import os
import subprocess
import time
import webbrowser
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from api.routes import router, push_realtime_data
from core.logger import setup_logger

setup_logger(logging.INFO)
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).parent
PORT = 8080


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("QuantCore 启动中...")

    from core.database import get_db
    from core.data_fetcher import SmartDataFetcher
    from core.strategies import CompositeStrategy
    from core.simulated_trading import SimulatedTrading

    app.state.db = get_db()
    app.state.fetcher = SmartDataFetcher()
    app.state.composite_strategy = CompositeStrategy()
    app.state.trading = SimulatedTrading()
    app.state.start_time = time.time()

    try:
        from core.stock_search import _STOCK_INDEX
        logger.info(f"股票搜索索引: {len(_STOCK_INDEX)} 条")
    except Exception:
        pass

    try:
        asyncio.create_task(_warm_cache(app.state.fetcher))
    except Exception:
        pass

    try:
        asyncio.create_task(push_realtime_data(app.state.fetcher))
    except Exception:
        pass

    os.makedirs(BASE_DIR / "data", exist_ok=True)
    os.makedirs(BASE_DIR / "static", exist_ok=True)

    logger.info(f"QuantCore 启动完成 -> http://localhost:{PORT}")
    yield
    logger.info("QuantCore 关闭")


async def _warm_cache(fetcher):
    await asyncio.sleep(2)
    try:
        await fetcher.get_market_overview()
        await fetcher.get_hot_stocks()
    except Exception:
        pass


app = FastAPI(title="QuantCore", version="3.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")


@app.get("/")
def index():
    index_file = BASE_DIR / "static" / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return {"name": "QuantCore", "version": "3.0.0", "status": "running", "docs": "/docs"}


assets_dir = BASE_DIR / "static" / "assets"
if assets_dir.exists():
    app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")


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
    logger.info("构建前端...")
    try:
        result = subprocess.run(
            ["npx", "vite", "build", "--outDir", str(static_dir)],
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
        time.sleep(2)
        webbrowser.open(f"http://localhost:{PORT}")

    import threading
    threading.Thread(target=open_browser, daemon=True).start()

    uvicorn.run(app, host="0.0.0.0", port=PORT, log_level="warning")
