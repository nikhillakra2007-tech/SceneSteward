"""Tests for distributed rate limiter, IP extraction, and fallback resilience."""
from __future__ import annotations

from unittest.mock import MagicMock

from app.core.rate_limiter import RateLimiter, get_client_ip, is_ip_trusted


def make_mock_request(client_host: str, forwarded_for: str | None = None, path: str = "/api/v1/projects"):
    req = MagicMock()
    req.client.host = client_host
    req.headers = {}
    if forwarded_for:
        req.headers["X-Forwarded-For"] = forwarded_for
    req.url.path = path
    return req


def test_is_ip_trusted():
    trusted = ["127.0.0.1", "10.0.0.0/8", "192.168.1.5"]
    assert is_ip_trusted("127.0.0.1", trusted) is True
    assert is_ip_trusted("10.1.2.3", trusted) is True
    assert is_ip_trusted("192.168.1.5", trusted) is True
    assert is_ip_trusted("8.8.8.8", trusted) is False
    assert is_ip_trusted("192.168.1.6", trusted) is False
    assert is_ip_trusted("invalid_ip", trusted) is False


def test_client_ip_spoof_prevention_from_untrusted_peer():
    trusted = ["10.0.0.1"]
    # Untrusted attacker connects directly from 203.0.113.5 and attempts to spoof X-Forwarded-For
    req = make_mock_request(client_host="203.0.113.5", forwarded_for="1.1.1.1, 10.0.0.1")
    resolved = get_client_ip(req, trusted)
    # The untrusted peer cannot spoof IP: the direct peer must be returned
    assert resolved == "203.0.113.5"


def test_client_ip_resolution_through_trusted_proxy():
    trusted = ["10.0.0.1", "127.0.0.1"]
    # Reverse proxy (10.0.0.1) forwards request from client 198.51.100.42
    req = make_mock_request(client_host="10.0.0.1", forwarded_for="198.51.100.42, 10.0.0.1")
    resolved = get_client_ip(req, trusted)
    assert resolved == "198.51.100.42"


def test_rate_limiter_allows_under_limit():
    limiter = RateLimiter(redis_url=None)
    key = "test_client_1"
    for i in range(5):
        res = limiter.check(key, limit_per_minute=10)
        assert res.is_limited is False
        assert res.remaining == 10 - (i + 1)
        assert res.limit == 10
        assert res.reset_seconds > 0


def test_rate_limiter_blocks_over_limit():
    limiter = RateLimiter(redis_url=None)
    key = "test_client_blocked"
    # Exhaust 5 tokens
    for _ in range(5):
        limiter.check(key, limit_per_minute=5)

    # 6th request is blocked
    res = limiter.check(key, limit_per_minute=5)
    assert res.is_limited is True
    assert res.remaining == 0
    assert res.reset_seconds > 0


def test_rate_limiter_route_tiers():
    limiter = RateLimiter(redis_url=None)
    assert limiter.get_tier_limit("/api/v1/auth/token", default_limit=120) == 20
    assert limiter.get_tier_limit("/api/v1/documents/upload", default_limit=120) == 30
    assert limiter.get_tier_limit("/api/v1/reviews/123", default_limit=120) == 40
    assert limiter.get_tier_limit("/api/v1/other", default_limit=120) == 120


def test_rate_limiter_redis_unreachable_fallback():
    # Invalid redis host should cleanly fall back to memory without throwing
    limiter = RateLimiter(redis_url="redis://nonexistent.host.local:6379/0")
    assert limiter._redis_available is False
    res = limiter.check("fallback_test", limit_per_minute=10)
    assert res.is_limited is False
    assert res.remaining == 9
