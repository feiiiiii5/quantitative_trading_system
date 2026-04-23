import asyncio
import logging
import os
import signal
import threading
import time
import webbrowser
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

app = FastAPI(title="QuantVision", docs_url=None, redoc_url=None)

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


@app.on_event("startup")
async def on_startup():
    logger = logging.getLogger(__name__)
    logger.info("QuantVision starting up...")

    try:
        from core.stock_search import _build_index
        _build_index()
        logger.info("Stock search index built")
    except Exception as e:
        logger.warning(f"Failed to build search index: {e}")

    try:
        from api.routes import fetcher
        asyncio.create_task(_warm_cache(fetcher))
    except Exception as e:
        logger.warning(f"Cache warm-up failed: {e}")

    try:
        os.makedirs(os.path.join(BASE_DIR, "data"), exist_ok=True)
    except Exception:
        pass


async def _warm_cache(fetcher):
    await asyncio.sleep(2)
    try:
        await fetcher.get_hot_stocks()
        logging.getLogger(__name__).info("Hot stocks cache warmed")
    except Exception as e:
        logging.getLogger(__name__).debug(f"Hot stocks warm-up failed: {e}")


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
