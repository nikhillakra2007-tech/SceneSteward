# SceneSteward — API Reference

Base URL: `/api/v1`. Interactive docs: `/docs` (disabled in production).
Auth: `Authorization: Bearer <token>` on every endpoint except `/health*` and the
HMAC-signed storage transfer routes. Token verification: dev HS256 (local) or
Supabase JWKS (configurable issuer/audience). See SECURITY.md.

## Conventions

- **Errors** — uniform body: `{"error": {"code", "message", "correlation_id?", "detail?"}}`.
  Codes: `unauthenticated`, `invalid_token`, `token_expired`, `invalid_audience`,
  `invalid_issuer`, `user_not_provisioned`, `account_inactive`, `permission_denied`,
  `not_found`, `conflict`, `version_conflict`, `precondition_failed`,
  `invalid_review_transition`, `already_confirmed`, `already_member`, `last_owner`,
  `payload_too_large`, `rate_limited`, `upstream_unavailable`, `internal_error`.
- **Pagination** — most lists: `limit` (1–100, default 20) & `offset` → `{items, total, limit, offset}`.
  Timeline: keyset — `limit` (1–200, default 50) & `cursor` (opaque) → `{items, next_cursor}`.
- **Optimistic locking** — PATCH endpoints for `projects`, `participants`,
  `story-elements`, `proposed-uses`, consent confirm and review decisions require
  `expected_version` (integer ≥ 1) → `409 version_conflict` on mismatch.
- **Idempotency** — `integration_events` is unique on `(integration_name, external_event_id)`;
  all other POSTs are not idempotent by default.
- **Sensitive reads** (contacts, consent, documents, timeline details) require the
  `project_owner`, `producer`, or `participant_care_lead` role, or the linked
  participant for their own data. Editors/viewers/directors are denied.
- **Not-found vs forbidden** — membership/scope failures return `404` (no existence
  oracle across projects); role failures inside an accessible project return `403`.

## Auth
`GET /auth/me` → current user + active memberships.
`POST /auth/logout` → stateless; clients discard the token (Supabase: sign out client-side).

## Projects & members
```
POST   /projects                                   create (creator becomes project_owner)
GET    /projects?limit&offset                      list my projects
GET    /projects/{project_id}                      member only
PATCH  /projects/{project_id}                      owner|producer|director; expected_version
GET    /projects/{project_id}/members              member only
POST   /projects/{project_id}/members              owner only – {email, role}; 404 if email unknown
PATCH  /projects/{project_id}/members/{member_id}  owner only; last active owner cannot be demoted/deactivated (412)
DELETE /projects/{project_id}/members/{member_id}  owner only; soft removal; last owner protected (412)
```

## Participants
```
POST   /projects/{project_id}/participants         owner|producer|care_lead
GET    /projects/{project_id}/participants         members; linked participant sees only self
GET    /participants/{id}                          member / self
PATCH  /participants/{id}                          staff (or self: language/contact/accessibility only)
GET    /participants/{id}/history                  consent version history summary
GET    /participants/{id}/timeline                 keyset; viewer-filtered
GET    /participants/{id}/contacts                 owner|producer|care_lead|self  (decrypted on the fly)
POST   /participants/{id}/contacts                 owner|producer|care_lead; stored Fernet-encrypted
```

## Consent records (versioned; append-only)
```
POST   /participants/{id}/consent-records          owner|producer|care_lead
          {source_type, source_document_id?, explanation?, choices:[{category, choice, ...}]}
GET    /participants/{id}/consent-records          members
GET    /consent-records/{record_id}                members
GET    /consent-records/{record_id}/history        members (all versions, ascending)
POST   /consent-records/{record_id}/confirm        owner|producer|care_lead
          {confirmation: confirmed|declined|partial, confirmation_evidence, expected_version}
          confirmed ⇒ record locked (trigger-enforced), previous confirmed version superseded
```
No PATCH/PUT exists for consent records or choices. Corrections = new version.

## Release documents (private storage)
```
POST   /participants/{id}/documents/upload-url     owner|producer|care_lead
          {original_filename, mime_type, file_size, document_date?, signature_status?}
          → {storage_key, upload_url, expires_in_seconds}
PUT    {upload_url}                                raw bytes; token is the capability (10 min TTL, 25 MiB cap)
POST   /participants/{id}/documents/complete-upload {storage_key, document_date?, signature_status?}
          verifies file exists, size cap, magic-byte MIME sniff → creates record (pending)
GET    /participants/{id}/documents                owner|producer|care_lead|self
GET    /documents/{id}                             same access rule
GET    /documents/{id}/download-url                same rule → 5 min signed URL
POST   /documents/{id}/extract                     owner|producer|care_lead → pypdf/txt/docx pages
POST   /documents/{id}/propose-consent             runs Consent Analyst → UNCONFIRMED proposal
GET    /api/v1/storage/local/download/{token}      download via signed token (dev storage)
```
Never: path traversal keys (rejected), unverifiable MIME (file discarded), editor/viewer access.

## Story elements
```
POST   /projects/{pid}/story-elements              owner|producer|director|editor
GET    /projects/{pid}/story-elements              members; identifying_details hidden from editor/viewer
GET    /story-elements/{id}                        members
PATCH  /story-elements/{id}                        same roles; expected_version
```

## Proposed uses & analysis
```
POST   /projects/{pid}/proposed-uses               owner|producer|director|editor
          {participant_id, story_element_id?, use_type, platform?, audience?, purpose?,
           territory?, context_description?, run_analysis=true}
GET    /projects/{pid}/proposed-uses[?status=]     members
GET    /proposed-uses/{id}                          members
PATCH  /proposed-uses/{id}                          same roles; status only → 'withdrawn'; expected_version
POST   /proposed-uses/{id}/analyse                  same roles → runs deterministic engine + agents
GET    /proposed-uses/{id}/agent-findings           members
```
Outcomes: `RECORDED_CHOICE_MATCH | NEEDS_DISCUSSION | PARTICIPANT_DECLINED | HUMAN_REVIEW_REQUIRED | UNRESOLVED`.
A match is never an approval; human review is always created.

## Reviews
```
GET    /projects/{pid}/reviews[?review_status=]    members
GET    /reviews/{id}                               members
POST   /reviews/{id}/human-decision                owner|producer|care_lead
          {decision: approve|decline|request_changes|needs_participant_discussion|escalate,
           reason, expected_version}
          Validated state machine (pending|escalated → completed); decided reviews are immutable (409/412).
POST   /reviews/{id}/request-participant-discussion owner|producer|care_lead; creates follow-up task
POST   /reviews/{id}/resolve                       owner|producer|care_lead; completed reviews only; idempotent
```
`approve` = internal review passed → proposed use `approved`. It is **not** participant consent.

## Agents
```
POST   /agents/runs                                owner|producer|care_lead
          {agent_name: consent_analyst|story_change_analyst|participant_advocate|
                        ethics_reviewer|production_coordinator, proposed_use_id}
GET    /agents/runs/{run_id}                       members
GET    /proposed-uses/{id}/agent-findings          members (5 runs after analysis)
```
Outputs are schema-validated; malformed model output → run `rejected`, never persisted as findings.

## Tasks & timeline
```
GET    /projects/{pid}/tasks[?status&owner_user_id=] members
PATCH  /tasks/{id}                                  assignee (status only) or owner|producer|director|editor|care_lead
GET    /projects/{pid}/timeline[?limit&cursor]      members; viewers see non-sensitive entries only
GET    /participants/{id}/timeline                  member / self
```

## Health & integration status (unauthenticated, secret-free)
```
GET    /health            liveness
GET    /health/ready      {"status":"ok|degraded","checks":{"database":"ok|unavailable"}}
GET    /api/v1/integrations/status
       → postgresql | storage | ai_provider | switch | auth | redis
         ∈ configured_verified | configured_unverified | missing_credentials |
           unavailable | failed_authentication | timeout | not_configured
```
`configured_verified` for Switch is printed only after a real health+auth probe, never from env vars alone.

## Example: the "Beyond the Silence" analysis

```bash
TOKEN=$(python scripts/dev_token.py --email oscar@example.com --name "Oscar Owner")
curl -s -H "Authorization: Bearer $TOKEN" -X POST \
  http://127.0.0.1:8000/api/v1/projects/<pid>/proposed-uses -H "Content-Type: application/json" -d '{
    "participant_id": "<participant>", "story_element_id": "<element>",
    "use_type": "promotional_trailer", "platform": "youtube",
    "context_description": "Sensitive interview excerpt for the promotional trailer + AI voice reconstruction",
    "run_analysis": true }'
# → 201, status "analysis_complete"
curl -s -H "Authorization: Bearer $TOKEN" http://127.0.0.1:8000/api/v1/projects/<pid>/tasks?status=open
# → unresolved_permission (festival_submissions, new_platform, new_territory, promotional_clips…), review task
```
