# SceneSteward Runbook 15: Redis Operations & Failover

**Document ID:** `RB-15-REDIS-OPERATIONS`  
**Target Environment:** Production  
**Audience:** SREs, Backend Engineers  

---

## 1. Redis Topology & Security
- **Version**: Redis 7 (Alpine).
- **Network Boundary**: Internal network `scenesteward-prod-net`; zero host ports exposed.
- **Authentication**: Strict mandatory password (`--requirepass ${REDIS_PASSWORD}`).
- **Persistence**: Append-Only File (AOF) enabled via `--appendonly yes`.
- **Purpose**: Distributed rate limiting counters (`rl:<key>:<window>`) and cache.

---

## 2. Health & Monitoring
Check Redis responsiveness:
```bash
docker exec -it scenesteward-prod-redis redis-cli -a "$REDIS_PASSWORD" ping
# Expected output: PONG
```

Check memory usage:
```bash
docker exec -it scenesteward-prod-redis redis-cli -a "$REDIS_PASSWORD" info memory
```

---

## 3. Graceful Failover & In-Memory Fallback
SceneSteward's rate limiter (`backend/app/core/rate_limiter.py`) is designed with high resilience:
- If Redis becomes unreachable, `RateLimiter` catches `REDIS_EXCEPTIONS` and switches seamlessly to an in-memory thread-safe local token bucket.
- User traffic is NOT interrupted during transient Redis restarts or network partitions.
- Readiness probe `/health/ready` reports:
  `checks.redis = {"status": "error", "fallback": "in_memory"}`
  and overall status transitions to `degraded` while keeping the service alive.
