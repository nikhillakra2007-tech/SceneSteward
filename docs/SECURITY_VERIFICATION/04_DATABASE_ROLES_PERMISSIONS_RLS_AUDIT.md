# SceneSteward — Database Roles, Permissions & RLS Audit

## 1. PostgreSQL Database Roles

| Role Name | Superuser | Inherit | Create DB | Create Role | Bypass RLS | Target Purpose |
|:---|:---:|:---:|:---:|:---:|:---:|:---|
| `postgres` | Yes | Yes | Yes | Yes | Yes | Administrative host root (never used by app) |
| `scenesteward` | No | No | No | No | Yes (table owner) | Schema owner; migrations only |
| `scenesteward_app` | **No** | **No** | **No** | **No** | **No** (`NOBYPASSRLS`) | Application runtime role; all queries subject to RLS |
| `scenesteward_readonly` | **No** | **No** | **No** | **No** | **No** (`NOBYPASSRLS`) | Read-only analytics; all queries subject to RLS |

## 2. Privilege Audit & Negative Testing

Live SQL inspection against PostgreSQL confirmed the following:

```sql
SELECT has_table_privilege('scenesteward_app', 'private.app_secrets', 'select'); -- Returns FALSE
SELECT has_table_privilege('scenesteward_app', 'private.app_secrets', 'insert'); -- Returns FALSE
SELECT has_table_privilege('scenesteward_app', 'private.app_secrets', 'update'); -- Returns FALSE
SELECT has_table_privilege('scenesteward_app', 'private.app_secrets', 'delete'); -- Returns FALSE
SELECT has_schema_privilege('scenesteward_app', 'private', 'usage');              -- Returns FALSE
```

When an attacker executing arbitrary SQL under `scenesteward_app` attempts:
```sql
SELECT * FROM private.app_secrets;
```
PostgreSQL aborts the statement with:
```
ERROR: 42501: permission denied for schema private
```

## 3. Function Security Audit

1. **`public.app_current_user_id()`**:
   - `SECURITY DEFINER`
   - Fixed `search_path = public, pg_catalog, pg_temp`
   - Validates HMAC signature against `private.app_secrets`.
   - Never exposes the secret or returns secret text.
   - Returns `uuid` of the verified user, or `NULL` on any failure.

2. **`public.app_verify_trust_handshake(p_nonce text, p_sig text)`**:
   - `SECURITY DEFINER`
   - Fixed `search_path = public, pg_catalog, pg_temp`
   - `REVOKE ALL ON FUNCTION public.app_verify_trust_handshake(text, text) FROM PUBLIC;`
   - `GRANT EXECUTE ON FUNCTION public.app_verify_trust_handshake(text, text) TO scenesteward_app, scenesteward;`
   - Returns `boolean` (`TRUE` if HMAC matches, `FALSE` otherwise).
   - Safe against SQL injection and parameter manipulation.
