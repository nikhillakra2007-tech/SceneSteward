# SceneSteward — Continuation / Progress

**State (Nov 2026): backend built, tested, documented, uncommitted-then-committed.**
61 tests pass; ruff clean; migrations apply and roll back cleanly.

## Done
- Repo + git init; `.gitignore` (env, venv, `backend/var/`).
- Backend app: FastAPI, 19 tables + triggers, Alembic migrations
  (`65898c97090c` schema, `b3f9c21a7d44` append-only audit + immutable confirmed consent).
- Auth: dev HS256 tokens + Supabase JWKS verification path (unverified live).
- RBAC for 8 roles; cross-project/participant isolation; contacts Fernet-encrypted.
- Full API (44 paths) see docs/API.md; interactive OpenAPI at `/docs`.
- Deterministic comparison engine (ENGINE_VERSION 1.0.0) — 10 unit tests.
- 5 agents (offline deterministic default, Anthropic provider wired) — 11 agent tests.
- Document pipeline: HMAC-signed upload/download URLs, magic-byte sniffing,
  PDF/TXT/MD/DOCX extraction with page refs, extraction → UNCONFIRMED consent proposal.
- Switch adapter (test + real agent-protocol HTTP adapter) + SSE listener + retry
  sweeper + room linking; **live connection UNVERIFIED** (see SWITCH_INTEGRATION.md).
- 'Beyond the Silence' e2e passes (NEEDS_DISCUSSION; consent untouched; draft stays draft).
- Ops: Dockerfile, docker-compose.yml (db+migrate+app), requirements(-dev).txt pinned.
- Docs: ARCHITECTURE, DATABASE (ER + rollback limits), API, SECURITY, SWITCH_INTEGRATION,
  AGENTS, TESTING, README.
- Demo: `scripts/seed_demo.py` (synthetic "Beyond the Silence", 6 users), `dev_token.py`,
  `switch_listener.py`, `switch_retry.py`.

## Not done / not verified (explicit)
- Switch live connection — no server/credentials here; adapter + mocks only.
- Supabase JWKS path — implemented, never run against a real tenant.
- Anthropic provider — never called (offline mode is the default and is tested).
- Docker image never built (Docker unavailable on this machine).
- `/docs` reload security, load/concurrency testing, pen test, RLS — see SECURITY.md "NOT done".
- No git tags/releases yet.

## How to resume
```powershell
cd backend; .\.venv\Scripts\Activate.ps1
pytest tests -q            # 61 passed
uvicorn app.main:app --port 8000 --reload
python scripts/seed_demo.py
python scripts/dev_token.py --email oscar@example.com --name "Oscar Owner"
```
