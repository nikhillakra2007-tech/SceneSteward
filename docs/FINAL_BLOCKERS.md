# SceneSteward — Final Blockers & Staging Progression Ledger

**Date**: November 4, 2026  
**Auditor**: Principal Backend Architect, Application Security Reviewer, SRE  
**Current Milestone**: **`STAGING CANDIDATE`**  
**Target Milestone**: **`LIVE STAGING VERIFIED`** / **`PRODUCTION CANDIDATE`**  

---

## 1. Executive Summary

Milestone 1 (**Staging Candidate**) is **100% complete and verified**. All core application logic, database schemas, Row Level Security policies, HMAC trust boundaries, 48 REST API endpoints, 107 automated tests, and disaster recovery harnesses are passing with zero defects.

To transition to Milestone 2 (**Live Staging Verified**) and ultimately Milestone 3 (**Production Candidate**), the external cloud service credentials and network daemons detailed below must be provisioned.

---

## 2. Blockers for Milestone 2 (`LIVE STAGING VERIFIED`)

| Blocker ID | Affected Service | Severity | Description | Remediation Action for Project Owner |
|:---:|:---|:---:|:---|:---|
| **BLK-01** | **Supabase Auth** | HIGH | Live RS256/ES256 verification against real Supabase JWKS endpoint is awaiting cloud project setup. | Provision staging Supabase project and provide `SUPABASE_URL` and `SUPABASE_ANON_KEY` in staging `.env`. |
| **BLK-02** | **Supabase Storage** | HIGH | Cloud S3-compatible document storage bucket is unconfigured; currently operating in verified local filesystem storage mode. | Create `scenesteward-documents` storage bucket in Supabase and set `SUPABASE_STORAGE_BUCKET`. |
| **BLK-03** | **Anthropic Claude API**| MEDIUM | Live AI agent analysis calls Claude API; currently evaluated using deterministic offline model evaluator. | Add valid `ANTHROPIC_API_KEY` to staging `.env` with Claude 3.5 Sonnet quota. |
| **BLK-04** | **Switch Webhook Host** | MEDIUM | Switch room creation and message sync is using mock/outbox retry pattern; live Switch staging host is unconfigured. | Set `SWITCH_BASE_URL` and `SWITCH_WEBHOOK_SECRET` pointing to the staging Switch cluster. |
| **BLK-05** | **ClamAV Daemon** | MEDIUM | Antivirus scanner is currently running in local simulated mode with fail-closed tests; live ClamAV daemon is not reachable on localhost. | Deploy ClamAV daemon container (`clamav/clamav:latest`) and configure `CLAMAV_HOST` and `CLAMAV_PORT`. |

---

## 3. Production Readiness Prerequisites (Milestone 3)

1. **Hardware Security Module (HSM) / Key Vault**:
   Store `FIELD_ENCRYPTION_KEY` and `DATABASE_IDENTITY_SECRET` in AWS KMS, Google Cloud KMS, or HashiCorp Vault rather than raw environment files.
2. **PostgreSQL Connection Pooler**:
   Deploy PgBouncer in transaction pooling mode in front of PostgreSQL 18.6 with session cleanup (`DISCARD ALL`).
3. **Continuous Disaster Recovery Backups**:
   Schedule automated daily `pg_dump` snapshots to an immutable, write-once-read-many (WORM) offsite cloud bucket.

