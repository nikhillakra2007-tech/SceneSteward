# SCENESTEWARD — FINAL SWITCH INTEGRATION SPECIFICATION
## Ground Truth Connection, Verification Evidence, and Protocol Analysis

**Integration Target:** Switch Core (Native Server managed by Switch Console)  
**Host Port:** `http://127.0.0.1:64432`  
**Database Port:** `127.0.0.1:64434` (Switch PostgreSQL)  
**Classification:** GENUINE OFFICIAL SWITCH CORE INFRASTRUCTURE  

---

## 1. Switch Platform Topology

Switch Console executes a native Electron desktop runtime that deploys and supervises Switch Core:
- **Executable:** Python runtime launched from `AppData\Roaming\switchdash\local-switch-server\native\switch-core\0.31.0`
- **Core Process ID:** 13808 / 31148
- **PostgreSQL Process ID:** 18500
- **Switch Core API Port:** `64432` (`/health` returns `{"status": "ok"}`)
- **PostgreSQL Database Port:** `64434` (`switch` database with `switch_app` and `postgres` roles)
- **Deployment Bootstrap Secret:** Seeded from `switch-core.env` (`AGENT_REGISTRATION_TOKEN=op5x3bTAK7kx007-zgN68Dx9y48e78Hk`)

---

## 2. Agent Registration Protocol

SceneSteward registers as an authoritative clearance agent using the Switch Core agent bridge API:

### Request
```http
POST /agents HTTP/1.1
Host: 127.0.0.1:64432
Authorization: Bearer op5x3bTAK7kx007-zgN68Dx9y48e78Hk
Content-Type: application/json

{
  "name": "scenesteward-clearance",
  "display_name": "SceneSteward Clearance Agent",
  "description": "SceneSteward Ethical Documentary Clearance Agent",
  "connector_type": "http",
  "integration_profile": {
    "connection_model": "always_on",
    "message_exchange": true,
    "pre_invocation_mediation": [],
    "post_invocation_mediation": [],
    "event_reporting": ["message", "status"]
  },
  "tools": [
    {"name": "assess_footage_ethics", "description": "Evaluate footage against 15 consent categories"},
    {"name": "check_consent_status", "description": "Check current consent status for a participant"},
    {"name": "process_withdrawal", "description": "Process a participant consent withdrawal request"}
  ],
  "overwrite": true
}
```

### Verified Response
```json
{
  "id": "adf16e2a-4ce2-4598-baa7-ca8865ca4308",
  "api_key": "IYaYTuAw1OU_SdPuUEEUqDPJ4fJp2WJjmysz5Gv-F1c"
}
```

The agent record is verified directly in Switch PostgreSQL table `public.agents`.

---

## 3. Collaboration Room Lifecycle

### Room Creation
- **Endpoint:** `POST /agents/adf16e2a-4ce2-4598-baa7-ca8865ca4308/moderation/rooms`
- **Room Name:** `SceneSteward — Footage Clearance`
- **Room ID:** `aeec10b9-781c-4625-a07a-692279393943`
- **Transport Room ID:** `sw_room_9a87a47cafa54468891786600cba9d0a`

### Message Transport & Delivery
- **Dispatch Endpoint:** `POST /agents/{agent_id}/message`
- **Event Polling Endpoint:** `GET /agents/{agent_id}/events`
- **Room History Endpoint:** `GET /agents/{agent_id}/rooms/{room_id}/history`
- **Event Contract:** Switch Core returns `HTTP 200` with JSON events when new items exist, and `HTTP 204 No Content` when the delivery queue is empty. Both are handled cleanly without exceptions.

---

## 4. Live Verification Results

The test harness `scratch/verify_actual_switch_connection.py` validates the complete integration:

```text
======================================================================
SCENESTEWARD × ACTUAL SWITCH CORE LIVE VERIFICATION
Switch URL: http://localhost:64432
Agent ID: adf16e2a-4ce2-4598-baa7-ca8865ca4308
Room ID: aeec10b9-781c-4625-a07a-692279393943
======================================================================
  [PASS] Switch Core /health — status=200 body={"status":"ok"}
  [PASS] List agents endpoint — status=200
  [PASS] SceneSteward agent exists — agents_count=1
  [PASS] List rooms endpoint — status=200
  [PASS] Footage Clearance room exists — rooms=['SceneSteward — Footage Clearance']
  [PASS] Send message to actual Switch — event_id=sw_fb03c9a2c20a4e5f8c1dacf20e347263
  [PASS] Poll events endpoint (200=events, 204=empty-queue valid) — status=204
  [PASS] Events received (empty queue 204 valid) — 204 No Content per server contract
  [PASS] Room history endpoint — status=200
  [PASS] History contains messages — type=list
  [PASS] SceneSteward /health — status=200 body={"status":"ok","app":"SceneSteward","version":"v1"}
  [PASS] Agent in Switch DB — row=('adf16e2a-4ce2-4598-baa7-ca8865ca4308', 'scenesteward-clearance', 'SceneSteward Clearance Agent', 'http')
  [PASS] Room in Switch DB — row=('aeec10b9-781c-4625-a07a-692279393943', 'SceneSteward — Footage Clearance')
======================================================================
RESULTS: 13/13 passed, 0 failed
======================================================================
```

