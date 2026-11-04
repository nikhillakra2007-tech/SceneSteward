"""Lightweight in-process HTTP and database metrics collector."""
from __future__ import annotations

import threading
import time
from collections import defaultdict
from typing import Any

from app.core.database import get_engine

_lock = threading.Lock()
_start_time = time.time()
_request_counts: dict[tuple[str, str, int], int] = defaultdict(int)
_latency_sums: dict[str, float] = defaultdict(float)
_latency_counts: dict[str, int] = defaultdict(int)


def record_request(*, method: str, endpoint: str, status_code: int, duration_ms: float) -> None:
    # Normalize high-cardinality endpoint paths (e.g. replace UUIDs with {id})
    import re
    normalized = re.sub(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", "{id}", endpoint)

    with _lock:
        _request_counts[(method, normalized, status_code)] += 1
        _latency_sums[normalized] += duration_ms
        _latency_counts[normalized] += 1


def get_db_pool_stats() -> dict[str, int]:
    try:
        pool = get_engine().pool
        return {
            "size": pool.size(),
            "checked_in": pool.checkedin(),
            "checked_out": pool.checkedout(),
            "overflow": pool.overflow(),
        }
    except (AttributeError, RuntimeError, OSError):
        return {"size": 0, "checked_in": 0, "checked_out": 0, "overflow": 0}


def get_metrics_summary() -> dict[str, Any]:
    uptime = time.time() - _start_time
    with _lock:
        total_reqs = sum(_request_counts.values())
        status_breakdown: dict[str, int] = defaultdict(int)
        by_endpoint: list[dict[str, Any]] = []

        for (method, endpoint, status), count in _request_counts.items():
            status_breakdown[str(status)] += count
            by_endpoint.append({
                "method": method,
                "endpoint": endpoint,
                "status": status,
                "count": count,
            })

        avg_latencies = {
            ep: round(_latency_sums[ep] / max(1, _latency_counts[ep]), 2)
            for ep in _latency_counts
        }

    return {
        "uptime_seconds": round(uptime, 2),
        "total_requests": total_reqs,
        "requests_by_status": dict(status_breakdown),
        "endpoints": by_endpoint,
        "average_latency_ms": avg_latencies,
        "db_pool": get_db_pool_stats(),
    }


def get_prometheus_metrics() -> str:
    lines = [
        "# HELP scenesteward_http_requests_total Total number of HTTP requests.",
        "# TYPE scenesteward_http_requests_total counter",
    ]
    with _lock:
        for (method, endpoint, status), count in _request_counts.items():
            lines.append(
                f'scenesteward_http_requests_total{{method="{method}",endpoint="{endpoint}",status="{status}"}} {count}'
            )

        lines.extend([
            "# HELP scenesteward_http_request_duration_ms_total Sum of duration in ms.",
            "# TYPE scenesteward_http_request_duration_ms_total counter",
        ])
        for endpoint, duration_sum in _latency_sums.items():
            lines.append(f'scenesteward_http_request_duration_ms_total{{endpoint="{endpoint}"}} {duration_sum:.2f}')

    pool = get_db_pool_stats()
    lines.extend([
        "# HELP scenesteward_db_pool_connections Current connection pool stats.",
        "# TYPE scenesteward_db_pool_connections gauge",
        f'scenesteward_db_pool_connections{{state="checked_in"}} {pool["checked_in"]}',
        f'scenesteward_db_pool_connections{{state="checked_out"}} {pool["checked_out"]}',
        f'scenesteward_db_pool_connections{{state="overflow"}} {pool["overflow"]}',
        f'scenesteward_db_pool_connections{{state="size"}} {pool["size"]}',
    ])
    return "\n".join(lines) + "\n"
