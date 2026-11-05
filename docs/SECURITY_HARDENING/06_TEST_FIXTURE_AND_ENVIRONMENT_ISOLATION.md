# 06. Test Fixture and Environment Isolation

## Background & Security Invariant
A test suite that interacts with real database schemas carries inherent risk if configuration mistakes or accidental execution occur against non-test environments. Because SceneSteward's test fixtures perform destructive teardown operations (`TRUNCATE ... RESTART IDENTITY CASCADE`) and synchronize database trust secrets, strict, fail-safe isolation is required.

## Hardening Controls Implemented in `backend/tests/conftest.py`

### 1. Pre-Execution Environment Rejection
Before importing application components or initializing engines, the test harness inspects `APP_ENV`:
```python
_orig_env = os.environ.get("APP_ENV", "").lower()
if _orig_env in {"production", "staging"}:
    raise RuntimeError(
        f"CRITICAL SECURITY GUARD: Refusing to execute test suite in APP_ENV={_orig_env!r}! "
        "Test fixtures execute destructive operations (TRUNCATE) and must never target staging or production."
    )
```

### 2. DSN Suffix & Cloud Host Verification
The database URLs provided in `DATABASE_URL_TEST` and `DATABASE_URL_ADMIN` must strictly target databases whose names end with `_test`:
```python
for _label, _check_url in [("DATABASE_URL_TEST", _test_url), ("DATABASE_URL_ADMIN", _admin_url)]:
    _db_part = _check_url.rsplit("/", 1)[-1].split("?")[0]
    if not _db_part.endswith("_test"):
        raise RuntimeError(
            f"CRITICAL SECURITY GUARD: Refusing to execute tests! {_label} target database {_db_part!r} "
            "does not end with '_test'. Tests must target a dedicated disposable test database."
        )
    _lower_url = _check_url.lower()
    for _forbidden_host in [".rds.amazonaws.com", ".supabase.co", ".database.windows.net", "cockroachlabs.cloud"]:
        if _forbidden_host in _lower_url:
            raise RuntimeError(
                f"CRITICAL SECURITY GUARD: Refusing to execute tests against cloud database host {_forbidden_host!r}!"
            )
```

### 3. Active Runtime Database Suffix Assertion
Even if the connection string appears safe, the test harness queries PostgreSQL's engine directly to verify the active connected database:
```python
with _admin_engine.connect() as conn:
    active_db = conn.execute(text("SELECT current_database()")).scalar()
    if not active_db or not str(active_db).endswith("_test"):
        raise RuntimeError(
            f"CRITICAL DATABASE TRUST VIOLATION: Connected database {active_db!r} is not a test database! "
            "Refusing to inspect schema or modify trust configuration."
        )
```

### 4. Secret Synchronization Boundary
Secret synchronization in `private.app_secrets` is only permitted if `settings.app_env == 'test'`. Under no circumstances can running tests modify secrets in staging or production.
