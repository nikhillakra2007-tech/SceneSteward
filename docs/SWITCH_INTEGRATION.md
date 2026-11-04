# SceneSteward ↔ Switch Integration

**Status: UNVERIFIED (no live Switch server in this environment).**
The adapter is implemented and unit/mock tested. The connection has never been
exercised against a running Switch. Everything below is derived from the Switch
source at `C:\Users\nikhi\OneDrive\Desktop\coding\SWITCH\switch` (Agent Switch,
Apache-2.0 + Commons Clause, by sandbox-quantum).

## What Switch is

Agent Switch is a self-hosted layer that puts AI teammates into Slack/Teams/Discord/
Telegram/Mattermost. Each channel becomes a "room" where humans and agents work from
the same conversation. Switch is **never** an authority for consent; it carries
context and notifications only.

Integration model (verified in Switch source, `docs/official/internals/agent-protocol.md`
and `core/switch_core/bridges/agent/`):

- Agents connect **outbound**: SSE stream down (`GET /agents/{id}/events`) or a newer
  WebSocket (`/agents/{id}/connection/ws`, rev 8, replacing SSE over a compatibility
  window). Heartbeat `POST /agents/{id}/connection/beat` every 2s, TTL 6s.
- All other calls are plain HTTP with `Authorization: Bearer <agent API key>`:
  `GET /agents/{id}/ops` (discovery), `POST /agents/{id}/ops/{op}` (arguments as the
  unwrapped body, requires `X-Switch-Connection-Id` of an open connection),
  `POST /agents/{id}/message` `{room_id, content}` (no connection needed),
  `POST /agents/{id}/ops/create_room` (connection required).
- Registration: `POST /agents/register-known` with a **registration token**
  (`AGENT_REGISTRATION_TOKEN` bootstrap from the server `.env`, or a personal
  registration key minted in the Gateway → API Keys). Returns the agent API key
  **once**. The agent inherits its owner's permissions — register it under a
  dedicated, least-privilege Gateway user.
- Rooms are Postgres rows bound 1:1 to a chat channel (or internal-only). Least
  privilege: SceneSteward uses a **project room** and optional 1:1
  **participant-review rooms** (`switch_room_links`, UNIQUE per scope).
- Inbound events: only by holding the SSE/WS connection. **Switch has no outbound
  webhook mechanism for external services.** Messages from Switch cannot mutate
  SceneSteward state; they are recorded in `integration_events` for humans to read.

## What SceneSteward does with it

- `scripts/switch_listener.py` — holds the SSE connection, validates each event
  (type + sequence/event_id), deduplicates on `(integration_name, external_event_id)`,
  correlates `room_id` → project/participant via `switch_room_links`, stores only a
  minimal `payload_summary` (type, room_id, mapped ids). It **cannot** write consent,
  reviews, or decisions (enforced by code review and by `test_switch.py`).
- Analysis workflow sends a terse, structured review context to the linked room:
  proposed_use_id, outcome, missing/declined category names, and a reminder that
  decisions happen in SceneSteward. No participant data beyond the use reference.
- Delivery failures are recorded (`integration_events.processing_status='failed'`),
  retried by `scripts/switch_retry.py` (≤3 attempts), then parked as `dead_letter`
  with an `integration_failure` task. Nothing about consent is ever retried into
  existence or blocked.

## Setup (when you have a Switch server)

1. Deploy Switch (see Switch docs `deploy/self-host.md`; locally: `just up && just migrate && just run`).
2. In Gateway → API Keys, mint a personal registration key **as a dedicated
   least-privilege user** (not the admin).
3. Register SceneSteward:
   ```bash
   curl -X POST $SWITCH_BASE_URL/agents/register-known \
     -H "Authorization: Bearer $SWITCH_REGISTRATION_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"agent_type":"custom","name":"scenesteward","description":"SceneSteward review context relay"}'
   # → {"id":"agent:...","api_key":"..."}   (shown once)
   ```
4. `backend/.env`:
   ```
   SWITCH_ADAPTER=http
   SWITCH_BASE_URL=http://127.0.0.1:8000
   SWITCH_AGENT_ID=agent:<id-from-step-3>
   SWITCH_API_KEY=<api_key-from-step-3>
   SWITCH_REGISTRATION_TOKEN=<registration-key>   # only for step 3
   ```
5. Verify: `GET /api/v1/integrations/status` → switch must show
   `configured_verified` (it probes `/health` + authenticated ops discovery).
   **Env vars alone never produce `configured_verified`.**
6. Link rooms: `POST /api/v1/integrations/switch/projects/{id}/rooms`
   `{scope:"participant", participant_id, connection_id}` — room creation needs an
   open agent connection (`scripts/switch_listener.py` provides one).
7. Run the listener: `python scripts/switch_listener.py`.
8. Retry sweep (cron): `python scripts/switch_retry.py`.

## Verification matrix

| Check | How | Result in this environment |
|---|---|---|
| Valid credentials → verified | live probe | **Not executed — no server/creds** |
| Invalid credentials → failed_authentication | live probe | Not executed |
| Missing credentials → missing_credentials | code path | Yes (status endpoint) |
| Timeout handling | adapter timeout 10s | Mock tests only |
| Room create / reuse | ops call with connection | Mock tests only |
| Event delivery | `/agents/{id}/message` | Mock tests only |
| Incoming event validation | listener | Unit-tested (mock raw events) |
| Duplicate delivery → skipped_duplicate | UNIQUE constraint | Unit-tested |
| 403/401 → listener stops (no auth storm) | listener | Code reviewed, not run |
| Outbound webhooks | n/a — do not exist in Switch | Documented |

## Limitations (Switch-imposed)

- Single-process switch-core; no horizontal scale.
- Gateway API is a first-party UI contract (cookie JWT, human login) — **not** a
  service-account path; SceneSteward never uses it.
- `task_*` frames are explicitly "not ready for use" — SceneSteward ignores them.
- WebSocket transport is rev-8 "meant to replace" SSE; SSE is kept for compatibility;
  either way, the contract here is wrapped behind `SwitchAdapter` — an easy swap.
- Room membership: verify the Switch room contains only intended members; SceneSteward
  does not (and cannot) police Switch-side membership — least privilege must be
  enforced by the Switch admin when creating rooms.
- Rate limits: Switch has open-gate pacing (429 + Retry-After) and a refusal breaker;
  SceneSteward treats 429 as transient and surfaces it; it never loops on 429.

## What would close the gap

Run steps 1–8 against a staging Switch, record results here, and re-label the two
STATUS lines at the top. Until then: **live connection unverified; do not rely on
Switch for delivery of anything that must arrive.**
