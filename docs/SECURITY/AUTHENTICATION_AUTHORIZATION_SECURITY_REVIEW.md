# SceneSteward — Authentication & Authorization Security Review

**Status:** Verified & Remediated  
**Date:** 2026-11-06  
**Auditors:** Application Security Engineer, Principal Architect  
**Scope:** Authentication Flow, Token Lifecycle, RBAC, Participant Portal Access  

---

## 1. Authentication Mechanisms

SceneSteward supports dual authentication mechanisms designed for staff crew members and documentary participants:

### 1.1 Staff Crew Authentication (JWT)
- **Production Mode (`auth_provider="supabase"`):**
  - Cryptographically verifies incoming `Authorization: Bearer <token>` headers against Supabase JSON Web Key Set (JWKS).
  - Validates `iss` (Issuer), `aud` (Audience), and expiration timestamps (`exp`).
  - Claims map to platform identity: `sub` identifies user account, `email` resolves or links user record.
- **Development/Test Mode (`auth_provider="dev"`):**
  - Mints and verifies HMAC-SHA256 signed JWTs using `AUTH_DEV_SECRET`.
  - Disallowed in production environment (`app_env == "production"` triggers startup guard failure).

### 1.2 Participant Self-Service Portal Tokens
- **Participant Access Token:**
  - Independent, cryptographically signed token minted via `mint_participant_token(participant_id, project_id, ttl_seconds=604800)`.
  - Payload contains:
    ```json
    {
      "sub": "<participant_uuid>",
      "project_id": "<project_uuid>",
      "scope": "participant_portal",
      "iss": "scenesteward",
      "iat": 1794040000,
      "exp": 1794644800
    }
    ```
  - Allows participants to view their personal consent choices and submit questions or withdrawal requests without requiring a full platform account.
  - Validated by `decode_participant_token()`: enforces scope check, expiration check, and signature verification.

---

## 2. Role-Based Access Control (RBAC) Matrix

Project access is governed by strict project-scoped roles stored in `project_memberships`:

| Operation / Endpoint | `project_owner` | `producer` | `archivist` | `legal_counsel` | `participant_care_lead` | Unassigned / Viewer |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **Project Settings / Delete** | **ALLOW** | DENY | DENY | DENY | DENY | DENY |
| **Invite Members** | **ALLOW** | DENY | DENY | DENY | DENY | DENY |
| **Register Participant** | **ALLOW** | **ALLOW** | DENY | DENY | **ALLOW** | DENY |
| **Record Consent Choices** | **ALLOW** | **ALLOW** | DENY | DENY | **ALLOW** | DENY |
| **View Decrypted Contacts** | **ALLOW** | **ALLOW** | DENY | DENY | **ALLOW** | DENY |
| **Submit Proposed Use** | **ALLOW** | **ALLOW** | **ALLOW** | DENY | DENY | DENY |
| **Human Decision on Review** | **ALLOW** | **ALLOW** | DENY | **ALLOW** | DENY | DENY |
| **Approve Outbound Comm** | **ALLOW** | **ALLOW** | DENY | DENY | **ALLOW** | DENY |
| **Read-Only Audit Timeline** | **ALLOW** | **ALLOW** | **ALLOW** | **ALLOW** | **ALLOW** | DENY |

---

## 3. Discovered Vulnerability Remediation: Participant Clarification Gate

### 3.1 The Vulnerability
Prior to this hardening cycle, the endpoint `POST /api/v1/participants/{participant_id}/clarification-requests` contained an authentication bypass condition:
```python
# VULNERABLE LOGIC:
if token:
    # validated participant token
elif authorization:
    # validated user token
else:
    actor_desc = "participant_direct"  # <--- Bypassed authentication completely!
```
An attacker could invoke this endpoint without credentials, forging clarification tasks or fake withdrawal alerts.

### 3.2 The Secure Implementation
The endpoint now strictly enforces mutual exclusivity and non-repudiation:
```python
# REMEDIATED LOGIC:
if token:
    claims = decode_participant_token(token)
    if claims.get("sub") != str(participant_id):
        raise PermissionDenied("Token does not match this participant")
    actor_desc = "participant_token"
elif authorization and authorization.lower().startswith("bearer "):
    from app.api.dependencies import get_current_user
    user = get_current_user(db, authorization)
    actor_desc = f"user:{user.id}"
else:
    raise Unauthenticated("Participant token or bearer authorization required")

with system_context(db):
    participant = db.get(Participant, participant_id)
    if participant is None:
        raise NotFoundError("Participant not found")

    if claims is not None:
        if str(participant.project_id) != claims.get("project_id"):
            raise NotFoundError("Participant not found")
    elif user is not None:
        membership = get_membership(db, participant.project_id, user)
        if membership is None:
            raise NotFoundError("Participant not found")
```

### 3.3 Security Boundary Properties
1. **Unauthenticated Access:** Blocked with HTTP 401 (`Unauthenticated`).
2. **Participant Token Mismatch:** Mismatched `sub` returns HTTP 403; mismatched `project_id` returns HTTP 404.
3. **Cross-Tenant Staff Access:** Authenticated users from outside the project receive HTTP 404, preventing cross-tenant information leakage.
4. **Audit Trail Authenticity:** The audit record strictly identifies `actor_id="participant_token"` or `actor_id=f"user:{user.id}"`.
