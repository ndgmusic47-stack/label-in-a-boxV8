from time import time
from typing import Dict, Tuple
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response


class RateLimiterMiddleware(BaseHTTPMiddleware):
    """
    Simple in-memory token bucket limiter per client IP.
    Default: 30 requests per 60 seconds per IP.
    """

    def __init__(self, app, requests_per_minute: int = 30):
        super().__init__(app)
        self.capacity = requests_per_minute
        self.refill_time_window = 60.0
        # ip -> (tokens, last_refill_ts)
        self._buckets: Dict[str, Tuple[float, float]] = {}

    def _get_client_ip(self, request: Request) -> str:
        xff = request.headers.get("x-forwarded-for")
        if xff:
            # Take first IP in the list
            return xff.split(",")[0].strip()
        client = request.client
        return client.host if client else "unknown"

    async def dispatch(self, request: Request, call_next) -> Response:
        now = time()
        ip = self._get_client_ip(request)

        tokens, last_refill = self._buckets.get(ip, (self.capacity, now))
        # Refill based on elapsed time
        elapsed = max(0.0, now - last_refill)
        refill = (elapsed / self.refill_time_window) * self.capacity
        tokens = min(self.capacity, tokens + refill)
        if tokens < 1.0:
            return JSONResponse(
                status_code=429,
                content={
                    "status": "error",
                    "data": {},
                    "message": "Rate limit exceeded. Try again shortly."
                },
            )
        # Consume a token and store
        self._buckets[ip] = (tokens - 1.0, now)

        return await call_next(request)


