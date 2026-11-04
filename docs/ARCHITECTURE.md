# SceneSteward — Architecture

Participant-centred documentary production workspace. **The SceneSteward PostgreSQL
database is the source of truth.** Switch is a collaboration surface only. AI agents
are analytical assistants. Humans retain authority over every participant decision.

## System context

```
┌────────────┐   HTTPS/JSON   ┌───────────────────────────────────────────┐
│  Dashboard │ ─────────────► │  FastAPI backend (app.main:app)           │
│  (static)  │  Bearer JWT    │                                           │
└────────────┘                │  api/v1 (routes)                          │
                              │    → services (business logic)             │
        ┌───────────────────► │    → repositories / SQLAlchemy             │
        │   signed URLs       │    → integrations/                        │
┌───────┴─────────┐           │        switch/  (agent-protocol adapter)   │
│ Private object  │ ◄──────── │        storage/ (local | supabase)         │
│ storage         │  PUT/GET  │        ai/      (anthropic | offline)      │
└─────────────────┘           │    → agents/   (5 specialist agents)       │
                              │    → workflows/(proposed_use_analysis)     │
                              └──────┬───────────────────┬─────────────────┘
                                     │ SQL                │ SSE down / HTTP up
                              ┌──────▼─────┐      ┌──────▼─────┐
                              │ PostgreSQL │      │   Switch   │  rooms, SSE, /message
                              │ (truth)    │      │ (collab.)  │
                              └────────────┘      └────────────┘
```

## Layering rules

1. **Routes** (`app/api/v1/endpoints`) — validate input, resolve auth + membership,
   call services, serialise output. No business logic.
2. **Services** (`app/services`) — business rules, transactions, audit writes.
3. **Models** (`app/models`) — SQLAlchemy 2.x mapping + CHECK constraints.
4. **Schemas** (`app/schemas`) — Pydantic request/response contracts.
5. **Integrations** (`app/integrations`) — all external systems behind interfaces.
6. **Agents** (`app/agents`) — validated structured analysis; never mutate state.
7. **Workflows** (`app/workflows`) — orchestration of engine + agents + outcomes.

Request flow: request-id middleware → rate limiter → CORS → body-size cap →
route → `get_current_user` → `get_membership` → role gate → resource scope
check → service (single transaction) → audit event → response (+ security headers).

## Trust boundaries

| Boundary | Rule |
|---|---|
| Browser → API | Bearer JWT (dev HS256 locally; Supabase JWKS in prod). Claims verified; user_id never taken from the client. |
| API → PostgreSQL | Dedicated role, least privilege, parameterised ORM. Audit + consent immutability enforced by DB triggers. |
| API → Storage | Private bucket; short-lived HMAC-signed upload/download URLs; MIME sniffed from bytes. |
| API → AI (Anthropic) | Offline deterministic mode by default; documents sent as *data only* with injection defences; outputs schema-validated, rejected if malformed. Agents hold no DB credentials and no tools. |
| API → Switch | Agent-protocol only (SSE down, HTTP up, Bearer agent key). Inbound events validated + deduplicated. **No path from a Switch event to consent tables exists.** |
| Human ↔ decision | Confirmed consent changes only via `/consent-records/{id}/confirm` by owner/producer/care_lead; decisions only via `/reviews/{id}/human-decision`. |

## Failure modes & degradation

- **Switch down** → `/integrations/status` reports it; nothing is sent; `integration_events` record failures; retries via `scripts/switch_retry.py` (bounded, dead-letter). Records are never blocked.
- **AI down** (anthropic mode) → agent run marked `failed`/`timeout`; workflow still persists engine analysis, review, and tasks; outcome is unaffected (engine is deterministic).
- **DB down** → `/health/ready` = `degraded`; write endpoints return 503 via exception handler; no partial writes (single transaction per request).
- **Bad upload** → MIME sniff fails → file deleted, `412`; size exceeded → `413`/`412`, nothing persisted.

## Data flow — proposed use analysis

```
POST /projects/{id}/proposed-uses ──► create (status=submitted)
                                      │
                                      ▼ (if run_analysis)
                    consent_comparison.normalize_proposed_use (keywords + use_type map)
                                      ▼
                    compare_with_confirmed_record (latest CONFIRMED record only)
                                      ▼  outcome ∈ RECORDED_CHOICE_MATCH | NEEDS_DISCUSSION
                    persist proposed_use_analyses (append-only)   | PARTICIPANT_DECLINED |
                                      ▼                             HUMAN_REVIEW_REQUIRED | UNRESOLVED
                    proposed_uses.status = analysis_complete
                                      ▼
                    CREATE Review (human, pending) + tasks (unresolved_permission, review)
                                      ▼
                    agents ×5 (validated output; agent_runs rows)  [never approves anything]
                                      ▼
                    draft participant communication (status=draft; NEVER sent)
                                      ▼
                    Switch notify (best-effort; skipped if unverified/unlinked)
                                      ▼
                    human records decision → audit_events (append-only)
```

Silence is never agreement: categories absent from the latest confirmed record are
treated as `not_discussed`. `RECORDED_CHOICE_MATCH` is not publication approval.

## Repository map

See top-level README.md. Backend root = `backend/`; tests = `backend/tests/`.
