from __future__ import annotations

import logging
import time

from fastapi import APIRouter, Request

from api.utils import json_response as _json_response
from api.utils import safe_error

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/user/memory")
async def get_user_memory(request: Request):
    try:
        from core.memory import get_user_memory
        memory = get_user_memory()
        summary = await memory.get_memory_summary()
        return _json_response(True, data=summary)
    except Exception as e:
        logger.error("Get user memory error: %s", e)
        return _json_response(False, error=safe_error(e))


@router.post("/user/memory/clear")
async def clear_user_memory(request: Request):
    try:
        from core.memory import get_user_memory
        memory = get_user_memory()
        await memory.clear_memory()
        return _json_response(True, data={"message": "记忆已清除"})
    except Exception as e:
        logger.error("Clear user memory error: %s", e)
        return _json_response(False, error=safe_error(e))


@router.get("/user/recommendations")
async def get_user_recommendations(request: Request):
    try:
        from core.memory import get_user_memory
        memory = get_user_memory()
        symbols = await memory.get_recommended_symbols()
        return _json_response(True, data={
            "symbols": symbols,
            "count": len(symbols),
            "timestamp": time.time(),
        })
    except Exception as e:
        logger.error("Get recommendations error: %s", e)
        return _json_response(False, error=safe_error(e))
