# Mission 44 — Actual Switch Connection (Final Report)

**Date:** 2026-11-07
**Repository:** SceneSteward (FLIPTHESWITCH), branch `main`
**Switch Core:** `http://127.0.0.1:64432` (Agent Switch Console, reachable)
**SceneSteward backend:** `http://127.0.0.1:8000` (healthy)

> Honest status up front: SceneSteward is connected to the real Switch Core and can
> process a Switch-shaped room event end-to-end against PostgreSQL. Two things are
> **not** verified: (1) a genuinely human-originated room message (no human is a
> member of the room), and (2) Google Antigravity as a Console provider / room
> participant (sign-in + `session/new` blocked). Details and evidence below.

---

## A. What was reused (nothing recreated)

| Item | Value |
|---|---|
| Agent ID | `adf16e2a-4ce2-4598-baa7-ca8865ca4308` (`scenesteward-clearance`) |
| Room ID | `aeec10b9-781c-4625-a07a-692279393943` (SceneSteward — Footage Clearance) |
| Matrix room | `sw_room_9a87a47cafa54468891786600cba9d0a`, `channel_public` |
| Switch DB | PostgreSQL `127.0.0.1:64434/switch` (1 agent, 1 room, ≥19 messages) |
| Registration token | existing; **not** re-registered (avoids duplicate agent) |

No new agent, room, or script was created. The local simulator under
`port 8010` was left intact for regression.

---

## B. Switch Core verification — 13/13 PASS

Script: `scratch/verify_actual_switch_connection.py`
Evidence: `scratch/actual_switch_verification_results.json`

| # | Check | Result |
|---|---|---|
| 1 | `GET /health` | PASS — 200 `{"status":"ok"}` |
| 2 | List agents | PASS — 200 |
| 3 | SceneSteward agent exists | PASS — count 1 |
| 4 | List rooms | PASS — 200 |
| 5 | Footage Clearance room exists | PASS |
| 6 | Post message to room | PASS — `event_id=sw_e2668fd74d814040aaa2740ca82c07ab` |
| 7 | Poll agent events | PASS — 204 (empty queue; contract-valid) |
| 8 | Poll verdict | PASS |
| 9 | Room history | PASS — 200 |
| 10 | History non-empty | PASS |
| 11 | SceneSteward `/health` | PASS |
| 12 | Agent row in Switch DB | PASS |
| 13 | Room row in Switch DB | PASS |

### Event contract (read from Core 0.31.0 source, not guessed)

Source: `...\switch-core\0.31.0\src\core\switch_core\bridges\agent\`
(`api/handlers.py`, `api/schemas.py`, `protocol/types.py`, `protocol/event_buffer.py`).

| Endpoint | Method | Empty | Available |
|---|---|---|---|
| `/agents/{id}/events?timeout=` | GET (long-poll) | **204** | 200 `{"events":[AgentEvent]}` |
| `/agents/{id}/rooms/{rid}/events?timeout=` | GET | **204** | 200 `{"events":[...]}` |
| `/agents/{id}/notifications?timeout=` | GET | **204** | 200 |
| `/agents/{id}/events` + `Accept: text/event-stream` + `connection_id` | GET (SSE) | heartbeats | `event:`/`data:` frames, first `connection_state` |
| `/agents/{id}/rooms/{rid}/history?limit=` | GET | `{"events":[],"has_more":false}` | `{"events":[...],"has_more":bool}` |
| `/agents/rooms/{rid}/participants` | GET | — | `{"participants":[{type,agent_id,name,status}]}` |

**AgentEvent:** `{type: message|command|room_join, room_id, bridge_id, channel_type,
payload:{sender, sender_name, sender_kind, message_id, body, timestamp, thread_id,
attachments}}`. Dedupe key = `payload.message_id`.

SSE requires a client `connection_id` + `POST /agents/{id}/connection/beat` every ~2s
and room claims via `/connection/subscribe`. Long-poll is the simpler, verified path.

Own posted messages do **not** appear in the sender's own event stream — loop safety is
server-side as well as in our handler.

---

## C. SceneSteward end-to-end (worker-level) — PARTIAL

**Verified working:**
- `SWITCH_ADAPTER=http` config points at the live Core.
- Direct post through the agent API succeeds (`200`, `event_id` returned).
- `SwitchAgentWorker.process_room_message` runs the real clearance workflow:
  PostgreSQL lookup → project / participant / consent / proposed use → non-transitive
  consent rules → assessment → `NEEDS_DISCUSSION` (or `REQUIRES_HUMAN_REVIEW`).
- Worker result from the live run:
  `{"status":"clearance_analyzed","room_id":"aeec10b9-...",
    "project_id":"63eb18b5-...","review_id":"<uuid>","outcome":"NEEDS_DISCUSSION"}`
- Room history contains prior SceneSteward assessments, including the full F-104 audit
  (`promotional_clips = NOT_DISCUSSED`, non-transitive invariant, Review ID
  `1fafb3f6-50b9-4d9b-a43e-cded10de08ea`).

**Honest gap:** `scripts/run_real_switch_e2e.py` printed
`switch message failed status=404` before falling back to an `integration_failure`
task. The clearance computation succeeded, but **the reply post through that script's
adapter path returned 404**. Direct posts through `/agents/{id}/message` return 200.
→ The adapter's outbound path and the script's room/message call are **not** the same
call that was verified. This must be fixed before claiming "reply posted" for that
script. Classification for this path: **PARTIAL**.

**Hardened this session (uncommitted):**
- `app/integrations/switch/http_adapter.py` — `validate_inbound_event` now accepts the
  real `AgentEvent` shape (`{type, room_id, payload:{...}}`) in addition to the
  simulator shape.
- `app/integrations/switch/listener.py` — `_extract_room_id`, `external_event_id`
  (dedupe on `payload.message_id`), and both wire shapes in `_record_inbound_event`.
- `app/integrations/switch/agent_worker.py` — `process_room_message` handles the real
  `payload` shape; loop guard uses `payload.sender_kind in {agent, platform}` plus a
  name fallback only when `sender_kind` is absent.
- `app/integrations/antigravity/actual_switch_bridge.py` — rewritten to the real
  contract: long-poll (`204` = empty), SSE mode with `connection_id` + heartbeat,
  message dedupe on `payload.message_id`, `list_rooms`, `list_participants`,
  `get_room_history`, bounded timeouts, daemon threads, graceful `stop()`.
- `app/integrations/antigravity/switch_bridge.py` — same dual-shape handling +
  loop prevention.
- Compiles clean; all switch/antigravity integration tests pass.

**Not achieved:** a genuinely human-originated inbound message. `participants` returns
only `scenesteward-clearance`; the admin user is not a room member, so no human post can
be produced through the Gateway without `add_users_to_room` (or the Console UI). All
messages observed in history are agent-authored. The "worker received an event" step
was exercised with a Switch-shaped event in-process, **not** with a live human post.

---

## D. Google Antigravity — NOT VERIFIED

| Piece | State |
|---|---|
| ACP binary `backend/tools/antigravity/agy_acp_server.exe` | Present (55.8 MB), v1.4.5 |
| ACP `initialize` handshake | PASS (`agentInfo`, authMethods oauth-personal / oauth-business / gemini-api-key / agent-platform) |
| ACP `session/new` | **HANGS >120 s**, no response, no stderr (repro: `scratch/test_acp*.py`) |
| OAuth token file `~/.local/state/switch/antigravity-acp/acp_token.json` | Present, `refresh_token` only, **no access token** |
| Console provider enum | Includes `antigravity` (confirmed from `app.asar`) |
| Console readiness | Reports **"CLI not installed"**; Console checks command `antigravity` |
| PATH shim | `antigravity.cmd` → `antigravity-ide.cmd` exists; Console still does not register the provider |
| Room membership | Antigravity is **not** an agent in Core, **not** in the room |

**Root cause of the hang:** most likely expired/absent access token (refresh only) or
Google account quota ("Individual quota reached" seen earlier). This cannot be resolved
without an interactive sign-in — it is a genuine external blocker, not a code defect.

**Code status:** `acp_client.py` (JSON-RPC client) and `switch_bridge.py` (room → ACP →
room, with dedupe and PII minimisation) exist and are unit-tested. They are wired to the
real wire shapes after this session's edits. They have not been proven against a live
Antigravity session.

---

## E. Security invariant review — VERIFIED

- Consent categories independent; `NOT_DISCUSSED` ≠ permission (enforced in worker and
  in `tests/security/test_review_decision_boundary.py`).
- AI/agents cannot write consent, reviews, or decisions; only `agent_runs` rows.
- Human decision only via `POST /api/v1/reviews/{id}/human-decision`, mandatory
  rationale, audit event atomic with the state change, SHA-256 digest.
- Withdrawn consent blocks new uses; no transitive grants.
- Switch membership ≠ SceneSteward project authorization (separate identity, RLS/RBAC).
- Audit append-only (DB trigger).
- Inbound Switch events validated + deduplicated; cannot mutate consent tables.
- No credentials were exposed in the report; `.env` untouched; `.env.example` intact.
- Nothing committed or pushed.

---

## F. Test results (actual, this run)

| Suite | Result |
|---|---|
| `pytest tests` (excluding `test_extraction.py`, which fails to import for an unrelated pre-existing reason) | **305 passed, 1 skipped** |
| `pytest tests/integration/test_switch.py test_switch_multi_agent.py` | pass |
| `pytest tests/integration/test_antigravity_acp.py` | pass (1 skipped: live ACP) |
| `python -m compileall app scripts` | clean |
| `scratch/verify_actual_switch_connection.py` | **13/13 PASS** |
| `scripts/run_real_switch_e2e.py` | worker OK, outbound post **404** (see §C) |

`ruff` is not installed in this environment, so a lint pass could not be produced.

---

## G. Classification

| Component | Classification |
|---|---|
| Actual Switch Core reachable | **VERIFIED** |
| SceneSteward agent registration (DB) | **VERIFIED** |
| SceneSteward room membership | **VERIFIED** |
| Agent auth + ops discovery | **VERIFIED** |
| Post message via agent API | **VERIFIED** |
| Room history / participants read | **VERIFIED** |
| Event poll contract (204/200/SSE) | **VERIFIED** (source + live) |
| Bridge hardened to real contract | **VERIFIED** (code + tests) |
| SceneSteward clearance computation on a Switch-shaped event | **VERIFIED** |
| Genuine human-originated inbound event | **NOT VERIFIED** |
| End-to-end reply posted from worker path | **PARTIAL** (404 on outbound path) |
| Antigravity binary + ACP initialize | **VERIFIED** |
| Antigravity `session/new` / prompt | **NOT VERIFIED** (hangs) |
| Antigravity Console provider recognized | **NOT VERIFIED** ("CLI not installed") |
| Antigravity room participation | **NOT VERIFIED** |
| Multi-agent collaboration | **PARTIAL** (SceneSteward only) |
| Consent enforcement / decision boundary | **VERIFIED** |
| Overall | **PARTIAL — READY WITH DISCLOSED BLOCKERS** |

---

## H. Exact next actions (short)

1. **Fix the outbound 404**: point the worker's reply at `POST /agents/{id}/message`
   with `{room_id, content}` (direct call verified 200); add a regression asserting the
   adapter posts to that path, not a `/rooms/{id}/messages` variant.
2. **Add the human to the room** (`add_users_to_room` op or Console UI), then post the
   required message verbatim:
   `SceneSteward and Antigravity, review footage F-104 from project P-001 for
   documentary trailer use. Explain the consent implications and technical
   implementation considerations.`
   Confirm it arrives via `/agents/{id}/rooms/{rid}/events` (200, not 204) and that the
   worker replies.
3. **Antigravity sign-in**: run `agy_acp_server.exe --login` or Console → Agent
   Providers → Antigravity → Sign in; confirm `acp_token.json` gains an access token;
   retry `initialize` → `session/new` → `session/prompt`.
4. **Register Antigravity in the room** once the Console shows it installed.
5. Re-run this report's checks and flip the NOT VERIFIED rows.

---

## Note on uncommitted work

All Mission 44 changes remain uncommitted on `main`; nothing has been pushed. Working
tree includes the hardened bridge/adapter/listener/worker, Antigravity modules, tests,
and this report.
