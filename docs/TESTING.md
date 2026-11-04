# SceneSteward — Testing

**61 tests, all passing** (verified 2026-11-04, PostgreSQL 18, Python 3.12):

```
tests/unit         10  comparison engine (mapping, outcomes, injection)
tests/agents       11  5 agents × output validation, injection, unsupported claims
tests/integration  28  auth(9) · documents(8) · migrations(4) · switch(7)
tests/security     10  RBAC, cross-project isolation, last-owner, viewer timeline
tests/e2e           2  "Beyond the Silence" full flow + viewer denial
```

## What the suite proves (and what it doesn't)

**Proven against a real PostgreSQL test DB** (`scenesteward_test`, migrated to head `b3f9c21a7d44`):
- Scenario for every role × key endpoint; cross-project and linked-participant isolation;
  encrypted contacts readable only by owner/producer/care_lead/self.
- Consent versioning: create → confirm (care_lead) → supersede on re-confirm;
  confirmed records immutable via trigger; audit trail append-only via trigger;
  FK / UNIQUE / CHECK violations fail.
- The flagship e2e: proposed use (sensitive excerpt → trailer + AI voice reconstruction)
  ⇒ outcome `NEEDS_DISCUSSION`; promotional_clips + voice_cloning detected; interview
  agreement recognised; **consent record untouched**; review + `unresolved_permission`
  + `review` tasks created; 5/5 agent runs succeeded; draft communication stays draft;
  human decision recorded (producer) → proposed use `awaiting_participant_discussion`;
  decided reviews are immutable; viewer forbidden end-to-end.
- Documents: signed-URL round trip (PUT→complete→download), magic-byte sniffing,
  extension/size caps, traversal rejection, editor denied.
- Switch: mock adapter (verified flag honesty), room reuse, send-to-unknown-room fails
  closed, inbound dedupe (`skipped_duplicate`), unmapped room recorded, no code path
  from inbound events to consent tables.

**Not covered / not guaranteed here:**
- Live Switch server (none available) — mock only; see SWITCH_INTEGRATION.md.
- Live Supabase JWKS verification (no project) — dev HS256 tested; JWKS path is implemented
  but exercised only via code review + unit decode logic, not against a real tenant.
- Live Anthropic API — offline deterministic agents tested; provider path never called in tests.
- Concurrency stress beyond integrity tests (single-writer paths verified; no load test).
- Frontend behaviour. No browser tests exist.

## Running the tests

```powershell
cd backend
python -m venv .venv ; .\.venv\Scripts\Activate.ps1
uv pip install --python .venv -r requirements-dev.txt   # or pip install -r requirements-dev.txt
# create test DB once:
$env:PGPASSWORD='postgres'
psql -h 127.0.0.1 -U postgres -c "CREATE DATABASE scenesteward_test OWNER scenesteward"
psql -h 127.0.0.1 -U postgres -c "CREATE ROLE scenesteward LOGIN PASSWORD '<pw>'"   # if missing
$env:DATABASE_URL_TEST='postgresql+psycopg://scenesteward:<pw>@127.0.0.1:5432/scenesteward_test'
alembic -c alembic.ini upgrade head     # with ALEMBIC_DATABASE_URL set to the TEST db
pytest tests -v
```

`conftest.py` **hard-aborts** unless the effective database name ends in `_test` —
it is impossible to run the suite against the dev database by accident.

Every test truncates all tables before running (fresh, isolated state, same process
connection pool) — no test order dependence.

## Layout

```
tests/conftest.py            db guard, truncation, factories (make_user/project/member, auth_headers)
tests/unit/                  pure logic, no DB
tests/agents/                offline agent contract tests
tests/integration/            real DB through HTTP (TestClient)
tests/security/               RBAC matrix
tests/e2e/                    Beyond the Silence
```

## Adding tests

- New endpoint ⇒ happy path + one denial per role involved + isolation probe.
- New invariant on consent/audit ⇒ add a trigger test, not only an API test.
- Never seed with real personal data.

## CI sketch

```yaml
services: postgres:18-alpine with POSTGRES_USER=scenesteward POSTGRES_PASSWORD=test
steps: install → alembic upgrade head (test db) → ruff check → pytest --junitxml
```
