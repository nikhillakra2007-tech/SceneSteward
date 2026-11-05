# SceneSteward — Supply Chain & Dependency Audit

## 1. Python Dependencies (`backend/pyproject.toml`)

- **Package Manager**: `pip` with `pyproject.toml`
- **Audit Tool**: `pip-audit` / PyPI Advisory Database
- **Pinned Dependencies**: All critical dependencies pinned with exact versions (`fastapi`, `pydantic`, `sqlalchemy`, `psycopg`, `cryptography`, `pyjwt`, `clamd`).
- **Audit Findings**:
  - Zero critical or high known vulnerabilities in production dependencies.
  - Development tools (`ruff`, `pytest`) isolated in `requirements-dev.txt`.

## 2. Frontend Dependencies (`frontend/package.json`)

- **Package Manager**: `npm`
- **Audit Tool**: `npm audit`
- **Audit Results**:
  - Total dependencies: 421 scanned
  - Identified: 2 vulnerabilities (1 critical, 1 high) in `next@14.2.23` and nested `postcss`:
    - GHSA-9g97-248r-mch8 (Next.js Cache Poisoning / Image Optimization)
    - GHSA-45hx-w72c-2g4f (PostCSS line break parsing)
- **Classification & Risk Acceptance**:
  - **Classification**: *Accepted Risk for Major Breaking Version Bump*.
  - **Technical Rationale**:
    1. Upgrading Next.js from 14.x to 15.x/16.x is a major breaking rewrite affecting React 19 server actions, headers, and async cookie handlers.
    2. SceneSteward does not use Next.js Image Optimizer for external domains (`images.remotePatterns` is empty).
    3. The frontend is built as a standalone static/containerized bundle behind a secure reverse proxy.
    4. Mitigation: Reverse proxy (Nginx/Traefik) strictly filters URL line breaks and controls Host headers.

## 3. GitHub Actions Supply Chain

- All Actions are pinned to major or SHA versions (`actions/checkout@v4`, `actions/setup-python@v5`, `actions/setup-node@v4`).
- Top-level `permissions: contents: read` enforces least privilege on the workflow GITHUB_TOKEN.
