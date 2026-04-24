import time
from collections import defaultdict, deque

from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware


class RequestMetricsAndLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, request_limit_per_second: int = 10):
        super().__init__(app)
        self.request_limit_per_second = request_limit_per_second
        self._requests: dict[str, deque] = defaultdict(deque)

    async def dispatch(self, request, call_next):
        if request.url.path.startswith("/static"):
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        now = time.time()
        bucket = self._requests[client_ip]
        while bucket and now - bucket[0] > 1:
            bucket.popleft()
        if len(bucket) >= self.request_limit_per_second:
            return JSONResponse(
                status_code=429,
                content={"success": False, "error": "请求过于频繁，请稍后再试"},
            )
        bucket.append(now)

        started = time.perf_counter()
        status_code = 500
        try:
            response = await call_next(request)
            status_code = getattr(response, "status_code", 200)
            return response
        finally:
            latency_ms = (time.perf_counter() - started) * 1000
            app_state = request.app.state
            if hasattr(app_state, "perf_dashboard"):
                try:
                    app_state.perf_dashboard.record_api_latency(request.url.path, latency_ms, status_code)
                except Exception:
                    pass
            if hasattr(app_state, "db"):
                try:
                    app_state.db.record_api_metric(request.url.path, latency_ms, status_code)
                except Exception:
                    pass
