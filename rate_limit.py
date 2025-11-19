import os
import json
from time import time
from typing import Dict, Tuple, Optional
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
import logging

logger = logging.getLogger(__name__)

# Try to import and initialize Redis
_redis_client = None
_redis_available = False

try:
    import redis
    redis_url = os.getenv("REDIS_URL")
    if redis_url:
        try:
            # Parse Redis URL (supports redis:// and redis://:password@host:port)
            _redis_client = redis.from_url(redis_url, decode_responses=True)
            # Test connection
            _redis_client.ping()
            _redis_available = True
            logger.info("✅ Redis connected successfully for rate limiting")
        except Exception as e:
            logger.warning(f"⚠️ Redis connection failed: {e}. Falling back to in-memory rate limiting.")
            _redis_client = None
            _redis_available = False
    else:
        logger.info("ℹ️ REDIS_URL not set. Using in-memory rate limiting.")
except ImportError:
    logger.warning("⚠️ redis package not installed. Using in-memory rate limiting.")


class RateLimiterMiddleware(BaseHTTPMiddleware):
    """
    Distributed rate limiter using Redis (with fallback to in-memory).
    Uses Token Bucket Algorithm.
    Default: 30 requests per 60 seconds per IP.
    """

    def __init__(self, app, requests_per_minute: int = 30):
        super().__init__(app)
        self.capacity = requests_per_minute
        self.refill_time_window = 60.0
        # Fallback: in-memory storage (ip -> (tokens, last_refill_ts))
        self._buckets: Dict[str, Tuple[float, float]] = {}
        self._use_redis = _redis_available and _redis_client is not None

    def _get_client_ip(self, request: Request) -> str:
        xff = request.headers.get("x-forwarded-for")
        if xff:
            # Take first IP in the list
            return xff.split(",")[0].strip()
        client = request.client
        return client.host if client else "unknown"

    def _get_redis_key(self, ip: str) -> str:
        """Generate Redis key for rate limiting"""
        return f"rate_limit:{ip}"

    async def _check_rate_limit_redis(self, ip: str) -> bool:
        """
        Check rate limit using Redis.
        Returns True if request is allowed, False if rate limited.
        Uses Token Bucket Algorithm stored in Redis.
        """
        if not self._use_redis or not _redis_client:
            return True  # Fall through to in-memory check
        
        try:
            key = self._get_redis_key(ip)
            now = time()
            
            # Get current bucket state from Redis
            bucket_data = _redis_client.get(key)
            
            if bucket_data:
                # Parse stored data: {"tokens": float, "last_refill": float}
                data = json.loads(bucket_data)
                tokens = float(data.get("tokens", 0))
                last_refill = float(data.get("last_refill", now))
            else:
                # New bucket, start with full capacity
                tokens = float(self.capacity)
                last_refill = now
            
            # Refill based on elapsed time
            elapsed = max(0.0, now - last_refill)
            refill = (elapsed / self.refill_time_window) * self.capacity
            tokens = min(self.capacity, tokens + refill)
            
            # Check if we have enough tokens
            if tokens < 1.0:
                return False
            
            # Consume a token
            tokens -= 1.0
            
            # Store updated state in Redis with TTL (expire after refill window)
            bucket_data = json.dumps({"tokens": tokens, "last_refill": now})
            _redis_client.setex(key, int(self.refill_time_window) + 10, bucket_data)
            
            return True
            
        except Exception as e:
            logger.warning(f"Redis rate limit check failed: {e}. Falling back to in-memory.")
            # Fall through to in-memory check
            return None  # Signal to use fallback

    async def _check_rate_limit_memory(self, ip: str) -> bool:
        """
        Check rate limit using in-memory storage (fallback).
        Returns True if request is allowed, False if rate limited.
        """
        now = time()
        tokens, last_refill = self._buckets.get(ip, (self.capacity, now))
        
        # Refill based on elapsed time
        elapsed = max(0.0, now - last_refill)
        refill = (elapsed / self.refill_time_window) * self.capacity
        tokens = min(self.capacity, tokens + refill)
        
        if tokens < 1.0:
            return False
        
        # Consume a token and store
        self._buckets[ip] = (tokens - 1.0, now)
        return True

    async def dispatch(self, request: Request, call_next) -> Response:
        ip = self._get_client_ip(request)
        
        # Try Redis first if available
        if self._use_redis:
            allowed = await self._check_rate_limit_redis(ip)
            if allowed is None:
                # Redis failed, use in-memory fallback
                allowed = await self._check_rate_limit_memory(ip)
        else:
            # Use in-memory fallback
            allowed = await self._check_rate_limit_memory(ip)
        
        if not allowed:
            return JSONResponse(
                status_code=429,
                content={
                    "status": "error",
                    "data": {},
                    "message": "Rate limit exceeded. Try again shortly."
                },
            )
        
        return await call_next(request)
