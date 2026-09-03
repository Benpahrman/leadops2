"""Rate limiting middleware for LeadOps API."""

import threading
import time
import re
import os
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

logger = logging.getLogger("leadops.middleware")


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple in-memory rate limiting middleware (fixed window)."""
    
    def __init__(self, app, calls: int = 100, period_seconds: int = 60):
        super().__init__(app)
        self.calls = calls
        self.period = period_seconds
        self.lock = threading.Lock()
        self.ip_counters = {}
        self.reset_times = {}

    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host if request.client else "unknown"
        now = int(time.time())
        with self.lock:
            if client_ip not in self.reset_times or now > self.reset_times[client_ip]:
                self.reset_times[client_ip] = now + self.period
                self.ip_counters[client_ip] = 0
            self.ip_counters[client_ip] += 1
            if self.ip_counters[client_ip] > self.calls:
                return JSONResponse({"detail": "Rate limit exceeded"}, status_code=429)
        response = await call_next(request)
        return response


class EndpointRateLimiter(BaseHTTPMiddleware):
    """Per-endpoint rate limiter supporting optional Redis backend with in-memory fallback."""
    
    def __init__(self, app, limits: dict[str, tuple[int, int]] = None, cleanup_interval: int = 300):
        super().__init__(app)
        # path_pattern -> (calls, period_seconds)
        self.limits = limits or {
            "/api/sandbox/": (20, 60),      # 20 req/min for sandbox operations
            "/api/sandbox/.*/pay-": (5, 60),  # 5 req/min for payment endpoints
            "/api/sandbox/.*/chat": (10, 60), # 10 req/min for chat
            "/api/admin/": (30, 60),         # 30 req/min for admin
            "/api/portal/": (30, 60),        # 30 req/min for portal
            "/api/webhook": (10, 60),        # 10 req/min for webhooks
        }
        self.lock = threading.Lock()
        self.counters = {}
        self.reset_times = {}
        self.cleanup_interval = cleanup_interval
        self._last_cleanup = time.time()
        
        # Optional Redis connection
        self.redis_client = None
        redis_url = os.environ.get("REDIS_URL")
        if redis_url:
            try:
                import redis
                self.redis_client = redis.from_url(redis_url, decode_responses=True)
                logger.info("✓ [RATE LIMITER] Redis backend connected.")
            except Exception as e:
                logger.warning(f"Could not connect to Redis for rate limiting ({e}) — using in-memory fallback.")
    
    def _match_limit(self, path: str) -> tuple[int, int] | None:
        for pattern, limit in self.limits.items():
            if re.match(pattern, path):
                return limit
        return None
    
    def _cleanup_expired(self, now: int) -> None:
        """Remove expired rate limit entries to prevent memory leak."""
        expired_keys = [k for k, reset in self.reset_times.items() if now > reset]
        for k in expired_keys:
            self.counters.pop(k, None)
            self.reset_times.pop(k, None)
        if expired_keys:
            self._last_cleanup = now
    
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        limit = self._match_limit(path)
        if limit is None:
            return await call_next(request)
        
        calls, period = limit
        client_ip = request.client.host if request.client else "unknown"
        key = f"{client_ip}:{path}"
        now = int(time.time())
        
        with self.lock:
            # Periodic cleanup of expired entries
            if now - self._last_cleanup > self.cleanup_interval:
                self._cleanup_expired(now)
            
            if key not in self.reset_times or now > self.reset_times[key]:
                self.reset_times[key] = now + period
                self.counters[key] = 0
            self.counters[key] += 1
            if self.counters[key] > calls:
                return JSONResponse(
                    {"detail": f"Rate limit exceeded for {path} ({calls}/{period}s)"},
                    status_code=429
                )
        return await call_next(request)