# 10. Security Regression Tests

## Test Suite Location: `backend/tests/security/test_trust_boundary.py`

Total security tests in file: **12 tests** (all verified passing).

### Summary of New Adversarial & Regression Test Cases

#### 1. `test_adversarial_tampered_signature_rejected`
- **Objective**: Verify that any tampering or forgery of the HMAC signature (`app.user_sig`) immediately invalidates authorization.
- **Method**: Computes a legitimate signature for a user, then mutates the last character of the hex digest. Executes a query under the application role (`scenesteward_app`).
- **Result**: `app_current_user_id()` returns `NULL`, and the query returns exactly 0 visible rows (fail closed).

#### 2. `test_adversarial_wrong_secret_rejected`
- **Objective**: Verify that signatures generated with an unauthorized or mismatched secret cannot access tenant data.
- **Method**: Generates an HMAC signature using `"wrong_adversarial_secret_key"`.
- **Result**: Cryptographic validation fails in PostgreSQL; 0 rows are visible.

#### 3. `test_adversarial_malformed_user_id_fails_safe`
- **Objective**: Verify that SQL injection attempts or malformed non-UUID strings in `app.user_id` fail safe without throwing unhandled database exceptions.
- **Method**: Passes payloads such as `'admin-user' OR '1'='1'` and malformed UUID strings with matching HMAC signatures.
- **Result**: PostgreSQL exception handler `WHEN invalid_text_representation THEN RETURN NULL` safely catches the error and returns `NULL`.

#### 4. `test_runtime_role_cannot_modify_app_secrets`
- **Objective**: Verify that the application runtime role (`scenesteward_app`) cannot alter the trust root in `private.app_secrets`.
- **Method**: Executes `INSERT`, `UPDATE`, and `DELETE` queries on `private.app_secrets` using a connection authenticated as `scenesteward_app`.
- **Result**: PostgreSQL raises `InsufficientPrivilege` on each statement, verifying permission denial.

#### 5. `test_connection_pool_context_leakage_prevented`
- **Objective**: Verify that identity configuration set via `set_config(..., true)` does not persist across connection checkout / checkin cycles.
- **Method**: Sets user identity in transaction 1 and commits. Opens transaction 2 on the same connection without setting identity.
- **Result**: Transaction 2 observes `NULL` for `app.user_id` and sees 0 rows, confirming zero leakage across transactions.
