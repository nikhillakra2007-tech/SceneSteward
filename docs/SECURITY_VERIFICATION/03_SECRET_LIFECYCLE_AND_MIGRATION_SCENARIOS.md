# SceneSteward — Secret Lifecycle & Migration Scenarios

## 1. Overview of Identity Secret Lifecycle

The PostgreSQL HMAC trust boundary relies on `DATABASE_IDENTITY_SECRET`. This secret must remain synchronized between the application process environment and PostgreSQL table `private.app_secrets`.

### Immutability of Business Data Under Secret Rotation
Crucially, SceneSteward's business data model does NOT store signatures or identity secrets in records:
- `projects`, `participants`, `consent_records`, `consent_choices`, `reviews`, and `audit_events` store standard foreign keys (`user_id`, `created_by`, `decided_by`, `actor_id`).
- Cryptographic signatures (`app.user_sig`, `app.system_sig`) are ephemeral and live ONLY for the duration of a single database transaction.
- Therefore, rotating `DATABASE_IDENTITY_SECRET` does NOT invalidate historical consent records, audit trails, or project data.

---

## 2. Evaluation of Migration Scenarios (A, B, C, D, E)

### Scenario A: Fresh Installation
- **Condition**: `private.app_secrets` is empty or being created for the first time.
- **Migration Behavior**: Reads `DATABASE_IDENTITY_SECRET` from environment. In production/staging, enforces `>= 32 characters` and rejects known placeholders. Inserts secret into `private.app_secrets`.
- **Outcome**: Handshake passes immediately upon app startup.

### Scenario B: Existing Valid Secret with Environment Mismatch
- **Condition**: PostgreSQL contains an existing secret $S_1$, while application environment supplies $S_2 \neq S_1$.
- **Prior Risk**: With `ON CONFLICT DO NOTHING`, migration ignored $S_2$, leaving $S_1$ in the database while the app used $S_2$. All RLS queries silently returned 0 rows.
- **Remediated Behavior**: Migration detects mismatch and raises `RuntimeError("DATABASE IDENTITY SECRET MISMATCH: ... To rotate the secret, re-run with ROTATE_IDENTITY_SECRET=true")`.
- **Runtime Protection**: FastAPI lifespan executes `verify_database_trust()`, logs critical error, and fails closed.

### Scenario C: Existing Insecure Placeholder Secret
- **Condition**: Database contains a placeholder (`CHANGE_ME`, default dev string) in a production or staging deployment.
- **Remediated Behavior**: Migration upgrade detects placeholder in restricted environments and refuses to proceed unless `ROTATE_IDENTITY_SECRET=true` is provided with a valid high-entropy secret.

### Scenario D: Missing or Empty Secret
- **Condition**: `DATABASE_IDENTITY_SECRET` unset or empty in production/staging.
- **Remediated Behavior**: `Settings` Pydantic validator rejects configuration immediately with `ValueError`. Application and migrations refuse to start.

### Scenario E: Explicit Authorized Secret Rotation
- **Condition**: Operator deliberately rotates the identity secret using `scripts/rotate_identity_secret.py --new-secret <secret> --confirm` or running migrations with `ROTATE_IDENTITY_SECRET=true`.
- **Behavior**:
  1. Validates new secret entropy and length.
  2. Updates `private.app_secrets` under schema owner credentials.
  3. Verifies post-rotation handshake using `app_verify_trust_handshake`.
  4. Leaves all historical consent records, audit events, and user data completely valid and accessible.
