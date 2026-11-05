# SceneSteward — Staging & Production Lifecycle Protection

## 1. Lifecycle Guard Architecture

A centralized module `backend/app/core/lifecycle_guards.py` intercepts all destructive operations:

```python
def ensure_safe_destructive_environment(
    settings: Settings | None = None,
    operation_name: str = "destructive database operation",
    target_database: str | None = None,
    allow_explicit_override: bool = False,
    override_token: str | None = None,
) -> None:
```

### Prohibited Operations in Restricted Environments
The following scripts and routines are protected:
- `backend/scripts/verify_documentary_lifecycle.py`: Drops and truncates test tables.
- `backend/scripts/restore_database.py`: Overwrites active tables from backup archives.
- `backend/scripts/seed_demo.py`: Injects synthetic test data.
- `backend/scripts/verify_isolated_restore.py`: Spins up disposable test schemas.
- Pytest `conftest.py` test harness: Truncates all tables on fixture setup.

## 2. Fail-Closed Rules

1. **Production & Staging**: Blocked by default with `RuntimeError: CRITICAL LIFECYCLE GUARD: Refusing ... Destructive operations are strictly prohibited in PRODUCTION/STAGING environment`.
2. **Missing Environment**: If `APP_ENV` is unset or empty, fails closed immediately.
3. **Unknown Environment**: If `APP_ENV` is not in `{'test', 'development', 'dev', 'local'}`, fails closed.
4. **Non-Test Database**: If `target_database` does not end with `_test` during test operations, fails closed.
5. **Explicit Override Token**: In emergency disaster recovery, requires passing both `--confirm-destructive-override` AND setting `CONFIRM_DESTRUCTIVE_OVERRIDE_PRODUCTION` or `CONFIRM_DESTRUCTIVE_OVERRIDE_STAGING`.
