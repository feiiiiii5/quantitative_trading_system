import asyncio
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from core.market_detector import MarketDetector

logger = logging.getLogger(__name__)
ws_router = APIRouter()


@ws_router.websocket("/ws/{symbol}")
async def websocket_endpoint(websocket: WebSocket, symbol: str):
    await websocket.accept()
    app = websocket.app
    market_info = MarketDetector.get_config(symbol)
    fail_count = 0
    try:
        while True:
            try:
                realtime = await app.state.fetcher.get_realtime(symbol)
                if realtime and realtime.get("price"):
                    fail_count = 0
                    await websocket.send_json({
                        "type": "realtime",
                        "symbol": symbol,
                        "market": market_info,
                        "data": realtime,
                    })
                else:
                    fail_count += 1
                    if fail_count <= 3:
                        await websocket.send_json({
                            "type": "realtime",
                            "symbol": symbol,
                            "data": {},
                        })
            except WebSocketDisconnect:
                break
            except Exception as e:
                fail_count += 1
                if fail_count <= 2:
                    logger.debug(f"WS push error for {symbol}: {e}")
                try:
                    await websocket.send_json({"type": "heartbeat"})
                except Exception:
                    break
            delay = 1 if fail_count < 3 else 10
            await asyncio.sleep(delay)
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.debug(f"WS closed for {symbol}: {e}")
