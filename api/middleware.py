# MODIFIED: Unified request validation middleware | VERSION: 2026-05-11
from __future__ import annotations

import logging
import time


logger = logging.getLogger(__name__)

SLOW_THRESHOLD_MS = 500


class RequestValidationMiddleware:
    def __init__(self, app):
        self._app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return

        path = scope.get("path", "")
        if path in ("/api/health", "/favicon.ico") or path.startswith("/api/ws/"):
            await self._app(scope, receive, send)
            return

        start = time.monotonic()

        response_started = False
        response_status = 200

        async def _send(message):
            nonlocal response_started, response_status
            if message["type"] == "http.response.start":
                response_started = True
                response_status = message.get("status", 200)
            await send(message)

        try:
            await self._app(scope, receive, _send)
        except Exception as e:
            logger.error(
                "Unhandled: %s %s -> %s",
                scope.get("method", ""),
                path,
                e,
            )
            if not response_started:
                import orjson
                body = orjson.dumps({"success": False, "error": str(e), "code": 500})
                await send({
                    "type": "http.response.start",
                    "status": 500,
                    "headers": [
                        [b"content-type", b"application/json"],
                    ],
                })
                await send({
                    "type": "http.response.body",
                    "body": body,
                })
            return

        elapsed_ms = (time.monotonic() - start) * 1000
        if elapsed_ms > SLOW_THRESHOLD_MS:
            logger.warning(
                "SLOW %s %s %.0fms",
                scope.get("method", ""),
                path,
                elapsed_ms,
            )
