# SceneSteward Runbook 12: Log Management & Audit

**Document ID:** `RB-12-LOG-MANAGEMENT`  
**Target Environment:** Staging, Production  
**Audience:** Security Engineers, Compliance Officers  

---

## 1. Structured Logging Standards
SceneSteward emits structured JSON logs via `backend/app/core/logging.py`. Every log line includes:
- `ts`: ISO 8601 UTC timestamp.
- `level`: `INFO`, `WARNING`, `ERROR`, `CRITICAL`.
- `logger`: Subsystem identifier (e.g. `scenesteward.app`, `scenesteward.database`).
- `request_id`: UUID tracking request lifecycle.
- `correlation_id`: Distributed correlation token propagated across headers.

---

## 2. Strict Secret Exclusion
Logs are guaranteed never to contain:
- Authorization tokens, bearer tokens, or Supabase JWTs.
- `DATABASE_IDENTITY_SECRET`, encryption keys, or HMAC signatures.
- Database passwords or connection DSNs (Redis URLs are sanitized via `re.sub`).
- Raw participant PII (decrypted phone numbers or physical addresses).

---

## 3. Immutable Audit Trails
Documentary consent actions produce immutable records in the `events` table:
- Actions: `participant.registered`, `consent.confirmed`, `review.human_decision`, `communication.approved`.
- Each event contains an immutable cryptographic hash, acting as an tamper-evident ledger.
- Audit queries utilize keyset pagination for high performance and forensic integrity.

---

## 4. Log Aggregation Configuration
Ship container logs to centralized logging (Elasticsearch, Loki, CloudWatch, Datadog):
```yaml
logging:
  driver: "json-file"
  options:
    max-size: "50m"
    max-file: "10"
```
