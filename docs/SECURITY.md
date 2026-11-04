# SceneSteward — Security Model

Security is a design constraint, not a review step. This document states what is
enforced, where it is enforced, and what is *not* yet done.

## Threat model (assets & actors)

**Assets**: participant identity & contact details, consent history, release
documents, story elements marked highly sensitive, agent outputs, audit trail.

**Actors**: anonymous internet, authenticated member with insufficient role,
malicious or compromised member, malicious document content (prompt injection),
compromised Switch room member, token replay/theft, curious viewer/editor.

## What is enforced (and where)

| # | Control | Where | Tested |
|---|---|---|---|
| 1 | JWT verification: signature, expiry, issuer, audience, subject; JWKS cached 1h (supabase mode) | `core/security.py` | `tests/integration/test_auth.py` |
| 2 | Dev tokens HS256, single purpose; refused when `AUTH_PROVIDER≠dev`; production refuses dev provider | startup check + `mint_dev_token` guard | test_auth.py, startup_checks |
| 3 | Account status must be `active` | `api/dependencies.get_current_user` | suspended-account test |
| 4 | Role-based authorisation per endpoint (never from client claims) | `core/permissions.py` + route gates | `tests/security/test_rbac.py` |
| 5 | Project isolation: membership + resource-scope checks; 404 (no oracle) for non-members | `api/dependencies.py` | cross-project tests |
| 6 | Participant isolation: linked participant sees only own record | participants endpoints + list scoping | rbac tests |
| 7 | Contact data Fernet-encrypted at rest; decrypted only for owner/producer/care_lead/self; never logged | `ParticipantContactRecord`, `core/security.py`, audit redaction | rbac + documents tests |
| 8 | Identifying story details hidden from editor/viewer; `highly_sensitive` included | `story_elements._out` | rbac tests |
| 9 | Consent immutability: DB triggers (see DATABASE.md); no update endpoints exist | migration `b3f9c21a7d44` | test_migrations.py |
| 10 | Audit append-only: DB triggers; app writes inside same transaction | `services/audit.py`, triggers | append-only test |
| 11 | Upload security: extension allowlist, 25 MiB cap, **magic-byte MIME sniff**, safe names (uuid prefix), path traversal rejected, single-use-purpose HMAC-signed URLs (10 min), discarded on failure | documents endpoints + `storage/local.py` | test_documents.py |
| 12 | Prompt injection: documents/messages are data; agents have **no tools**; instructions inside them cannot grant permissions; ethics reviewer flags them | agents + `ethics_reviewer.py` | agents tests |
| 13 | Agent permission profiles: prefetched minimal context; no DB session, no keys; outputs schema-validated, malformed → `rejected` | `agents/base.py`, `services/agent_context.py` | agents tests |
| 14 | Decisions are human-only: agents cannot call confirm/decide endpoints (no such agent capability exists); decisions immutable once made | endpoints + state machine | e2e test |
| 15 | Switch events validated (type+sequence/event_id), deduplicated (`integration_events` UNIQUE), correlated; **no path to consent tables** | `integrations/switch/listener.py` | test_switch.py |
| 16 | Rate limiting: 120 req/min per IP (configurable), 429 + no internals | `main.py` | manual/load |
| 17 | Security headers: nosniff, DENY frame, no-referrer, no-store; CORS restricted to `FRONTEND_ORIGIN` | `main.py` | — |
| 18 | Body-size cap 1 MiB (uploads exempt — they use signed URLs) | `main.py` | — |
| 19 | Secrets via env only; `.env` gitignored; `.env.example` has placeholders; startup checks report presence (never values) | `core/config.py` | — |
| 20 | Optimistic locking on mutable entities (`version` + `expected_version` → 409) | models + PATCH routes | concurrency paths |
| 21 | Least-privilege Switch rooms: `participant_review` rooms are 1:1 with a participant | `switch_room_links`, listener | — |
| 22 | Sensitive timeline entries hidden from viewers | `services/timeline.py` | rbac test |
| 23 | Synthetic data only in seed/tests; no real participant data anywhere | seeds, tests | review |

## What is NOT done (honest list)

- Token revocation/denylist (stateless JWTs) — mitigate with short TTLs (1h dev default);
  Supabase sessions are revocable client-side.
- Row-Level Security inside PostgreSQL (defence in depth beyond app-layer RBAC).
- Malware scanning of uploads (MIME sniff ≠ AV). Add ClamAV or a scanning function.
- Secrets manager integration (Vault/SM); env files only.
- WAF/rate limits at the edge (app-level only).
- Encryption-key rotation tooling for `APP_ENCRYPTION_KEY` (document, manual re-encrypt).
- Formal security audit / pen test. **No compliance or certification is claimed.**
  This is a prototype, not a medical/legal system of record.
- Sentry/alerting pipelines; logs are structured JSON on stdout for your collector.

## Data protection notes

- `participant_communications.draft_content` is stored in the DB (private). Emails are
  **never sent by the system**; all sending is an explicit human action after approval.
- `agent_runs.output_data` holds validated structured output only — never raw documents.
  If you enable the Anthropic provider, document pages are transmitted (≤12k chars) —
  minimise further before real participants are involved (see AGENTS.md → data sent).
- Audit events never store decrypted contacts (ciphertext or `[redacted]` only).
- Synthetic demo identity: "Amara Okoro (fictional)". Do not import real participants
  until items in "NOT done" are addressed.

## Reporting
If you find a vulnerability, do not open a public issue; contact the maintainers directly.
