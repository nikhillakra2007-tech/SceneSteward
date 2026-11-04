# SceneSteward — Secrets Management, Cryptography & Key Rotation

**Document Version:** 1.0.0  
**Status:** Active / Production Ready  
**Date:** 2026-11-04  

---

## 1. Threat Model & Principles

In SceneSteward, participant safety is paramount. Contact details (phone numbers, physical addresses, emergency contacts, secure email channels) represent high-risk Personally Identifiable Information (PII). A database compromise or snapshot leak must never expose unencrypted participant contact channels.

### Core Principles
1. **Zero Plaintext at Rest:** Plaintext contact data never touches PostgreSQL columns, database dumps, transaction logs, or audit payloads.
2. **Deterministic Fail-Closed:** If encryption keys are missing or invalid, operations fail closed with an explicit error (`encryption_unavailable` or `encryption_failed`). Data is never stored in plaintext or fallbacks.
3. **No Downtime Key Rotation:** Active keys can rotate seamlessly. The system supports multi-key key rings (`KID`s), allowing historical records to remain decryptable while all new records use the active key.
4. **Purpose-Bound Storage Access:** Document uploads and downloads rely on HMAC-SHA256 signed URLs bound to a strict purpose (`upload` vs `download`), participant/project scopes, expiration timestamps, and server-side secret material.

---

## 2. Cryptographic Architecture

### 2.1 Symmetric Encryption at Rest (Fernet + Versioned Envelope)

Participant contact data in `participant_contact_records.encrypted_contact_data` is encrypted using 128-bit AES in CBC mode with PKCS7 padding and HMAC-SHA256 authentication (via Cryptography's `Fernet`).

#### Envelope Formats

* **Version 2 (Active/Current):**
  ```text
  v2.<kid>.<fernet_token>
  ```
  - `v2`: Envelope version tag.
  - `<kid>`: Identifier of the key within the key ring (e.g. `primary`, `prod-2026-q4`).
  - `<fernet_token>`: Standard URL-safe Base64-encoded Fernet token.

* **Legacy Version 1 (Backward Compatible):**
  ```text
  gAAAAA...
  ```
  Unversioned Fernet tokens written prior to key ring versioning. The decryption engine automatically identifies legacy tokens and iterates over the key ring to decrypt them without data loss.

### 2.2 Key Ring Configuration

Keys are loaded from environment variables into `Settings`:
- `APP_ENCRYPTION_KEY`: Primary Base64 URL-safe 32-byte Fernet key.
- `APP_ENCRYPTION_CURRENT_KID`: Current active key identifier (default: `primary`).
- `APP_ENCRYPTION_KEYS`: JSON mapping or comma-separated pairs representing the active key ring:
  ```json
  {"primary": "<base64-key-1>", "legacy_2025": "<base64-key-2>"}
  ```
  or:
  ```text
  primary:<base64-key-1>,legacy_2025:<base64-key-2>
  ```

---

## 3. Key Rotation Procedure

To rotate encryption keys without service downtime:

1. **Deploy New Key Material:**
   Add the new key to `APP_ENCRYPTION_KEYS` while retaining the existing key in the ring.
   Set `APP_ENCRYPTION_CURRENT_KID` to the new key ID.
   ```bash
   APP_ENCRYPTION_CURRENT_KID=prod_2026_v2
   APP_ENCRYPTION_KEYS='{"prod_2026_v2": "<new_key>", "primary": "<old_key>"}'
   ```
   At this stage:
   - All newly created or updated contact records are encrypted with `prod_2026_v2`.
   - Existing records encrypted with `primary` continue to decrypt seamlessly.

2. **Execute In-Place Background Rotation:**
   Run the migration script to re-encrypt existing records to the new active KID:
   ```bash
   # Dry-run inspection:
   python -m scripts.rotate_encryption_keys --target-kid prod_2026_v2 --dry-run

   # Perform rotation:
   python -m scripts.rotate_encryption_keys --target-kid prod_2026_v2 --batch-size 100
   ```
   The script iterates over `participant_contact_records`, decrypts records matching older KIDs, re-encrypts them with the target KID, and commits in atomic batches.

3. **Retire Decommissioned Key:**
   Once all records are updated (confirmed via `--dry-run` returning 0 records needing re-encryption), remove the old key from `APP_ENCRYPTION_KEYS`.

---

## 4. Signed URLs for Private Document Access

Release documents and participant contracts are stored in private storage (local filesystem in development, private S3/Supabase storage in staging/production). Direct public access is strictly prohibited.

### Token Construction
```text
<base64url_payload>.<hmac_sha256_hex>
```
Payload schema:
```json
{
  "key": "project_id/participant_id/uuid_filename.pdf",
  "purpose": "download",
  "exp": 1793798400,
  "kid": "primary",
  "project_id": "<uuid>"
}
```

### Security Controls
1. **Purpose Binding:** An upload token cannot be used to download, and vice versa. Mismatch returns `412 Precondition Failed`.
2. **Replay & Expiration Guard:** Tokens include a POSIX timestamp expiration (`exp`). Expired tokens are rejected.
3. **Tamper Proofing:** The signature is calculated across `base64url(payload)` using HMAC-SHA256 derived from server-side secrets (`_signing_material()`). Constant-time comparison prevents timing attacks.
4. **Scope Validation:** Storage keys are strictly scoped as `{project_id}/{participant_id}/{uuid}_{filename}`.
5. **Security Headers on Retrieval:** Download responses enforce:
   - `X-Content-Type-Options: nosniff`
   - `Cache-Control: no-store`
   - Sanitized filename disposition.

---

## 5. Secrets Inventory & Storage Standards

| Environment Variable | Category | Description | Required in Prod |
|---|---|---|---|
| `DATABASE_URL` | DB Credentials | Least-privilege runtime connection (`scenesteward_app`) | Yes |
| `MIGRATION_DATABASE_URL` | DB Credentials | Schema owner connection (`scenesteward`) used only for Alembic | Yes |
| `APP_ENCRYPTION_KEY` | Crypto Secret | Primary 32-byte URL-safe base64 Fernet key | Yes |
| `APP_ENCRYPTION_CURRENT_KID` | Config | Active Key ID in the key ring | No (default: `primary`) |
| `APP_ENCRYPTION_KEYS` | Crypto Secret | JSON map of all valid decryption keys | No (fallback to primary) |
| `AUTH_DEV_SECRET` | Auth Secret | HS256 secret for local testing. Refused in production. | Prohibited in prod |
| `SUPABASE_URL` | Cloud Integration | Base URL for Supabase JWKS and storage API | When auth_provider=supabase |
| `SUPABASE_SERVICE_ROLE_KEY` | Cloud Secret | Restricted to administrative cloud tasks | If Supabase storage used |
| `ANTHROPIC_API_KEY` | AI Secret | Claude 3.5/4.5 Sonnet API key | When ai_provider=anthropic |
| `SWITCH_API_KEY` | Integration | Shared API secret for Switch orchestration webhook/calls | When switch_adapter=http |
| `SWITCH_WEBHOOK_SECRET` | Integration | HMAC secret for verifying incoming Switch events | When switch_adapter=http |

**Storage & Lifecycle Rules:**
- Never hardcode secrets in source code, default files, or tests.
- Production environments must inject secrets via Kubernetes Secrets, AWS Secrets Manager, or HashiCorp Vault.
- `.env.example` contains only dummy placeholders.

