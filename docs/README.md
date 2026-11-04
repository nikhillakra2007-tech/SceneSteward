# SceneSteward — Documentation Index

This directory contains technical specifications, architecture blueprints, acceptance reports, and operational guides for SceneSteward.

---

## 1. Architecture & Design Specifications
- [`BACKEND_ARCHITECTURE.md`](file:///c:/Users/nikhi/OneDrive/Desktop/coding/FLIPTHESWITCH/docs/BACKEND_ARCHITECTURE.md) — Comprehensive backend architectural overview and module design.
- [`DATABASE_ARCHITECTURE.md`](file:///c:/Users/nikhi/OneDrive/Desktop/coding/FLIPTHESWITCH/docs/DATABASE_ARCHITECTURE.md) — Schema design, RLS policies, tables, and tenancy boundaries.
- [`DATABASE_RELATIONSHIPS.md`](file:///c:/Users/nikhi/OneDrive/Desktop/coding/FLIPTHESWITCH/docs/DATABASE_RELATIONSHIPS.md) — Entity-relationship diagrams and composite integrity keys.
- [`DATABASE_SECURITY.md`](file:///c:/Users/nikhi/OneDrive/Desktop/coding/FLIPTHESWITCH/docs/DATABASE_SECURITY.md) — PostgreSQL security controls, least privilege roles, and RLS definitions.
- [`API_INTEGRATION_MAP.md`](file:///c:/Users/nikhi/OneDrive/Desktop/coding/FLIPTHESWITCH/docs/API_INTEGRATION_MAP.md) — Complete REST route hierarchy and data flow specifications.
- [`AUTHORIZATION_MATRIX.md`](file:///c:/Users/nikhi/OneDrive/Desktop/coding/FLIPTHESWITCH/docs/AUTHORIZATION_MATRIX.md) — Role-based permission map across projects, participants, and reviews.

---

## 2. Container Acceptance & Deployment Reports (November 2026)
- [`DOCKER_BUILD_REPORT.md`](file:///c:/Users/nikhi/OneDrive/Desktop/coding/FLIPTHESWITCH/docs/DOCKER_BUILD_REPORT.md) — Multi-service image builds, caching, non-root execution (`UID 10001`).
- [`CONTAINER_RUNTIME_REPORT.md`](file:///c:/Users/nikhi/OneDrive/Desktop/coding/FLIPTHESWITCH/docs/CONTAINER_RUNTIME_REPORT.md) — Live `docker compose ps` verification, port bindings, and health checks.
- [`DATABASE_CONTAINER_REPORT.md`](file:///c:/Users/nikhi/OneDrive/Desktop/coding/FLIPTHESWITCH/docs/DATABASE_CONTAINER_REPORT.md) — PostgreSQL 18 catalog audit (20 tables, 18 RLS, 69 policies) and migration head verification.
- [`CLAMAV_CONTAINER_REPORT.md`](file:///c:/Users/nikhi/OneDrive/Desktop/coding/FLIPTHESWITCH/docs/CLAMAV_CONTAINER_REPORT.md) — Live TCP `zINSTREAM` scanning, clean stream verification, and EICAR malware interception.
- [`NETWORK_SECURITY_REPORT.md`](file:///c:/Users/nikhi/OneDrive/Desktop/coding/FLIPTHESWITCH/docs/NETWORK_SECURITY_REPORT.md) — Network isolation, security headers, bridge networking, and exposure audit.
- [`CONTAINER_E2E_REPORT.md`](file:///c:/Users/nikhi/OneDrive/Desktop/coding/FLIPTHESWITCH/docs/CONTAINER_E2E_REPORT.md) — 13-step in-container documentary lifecycle execution and consent invariant proof.
- [`CONTAINER_RECOVERY_REPORT.md`](file:///c:/Users/nikhi/OneDrive/Desktop/coding/FLIPTHESWITCH/docs/CONTAINER_RECOVERY_REPORT.md) — Container fault injection, worker restart recovery, volume persistence, and isolated restore tests.
- [`DOCKER_DEPLOYMENT_BLOCKERS.md`](file:///c:/Users/nikhi/OneDrive/Desktop/coding/FLIPTHESWITCH/docs/DOCKER_DEPLOYMENT_BLOCKERS.md) — Resolution record for host Docker infrastructure.

---

## 3. Operational Runbooks & Deployment Guides
- [`DEPLOYMENT.md`](file:///c:/Users/nikhi/OneDrive/Desktop/coding/FLIPTHESWITCH/docs/DEPLOYMENT.md) — Deployment instructions and operational preflight.
- [`STAGING_DEPLOYMENT_GUIDE.md`](file:///c:/Users/nikhi/OneDrive/Desktop/coding/FLIPTHESWITCH/docs/STAGING_DEPLOYMENT_GUIDE.md) — Staging environment provisioning guide.
- [`DISASTER_RECOVERY.md`](file:///c:/Users/nikhi/OneDrive/Desktop/coding/FLIPTHESWITCH/docs/DISASTER_RECOVERY.md) — Backup, point-in-time recovery, and restore runbooks.
- [`SECRETS_AND_ENCRYPTION.md`](file:///c:/Users/nikhi/OneDrive/Desktop/coding/FLIPTHESWITCH/docs/SECRETS_AND_ENCRYPTION.md) — Fernet key ring management, key rotation, and secret boundaries.
- [`WORKER_OPERATIONS.md`](file:///c:/Users/nikhi/OneDrive/Desktop/coding/FLIPTHESWITCH/docs/WORKER_OPERATIONS.md) — Outbox daemon operation, polling intervals, and lease management.

---

## 4. Provider Verification Logs
- [`LIVE_CLAMAV_VERIFICATION.md`](file:///c:/Users/nikhi/OneDrive/Desktop/coding/FLIPTHESWITCH/docs/LIVE_CLAMAV_VERIFICATION.md) — Socket wire protocol inspection logs.
- [`LIVE_AUTH_VERIFICATION.md`](file:///c:/Users/nikhi/OneDrive/Desktop/coding/FLIPTHESWITCH/docs/LIVE_AUTH_VERIFICATION.md) — Supabase Auth adapter and dev token verification.
- [`LIVE_STORAGE_VERIFICATION.md`](file:///c:/Users/nikhi/OneDrive/Desktop/coding/FLIPTHESWITCH/docs/LIVE_STORAGE_VERIFICATION.md) — Storage provider verification and signed URL tests.
- [`LIVE_ANTHROPIC_VERIFICATION.md`](file:///c:/Users/nikhi/OneDrive/Desktop/coding/FLIPTHESWITCH/docs/LIVE_ANTHROPIC_VERIFICATION.md) — Anthropic Messages API client verification and deterministic fallback.
- [`LIVE_SWITCH_VERIFICATION.md`](file:///c:/Users/nikhi/OneDrive/Desktop/coding/FLIPTHESWITCH/docs/LIVE_SWITCH_VERIFICATION.md) — Switch integration adapter and room link verification.
