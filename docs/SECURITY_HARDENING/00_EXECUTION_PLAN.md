# 00. Execution Plan — Advanced CI/CD Security Hardening & Database Trust-Boundary Review

## Executive Mission Context
- **Target Repository**: `https://github.com/nikhillakra2007-tech/SceneSteward`
- **Initial Baseline SHA**: `b808f00a7613c9de38ca13997fc0277627639d5b`
- **Single Working Branch**: `security/ci-database-trust-hardening`
- **Objective**: Execute an advanced security hardening campaign covering GitHub Actions workflow permissions, supply-chain security, database identity trust boundaries (`DATABASE_IDENTITY_SECRET`), PostgreSQL RLS enforcement, test fixture isolation, connection pool safety, and automated security regression prevention.

## Git Rules & Protocol
1. Exactly ONE working branch: `security/ci-database-trust-hardening` (branched from latest verified `main` at `b808f00`).
2. Exactly ONE Pull Request targeting `main`.
3. Suggested Title: `Security: Harden CI/CD and Database Identity Trust Boundaries`.
4. All corrections, tests, and documentation committed exclusively to this branch.
5. Merge only when all required GitHub Actions checks pass green on the PR commit.
6. Synchronize `develop` with merged `main` ensuring exact commit parity.

## Core Security Workstreams
- **WS1: Test Fixture & Environment Isolation (`conftest.py`)**:
  - Enforce strict environment guards blocking test execution if `APP_ENV` is `production` or `staging`.
  - Validate database connection strings (`_test_url` AND `_admin_url`) ensuring both end with `_test`.
  - Query PostgreSQL's `SELECT current_database()` to cryptographically verify target database is a dedicated test database before synchronizing `private.app_secrets`.
  - Prohibit targeting external cloud databases.
- **WS2: Database Identity Secret Lifecycle & Migration Hardening (`e1f2a3b4c5d6`)**:
  - Forbid static fallback secrets in production environments.
  - Require explicit random secrets when `APP_ENV=production`.
  - Guard existing secrets: `ON CONFLICT (key_name) DO NOTHING` prevents clobbering active secrets during migration runs.
- **WS3: GitHub Actions Least-Privilege & Workflow Hardening (`ci.yml`)**:
  - Define top-level least-privilege permissions: `permissions: contents: read`.
  - Ensure zero access to production secrets on untrusted PRs.
  - Verify static argument passing and zero shell script injection vulnerabilities.
- **WS4: Container & Build Context Security (`.dockerignore`)**:
  - Exclude frontend `node_modules`, `.next`, cache files, and local logs from repository-root Docker build context.
- **WS5: Database Identity Boundary & Connection Pool Hygiene (`database.py`)**:
  - Ensure transaction-scoped identity variables cannot leak across pooled connections.
  - Add pool checkin/reset handlers to flush session state.
- **WS6: Security Regression Tests & Invariant Verification**:
  - Add automated test cases for connection pool isolation, malformed UUID handling in `app_current_user_id()`, signature tampering, and environment guard enforcement.
