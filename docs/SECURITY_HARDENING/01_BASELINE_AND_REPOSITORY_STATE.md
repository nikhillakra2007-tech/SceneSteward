# 01. Baseline and Repository State

## Mission & Scope
- **Repository**: `https://github.com/nikhillakra2007-tech/SceneSteward`
- **Initial Baseline Commit**: `b808f00a7613c9de38ca13997fc0277627639d5b` (Merged PR #26).
- **Working Branch**: `security/ci-database-trust-hardening` (branched directly from `main` at `b808f00`).
- **Target Branch**: `main`.
- **Git Policy Enforced**: Exactly ONE working branch, exactly ONE Pull Request.

## Remote & Local Alignment Preflight
Prior to initiating hardening activities, the repository state was inspected and verified:
- `git fetch origin`
- Local `main`: `b808f00a7613c9de38ca13997fc0277627639d5b`
- Remote `origin/main`: `b808f00a7613c9de38ca13997fc0277627639d5b`
- Remote `origin/develop`: `b808f00a7613c9de38ca13997fc0277627639d5b`
Both `main` and `develop` were verified to be in exact commit parity.

## Workspace Cleanliness
- Working tree at baseline was clean.
- Existing CI workflows: `.github/workflows/ci.yml` with 3 active jobs:
  1. `backend-test` (Python 3.12, PostgreSQL 16 service container, Alembic migration runner, pytest, ruff, safety check).
  2. `frontend-build` (Node 20, npm ci, linting, Next.js production build).
  3. `docker-validation` (Docker build preflight, compose validation).

## Scope of Hardening
1. Least privilege permissions on CI/CD workflows (`permissions: contents: read`).
2. Absolute test fixture database isolation (prevention of destructive operations against staging or production databases).
3. Secret lifecycle protection in database migrations (preventing overwrite of active production identity secrets).
4. Prevention of frontend artifacts leaking into Docker build context.
5. Adversarial security test coverage verifying identity signature boundaries and role restrictions.
