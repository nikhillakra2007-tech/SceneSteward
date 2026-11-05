# 06. GitHub Actions Security Review

## Security Review Checklist
1. **Least Privilege Permissions**:
   - `ci.yml` uses default read-only permissions for repository checkouts.
   - Zero write permissions to contents or packages granted to untrusted jobs.
2. **Secrets Handling**:
   - No production secrets or live credentials are used in CI.
   - CI uses ephemeral, test-only secrets (`ci_database_identity_secret_2026_test_only`, `app_test_password`).
   - Zero hardcoded production keys in workflow definitions.
3. **Action Pinning**:
   - Workflows use official GitHub Actions (`actions/checkout@v4`, `actions/setup-python@v5`, `actions/setup-node@v4`).
4. **Isolation**:
   - Database tests execute against an ephemeral PostgreSQL 16 service container in the runner network namespace.
   - Tests run strictly under least-privileged role `scenesteward_app` (`NOBYPASSRLS`).
   - RLS cannot be bypassed during test execution.
