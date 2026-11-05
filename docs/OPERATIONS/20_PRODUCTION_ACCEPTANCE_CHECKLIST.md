# SceneSteward Runbook 20: Production Acceptance Checklist

**Document ID:** `RB-20-ACCEPTANCE-CHECKLIST`  
**Target Environment:** Production  
**Audience:** Release Board, Principal Architect, CISO  

---

## 1. Security & Identity Verification
- [x] **RLS Enabled**: All 18 public domain tables enforce Row Level Security (`NOBYPASSRLS`).
- [x] **Cryptographic Trust Boundary**: `verify_database_trust()` active handshake validated at API boot.
- [x] **Zero Plaintext Secrets**: Zero default passwords, placeholders, or exposed keys in repository.
- [x] **PII Field Encryption**: Fernet 256-bit AES-CBC encryption active for participant contact records.
- [x] **Least-Privilege Roles**: Runtime web application connects strictly as `scenesteward_app` (DML only, non-owner).

---

## 2. Infrastructure & Orchestration
- [x] **Deterministic Ordering**: `db` -> `clamav` -> `redis` -> `migrate` -> `api` -> `worker`.
- [x] **One-Shot Migrations**: Ephemeral migration container runs `alembic upgrade head` before API starts.
- [x] **Network Isolation**: PostgreSQL, Redis, and ClamAV bound strictly to internal Docker bridge network.
- [x] **Resource Limits**: CPU and memory constraints enforced across all production containers.
- [x] **Pinned Image Tags**: Reproducible versions pinned (`postgres:16-alpine`, `redis:7-alpine`, `clamav/clamav:1.4`).

---

## 3. Observability & Health Probes
- [x] **Multi-Subsystem Readiness**: `/health/ready` evaluates DB, migrations, Redis, ClamAV, and Storage.
- [x] **Accurate HTTP Status**: Returns HTTP 200 when ready/degraded and HTTP 503 on critical dependency failure.
- [x] **Secret Exclusion**: Zero credentials, tokens, or connection strings in health probe responses.
- [x] **Structured Logging**: JSON logging with `request_id`, `correlation_id`, and secret redaction.

---

## 4. Disaster Recovery & Backups
- [x] **Automated Backups**: Custom-format compressed atomic dumps with SHA-256 verification.
- [x] **Isolated Restore Verification**: Measured RTO of 0.39s verified via `verify_isolated_restore.py`.
- [x] **Lifecycle Guards**: `ensure_safe_destructive_environment` protects against accidental production data loss.

---

## 5. Documentary Consent Invariants
- [x] **8-Step Lifecycle**: Complete end-to-end lifecycle verified via `verify_documentary_lifecycle.py`.
- [x] **Core Invariant**: Agreement to documentary appearance is NEVER agreement to promotional clips.
- [x] **Silence is Never Agreement**: Unsettled consent categories flagged and require explicit human confirmation.
- [x] **Human Decision Gate**: Advisory AI agents cannot approve or decline proposed likeness uses.

---

## 6. Release Signoff
**Status:** APPROVED FOR PRODUCTION DEPLOYMENT  
**Signoff:** Automated CI/CD & Operations Engineering Team  
