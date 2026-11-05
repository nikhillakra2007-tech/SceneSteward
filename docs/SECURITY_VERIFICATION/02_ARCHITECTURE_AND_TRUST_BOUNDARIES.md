# SceneSteward — Architecture & Trust Boundaries

## 1. Trust Boundary Model

SceneSteward separates system components into distinct trust zones:

```
[Untrusted Clients] (Web Frontend, External API Consumers)
        │
        ▼ (JWT Bearer Token: Supabase / Dev)
[FastAPI Application Layer] (Runtime Role: scenesteward_app)
        │
        │ Sets transaction-local GUCs:
        │ SELECT set_config('app.user_id', <uid>, true),
        │        set_config('app.user_sig', HMAC(uid, SECRET), true)
        ▼
[PostgreSQL Database Engine] (Enforces RLS, NOBYPASSRLS)
        │
        ├── public schema (Tables protected by RLS: projects, participants, etc.)
        ├── public.app_current_user_id() (SECURITY DEFINER with fixed search_path)
        ├── public.app_verify_trust_handshake() (SECURITY DEFINER with fixed search_path)
        │
        └── private schema (Strict isolation: USAGE revoked from scenesteward_app)
             └── private.app_secrets (Stores HMAC secret; owned by scenesteward)
```

## 2. Cryptographic Identity Signature

To prevent connection pooling leakage or SQL injection impersonation:
1. Every authenticated user request computes `HMAC_SHA256(user_id, DATABASE_IDENTITY_SECRET)`.
2. The FastAPI connection listener injects both `app.user_id` and `app.user_sig` as transaction-local parameters (`is_local = true`).
3. PostgreSQL Row-Level Security policies invoke `public.app_current_user_id()`.
4. `app_current_user_id()` executes under `SECURITY DEFINER` with fixed `search_path = public, pg_catalog, pg_temp`, reads `private.app_secrets.secret_val`, re-computes `HMAC_SHA256(user_id, secret)`, and compares it against `app.user_sig`.
5. If the signature is absent, malformed, or does not match, `app_current_user_id()` returns `NULL`, causing RLS to fail closed (0 rows returned).

## 3. Cryptographic Handshake at Lifespan

To prevent silent secret mismatch between the application and database, FastAPI startup verifies trust:
- Calls `public.app_verify_trust_handshake(p_nonce, p_sig)`.
- Recomputed inside PostgreSQL without returning or exposing the secret.
- If the handshake fails in `production` or `staging`, the application aborts startup immediately with a `RuntimeError`.
