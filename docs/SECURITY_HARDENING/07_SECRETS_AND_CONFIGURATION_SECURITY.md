# 07. Secrets and Configuration Security

## Configuration Loader Security (`app/core/config.py`)
SceneSteward utilizes Pydantic Settings (`pydantic-settings`) with strict field validators enforcing configuration safety at application startup.

### 1. Dev Auth Prohibitions in Production
- `AUTH_PROVIDER=dev` is strictly rejected if `APP_ENV=production`.
- The application raises `ValidationError` during settings instantiation, preventing the container or process from booting.
- In production, `AUTH_PROVIDER=supabase` is mandatory, requiring verified JWKS endpoint configurations and audience matching.

### 2. Encryption-at-Rest Key Management
- Participant personally identifiable information (PII) including email addresses, phone numbers, and physical addresses are encrypted at rest using AES-CBC / HMAC-SHA256 authenticated symmetric encryption via `cryptography.fernet.Fernet`.
- Key rotation is supported via a key ring structure (`APP_ENCRYPTION_KEY_RING`).
- If encryption key material is invalid or missing, the system fails closed with `Unauthenticated("Contact encryption is not configured", code="encryption_unavailable")` rather than falling back to plaintext storage.

### 3. Database Identity Trust Secret
- `DATABASE_IDENTITY_SECRET` must be set to a high-entropy string in production.
- Migration `e1f2a3b4c5d6` validates this constraint before executing schema updates.
- Secrets are never logged or returned in error payloads. All exceptions catch and mask sensitive database parameters.
