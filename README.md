# SceneSteward — Backend

> **Every story has people behind it.**
> A participant-centred documentary production workspace: recording → proposal →
> comparison → review → discussion → decision → preservation.
> The database is the truth. Switch is a collaboration surface. Humans decide.

A FastAPI + PostgreSQL backend for recording participant choices, detecting
proposals not covered by those choices, coordinating human review — with a full
accountability timeline. **Prototype with synthetic data; not a medical device,
not legal advice, not a compliance certification.**

## Status

Backed and tested end to end: 66 automated tests pass (see docs/TESTING.md).
Live Switch connection is **unverified** (no server in this environment) — see
docs/SWITCH_INTEGRATION.md. AI agents run offline/deterministic by default.

## Quickstart (clean environment)

Prereqs: Python 3.12, PostgreSQL 15+ (or Docker for compose), `uv` recommended.

```powershell
# 1. Create databases (as a Postgres superuser)
$env:PGPASSWORD='postgres'
psql -h 127.0.0.1 -U postgres -c "CREATE ROLE scenesteward LOGIN PASSWORD 'changeme'"
psql -h 127.0.0.1 -U postgres -c "CREATE DATABASE scenesteward OWNER scenesteward"
psql -h 127.0.0.1 -U postgres -c "CREATE DATABASE scenesteward_test OWNER scenesteward"

# 2. Install  (on Windows + OneDrive: use  uv pip install --link-mode=copy ... )
cd backend
uv venv .venv --python 3.12
$env:UV_LINK_MODE='copy'   # avoids "incompatible hardlinks" (os error 396) on OneDrive-backed paths
uv pip install --python .venv -r requirements-dev.txt

# 3. Configure
Copy-Item .env.example .env     # then edit: DATABASE_URL, AUTH_DEV_SECRET, APP_ENCRYPTION_KEY

# 4. Migrate
$env:ALEMBIC_DATABASE_URL='postgresql+psycopg://scenesteward:changeme@127.0.0.1:5432/scenesteward'
.\.venv\Scripts\python.exe -m alembic -c alembic.ini upgrade head

# 5. Seed synthetic demo data ("Beyond the Silence")
.\.venv\Scripts\python.exe scripts\seed_demo.py

# 6. Run
.\.venv\Scripts\python.exe -m uvicorn app.main:app --port 8000 --reload
# → http://127.0.0.1:8000/docs   |   GET /health   |   GET /api/v1/integrations/status

# 7. Demo token (dev provider only)
.\.venv\Scripts\python.exe scripts\dev_token.py --email oscar@example.com --name "Oscar Owner"
```

## Tests

```powershell
$env:DATABASE_URL_TEST='postgresql+psycopg://scenesteward:changeme@127.0.0.1:5432/scenesteward_test'
$env:ALEMBIC_DATABASE_URL=$env:DATABASE_URL_TEST
.\.venv\Scripts\python.exe -m alembic -c alembic.ini upgrade head
.\.venv\Scripts\python.exe -m pytest tests -q        # 66 passed
.\.venv\Scripts\python.exe -m ruff check app scripts tests
```

## Docker

```powershell
docker compose up --build        # postgres + migrate + api on :8000
```
(Not verified on this machine — see docs/TESTING.md and docs/SWITCH_INTEGRATION.md.)

## Documentation

- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — system context, trust boundaries, failure modes
- [docs/DATABASE.md](docs/DATABASE.md) — schema, ER diagram, migrations & rollback limits
- [docs/API.md](docs/API.md) — every endpoint, auth rules, error contract
- [docs/SECURITY.md](docs/SECURITY.md) — controls, RBAC matrix, known gaps
- [docs/SWITCH_INTEGRATION.md](docs/SWITCH_INTEGRATION.md) — real protocol, setup, verification matrix
- [docs/AGENTS.md](docs/AGENTS.md) — the five agents, contracts, data sent, injection posture
- [docs/TESTING.md](docs/TESTING.md) — what the 66 tests prove / don't

## Repo layout

```
backend/app/{api,core,models,schemas,repositories,services,workflows,agents,events,utils}
backend/app/integrations/{switch,storage,ai,notifications}
backend/migrations/   (2 revisions)     backend/tests/ (66)
docs/                                   docker-compose.yml  backend/Dockerfile
```

## Design invariants (do not break)

1. DB is the truth; Switch/AI/frontend are never authoritative for consent.
2. Missing category ⇒ **not agreed** — silence is never consent.
3. Confirmed consent is immutable; corrections are new versions.
4. Agents never approve; every proposed use gets a human review.
5. A communication draft is never "sent" without explicit human approval.
6. Synthetic data only until the gaps in SECURITY.md are closed.
