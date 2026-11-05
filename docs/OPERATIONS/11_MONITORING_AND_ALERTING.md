# SceneSteward Runbook 11: Monitoring & Alerting

**Document ID:** `RB-11-MONITORING-ALERTING`  
**Target Environment:** Production  
**Audience:** SREs, NOC Engineers  

---

## 1. Metrics Infrastructure
SceneSteward provides native observability via:
- `/health` & `/health/live`: HTTP process liveness probe.
- `/health/ready`: Multi-subsystem readiness probe (DB, Redis, ClamAV, Storage).
- `/api/v1/metrics`: Platform request counts, error rates, p95/p99 latency metrics, outbox backlog size.

---

## 2. Core Prometheus Alerts & Thresholds

| Alert Name | Metric Expression | Condition | Severity | Action |
| :--- | :--- | :--- | :--- | :--- |
| `APIUnhealthy` | `probe_success{job="scenesteward-ready"} == 0` | For 1 minute | Critical | Page on-call; check DB/ClamAV |
| `HighErrorRate` | `rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m]) > 0.01` | For 3 minutes | Critical | Inspect logs for unhandled exceptions |
| `ElevatedLatency` | `histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 1.5` | For 5 minutes | Warning | Check DB connection pool exhaustion |
| `SwitchOutboxBacklog` | `scenesteward_switch_outbox_pending_count > 100` | For 10 minutes | Warning | Verify worker container and Switch Core API |
| `ClamAVScannerDegraded`| `scenesteward_clamav_connected == 0` | For 2 minutes | Warning / Crit | Check ClamAV container memory/status |

---

## 3. Synthetic Probe Monitoring
Configure an external synthetics runner (e.g. UptimeRobot, Datadog Synthetic, AWS Route 53 Health Check) to query:
- URL: `https://app.scenesteward.com/health/ready`
- Interval: 30 seconds
- Timeout: 5 seconds
- Expected HTTP Code: `200`
