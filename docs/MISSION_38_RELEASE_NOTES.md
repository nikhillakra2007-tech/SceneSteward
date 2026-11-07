# SCENESTEWARD — RELEASE NOTES: v1.0.0-rc1
**Release Version:** `v1.0.0-rc1` (Local Release Candidate 1)  
**Target Commit:** `f01a9be4460f207c72ffc55bd85c0dbc073cb95a`  
**Release Date:** 2026-11-06  
**Engineering Lead:** Antigravity Engineering Systems  

---

## 1. Product Overview

SceneSteward is an ethical documentary production management platform designed to protect participant consent, likeness usage rights, and care continuity across the lifecycle of documentary filmmaking.

Release Candidate 1 (`v1.0.0-rc1`) represents a feature-complete, empirically verified local release candidate.

---

## 2. Key Capabilities & Architectural Highlights

### 2.1 The 15 Canonical Categories of Ethical Consent
- Enforces non-transitive consent: Consenting to documentary interview footage NEVER grants consent to promotional teasers, voice synthesis, or commercial merchandising.
- Silence is never consent: Unsettled categories default to `not_discussed` and block affected footage proposals.
- Immutable confirmed releases: Changes require a new versioned release agreement (`version: 2`).

### 2.2 Participant Transparency Portal
- Standalone, mobile-optimized portal for documentary subjects.
- Authenticated via time-limited cryptographic capability tokens (`604800s`).
- Allows participants to view their confirmed consent choices in plain language.
- Empowers subjects to submit direct questions, clarification requests, and formal consent withdrawals.

### 2.3 Double-Lock Audit Immutability & SHA-256 Chaining
- Layer 1 (RLS): Runtime application role `scenesteward_app` is denied `UPDATE` and `DELETE` privileges.
- Layer 2 (Engine Triggers): Table owner role `scenesteward` is blocked from mutating audit history by physical PostgreSQL triggers (`trg_audit_events_no_update`, `trg_audit_events_no_delete`).
- Every audit entry includes previous-event SHA-256 hash chaining for tamper-evident verification.

### 2.4 Fail-Closed Outbound Communication & Participant Care
- Mandatory human approval: Draft communications cannot be sent without prior human approval by an authorized role (`project_owner`, `producer`, or `care_lead`).
- Fail-closed outbound delivery: When external email/SMS providers are offline, requests return `HTTP 503` without falsely marking messages "sent".
- Operational 1-click clipboard fallback enables crew to route approved messages manually during outages.

### 2.5 Multi-Tenant Database Isolation
- 18 public tables protected by PostgreSQL Row Level Security (RLS).
- Evaluated per transaction using cryptographic HMAC session tokens.
- Cross-project queries return 0 rows at the database engine level.

---

## 3. Independent Verification Summary

| Test Harness | Total Tests | Passed | Failed | Status |
| :--- | :---: | :---: | :---: | :---: |
| **Backend Pytest Suite** | 293 | 293 | 0 | `VERIFIED` |
| **Playwright Automated Browser Suite** | 11 | 11 | 0 | `VERIFIED` |
| **Documentary Lifecycle Engine** | 8 | 8 | 0 | `VERIFIED` |
| **Synthetic Container Workflow** | 13 | 13 | 0 | `VERIFIED` |
| **PostgreSQL RLS & Trigger Audit** | 6 | 6 | 0 | `VERIFIED` |
| **Disaster Recovery & Restore** | 7 metrics | 7 | 0 | `VERIFIED` |
| **Point-in-Time Recovery (PITR)** | 4 metrics | 4 | 0 | `VERIFIED` |
| **Frontend Production Build** | 6 routes | 6 | 0 | `VERIFIED` |

---

## 4. Operational Requirements & Infrastructure Classification

To deploy `v1.0.0-rc1` to a live production environment, the following external cloud infrastructure components must be provisioned:

| Dependency | Local RC State | Production Provisioning Requirement |
| :--- | :--- | :--- |
| **Identity Provider** | Dev Provider (HS256) | Supabase JWKS RS256/ES256 Endpoint |
| **Antivirus Scanner** | Mock Scanner | ClamAV Daemon Container on TCP 3310 |
| **Email / SMS Delivery** | Safe Fail-Closed 503 | SMTP Server or Twilio Messaging Service |
| **Offsite Backup Target** | Local Vault Directory | AWS S3 or GCP Cloud Storage Bucket |
| **Document OCR Engine** | PyPDF / DOCX Extract | Host / Container Tesseract OCR Engine |
| **AI Advisory Guidance** | Deterministic Offline | Anthropic Claude API (`claude-sonnet-4-5`) |

---

## 5. Certification

SceneSteward `v1.0.0-rc1` is certified as an integrated, stable, and reproducible **Local Release Candidate**.

