# SceneSteward Runbook 11: Monitoring & Alerting

**Document ID:** `RB-11-MONITORING-ALERTING`  
**Target Environment:** Production  
**Audience:** SREs, NOC Engineers, On-Call Engineers  
**Last Updated:** 2026-11-06  

---

## 1. Observability Endpoints & Probes

SceneSteward provides multi-layered observability endpoints:
- `/health` & `/health/live`: HTTP process liveness probe.
- `/health/ready`: Comprehensive multi-subsystem readiness probe (PostgreSQL connectivity + migration version check, Redis fail-closed rate-limiting, ClamAV antivirus daemon, and document storage writeability).
- `scripts/switch_retry.py --check-health`: Dedicated background worker probe validating process loop heartbeat age (< 30s) and database connectivity.
- `/api/v1/metrics`: Platform request counts, error rates, p95/p99 latency metrics, outbox backlog size.

---

## 2. Core Prometheus Alerts & Action Thresholds

| Alert Name | Metric Expression | Condition | Severity | Playbook Action |
| :--- | :--- | :--- | :--- | :--- |
| `APIUnhealthy` | `probe_success{job="scenesteward-ready"} == 0` | For 1 min | Critical | Page on-call; check DB/Redis/ClamAV |
| `WorkerHeartbeatStale` | `scenesteward_worker_heartbeat_age_seconds > 30` | For 2 min | Critical | Check worker container logs and DB locks |
| `UnmigratedDatabaseStartup` | `scenesteward_db_migration_status{status="unmigrated"} == 1` | Immediate | Critical | Run one-shot migration container |
| `HighErrorRate` | `rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m]) > 0.01` | For 3 min | Critical | Inspect logs for unhandled exceptions |
| `ElevatedLatency` | `histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 1.5` | For 5 min | Warning | Check DB connection pool exhaustion |
| `SwitchOutboxBacklog` | `scenesteward_switch_outbox_pending_count > 100` | For 10 min | Warning | Verify worker container and Switch Core API |
| `ClamAVScannerDegraded`| `scenesteward_clamav_connected == 0` | For 2 min | Warning / Crit | Check ClamAV container memory/status |

---

## 3. Synthetic Probe Monitoring

Configure an external synthetics runner (e.g. UptimeRobot, Datadog Synthetic, AWS Route 53 Health Check) to query:
- **URL**: `https://app.scenesteward.com/health/ready`
- **Interval**: 30 seconds
- **Timeout**: 5 seconds
- **Expected HTTP Code**: `200`
- **Failure Threshold**: 2 consecutive failures triggers immediate SEV-1 notification.
