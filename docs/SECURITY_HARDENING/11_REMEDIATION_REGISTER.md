# 11. Remediation Register

| ID | Vulnerability / Deficiency | Severity | Affected Component | Status | Verification |
|---|---|---|---|---|---|
| **REM-01** | Default `GITHUB_TOKEN` had excessive write permissions in CI | Medium | `.github/workflows/ci.yml` | **REMEDIATED** | Added top-level `permissions: contents: read` |
| **REM-02** | Test runner lacked safeguards against running against production/staging DB | Critical | `backend/tests/conftest.py` | **REMEDIATED** | Added pre-run environment guard and `*_test` DSN checks |
| **REM-03** | Database identity migration could overwrite active secret via `ON CONFLICT DO UPDATE` | High | `backend/migrations/versions/e1f2a3b4c5d6...py` | **REMEDIATED** | Changed to `DO NOTHING` and enforced production entropy guard |
| **REM-04** | Test fixture secret synchronization lacked DB name verification | High | `backend/tests/conftest.py` | **REMEDIATED** | Added `SELECT current_database()` assertion before secret sync |
| **REM-05** | Backend Docker build context included frontend node_modules and `.next` caches | Low | `.dockerignore` | **REMEDIATED** | Added explicit excludes for frontend artifacts |
| **REM-06** | Absence of automated tests for tampered identity signatures and role privilege bounds | Medium | `backend/tests/security/test_trust_boundary.py` | **REMEDIATED** | Added 5 adversarial regression tests |
