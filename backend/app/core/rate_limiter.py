"""Distributed rate limiting with Redis support and resilient in-memory fallback.

Architecture:
- Shared counters across workers via Redis when REDIS_URL is configured.
- Thread-safe local fixed-window fallback when Redis is absent or temporarily unreachable.
- Safe client IP extraction respecting trusted reverse proxies (prevents X-Forwarded-For spoofing).
- Tiered, endpoint-specific rate limits (auth, document uploads, reviews, general API).
- Standard RFC headers: Retry-After, X-RateLimit-Limit, X-RateLimit-Remaining, X-RateLimit-Reset.
"""
from __future__ import annotations

import ipaddress
import logging
import threading
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

try:
    import redis
    import redis.exceptions
    REDIS_EXCEPTIONS: tuple[type[BaseException], ...] = (redis.exceptions.RedisError, OSError, ConnectionError, TimeoutError)
except ImportError:  # pragma: no cover
    redis = None  # type: ignore[assignment]
    REDIS_EXCEPTIONS = (OSError, ConnectionError, TimeoutError)

if TYPE_CHECKING:
    from fastapi import Request

logger = logging.getLogger("scenesteward.rate_limiter")

# Route-specific limit definitions: (path_prefix, limit_per_minute)
ROUTE_TIERS: tuple[tuple[str, int], ...] = (
    ("/api/v1/auth", 20),           # Auth endpoints: 20 req/min
    ("/api/v1/documents", 30),      # Document upload endpoints: 30 req/min
    ("/api/v1/projects", 60),       # Project mutation endpoints: 60 req/min
    ("/api/v1/reviews", 40),        # Human decision reviews: 40 req/min
)

EXCLUDED_PATHS: set[str] = {
    "/health",
    "/health/ready",
    "/docs",
    "/openapi.json",
    "/favicon.ico",
}


@dataclass(frozen=True)
class RateLimitResult:
    is_limited: bool
    limit: int
    remaining: int
    reset_seconds: int


def is_ip_trusted(ip_str: str, trusted_networks: list[str]) -> bool:
    """Check if an IP address belongs to trusted proxies or loopback/private ranges."""
    try:
        ip = ipaddress.ip_address(ip_str)
        if ip.is_loopback:
            return True
        for net in trusted_networks:
            try:
                if "/" in net:
                    if ip in ipaddress.ip_network(net, strict=False):
                        return True
                elif ip == ipaddress.ip_address(net):
                    return True
            except ValueError:
                continue
    except ValueError:
        return False
    return False


def get_client_ip(request: Request, trusted_proxies: list[str]) -> str:
    """Extract client IP safely.

    Traverses X-Forwarded-For from right to left only if the peer is a trusted proxy.
    Untrusted peers cannot spoof client identity via X-Forwarded-For.
    """
    direct_peer = request.client.host if request.client else "127.0.0.1"

    if not is_ip_trusted(direct_peer, trusted_proxies):
        return direct_peer

    # Peer is trusted proxy, inspect X-Forwarded-For
    forwarded = request.headers.get("X-Forwarded-For")
    if not forwarded:
        return direct_peer

    ips = [ip.strip() for ip in forwarded.split(",") if ip.strip()]
    if not ips:
        return direct_peer

    # Walk backwards from rightmost (nearest proxy) to find first untrusted IP
    for candidate in reversed(ips):
        if not is_ip_trusted(candidate, trusted_proxies):
            return candidate

    # All forwarded IPs are in trusted ranges; fallback to leftmost
    return ips[0]


class RateLimiter:
    """Distributed rate limiter with fallback to memory."""

    def __init__(self, redis_url: str | None = None) -> None:
        self.redis_client: Any = None
        self._lock = threading.Lock()
        self._memory_buckets: dict[tuple[str, int], int] = {}
        self._redis_available = False

        if redis_url and redis is not None:
            try:
                self.redis_client = redis.from_url(
                    redis_url,
                    socket_connect_timeout=1.0,
                    socket_timeout=1.0,
                    decode_responses=True,
                )
                self.redis_client.ping()
                self._redis_available = True
                logger.info("Connected to distributed Redis rate limiter: %s", redis_url)
            except REDIS_EXCEPTIONS as e:
                logger.warning("Redis rate limiter unavailable (%s); using in-memory limiter", e)
                self._redis_available = False

    def get_tier_limit(self, path: str, default_limit: int) -> int:
        """Find matching route tier limit or default."""
        for prefix, limit in ROUTE_TIERS:
            if path.startswith(prefix):
                return limit
        return default_limit

    def check(
        self,
        key: str,
        limit_per_minute: int,
        window_seconds: int = 60,
    ) -> RateLimitResult:
        """Check and increment counter for the given client key."""
        now = time.time()
        window_idx = int(now // window_seconds)
        reset_seconds = max(1, int(((window_idx + 1) * window_seconds) - now))

        # 1. Attempt Redis if available
        if self._redis_available and self.redis_client:
            redis_key = f"rl:{key}:{window_idx}"
            try:
                pipe = self.redis_client.pipeline()
                pipe.incr(redis_key)
                pipe.expire(redis_key, window_seconds + 5)
                results = pipe.execute()
                count = int(results[0])
                remaining = max(0, limit_per_minute - count)
                return RateLimitResult(
                    is_limited=(count > limit_per_minute),
                    limit=limit_per_minute,
                    remaining=remaining,
                    reset_seconds=reset_seconds,
                )
            except REDIS_EXCEPTIONS as e:
                logger.warning("Redis operation failed in rate limiter (%s); falling back to memory", e)
                # Fall through to memory bucket

        # 2. Resilient In-Memory Fallback
        bucket_key = (key, window_idx)
        with self._lock:
            count = self._memory_buckets.get(bucket_key, 0) + 1
            self._memory_buckets[bucket_key] = count

            # Opportunistic eviction of expired windows
            if len(self._memory_buckets) > 5000:
                current_window = window_idx
                expired = [k for k in self._memory_buckets if k[1] < current_window]
                for k in expired:
                    self._memory_buckets.pop(k, None)

            remaining = max(0, limit_per_minute - count)
            return RateLimitResult(
                is_limited=(count > limit_per_minute),
                limit=limit_per_minute,
                remaining=remaining,
                reset_seconds=reset_seconds,
            )


_global_limiter: RateLimiter | None = None
_limiter_lock = threading.Lock()


def get_rate_limiter(redis_url: str | None = None) -> RateLimiter:
    """Singleton getter for rate limiter."""
    global _global_limiter
    if _global_limiter is None:
        with _limiter_lock:
            if _global_limiter is None:
                _global_limiter = RateLimiter(redis_url)
    return _global_limiter
