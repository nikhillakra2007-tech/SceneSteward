# SceneSteward — Test Database Isolation & Connection Pooling

## 1. Safety Guard Rails for Test Suites

To prevent accidental data destruction or test execution against real databases:
1. **Target Database Name Check**: The test harness aborts immediately unless the connected database name ends with `_test`.
2. **Cloud Host Rejection**: `validate_test_database_url` inspects the DSN host and rejects known cloud host patterns (`*.rds.amazonaws.com`, `*.supabase.co`, `*.database.windows.net`, etc.).
3. **Environment Guard**: `ensure_safe_destructive_environment()` enforces fail-closed execution in production, staging, or unknown environments.

## 2. Connection Pool Isolation Verification

Adversarial tests in `backend/tests/security/test_trust_boundary.py` verify that transaction-scoped RLS context does not leak across connections:

1. **Transaction Commit**:
   - Setting `app.user_id` and committing a transaction does not leave identity in subsequent pool checkouts (`SELECT public.app_current_user_id()` returns `NULL` on new checkout).

2. **Transaction Rollback**:
   - Calling `ROLLBACK` clears local GUCs immediately.

3. **Failed Transaction / Exception**:
   - An unhandled exception or SQL error causing transaction abort cleans context upon connection recycling.

4. **Concurrent Thread Checkouts**:
   - Multiple worker threads simultaneously querying under different user identities (`User A` vs `User B`) verify that each connection's RLS scope remains completely isolated without bleed.
