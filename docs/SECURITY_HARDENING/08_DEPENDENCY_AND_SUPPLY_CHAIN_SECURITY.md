# 08. Dependency and Supply Chain Security

## Dependency Management & Integrity

### 1. Python Backend Dependencies (`backend/pyproject.toml`)
- Modern, clean dependency specification with explicit version bounds for core frameworks:
  - `fastapi>=0.115.0`
  - `sqlalchemy>=2.0.35`
  - `psycopg[binary]>=3.2.0`
  - `pydantic>=2.9.0`
  - `pydantic-settings>=2.5.0`
  - `cryptography>=43.0.0`
  - `pyjwt[crypto]>=2.9.0`
- Zero deprecated packages (e.g. `passlib`, `databases`).

### 2. Next.js Frontend Dependencies (`frontend/package.json`)
- Fixed dependency versions:
  - `next`: `14.2.15`
  - `react`: `^18`
  - `lucide-react`: `^0.460.0`
  - `tailwind-merge`: `^2.5.4`
- Locked via `frontend/package-lock.json` and installed via deterministic `npm ci`.

### 3. Base Container Images
- Base images specify explicit OS release codenames:
  - `python:3.12-slim-bookworm` (Debian Bookworm minimal base).
  - `postgres:16-alpine` (Minimal Alpine container for CI).
- Non-root user `scenesteward:scenesteward` configured for container runtime execution.
