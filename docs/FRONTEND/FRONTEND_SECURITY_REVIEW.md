# SceneSteward Frontend Subsystem — Security Review & Threat Boundary

This document audits the frontend architecture against web security threats, data leakage, and trust boundaries.

---

## 1. Security Architecture & Threat Boundaries

In SceneSteward, the Next.js frontend is treated as an **untrusted client**:
- The backend independently validates every request using signed JWT tokens and PostgreSQL Row-Level Security (RLS).
- The frontend never performs security-critical decisions or authorization bypasses.
- No database credentials, signing keys, or server secrets exist in client-side code.

---

## 2. Threat Vector Analysis & Safeguards

### 2.1. Cross-Site Scripting (XSS)
- **Threat**: Injected malicious scripts stealing participant consent tokens or session keys.
- **Safeguard**: React automatically escapes all string interpolations in JSX.
- **Audit**: Zero usage of `dangerouslySetInnerHTML`. All participant notes, explanations, and audit strings are rendered as standard React text nodes.

### 2.2. Secret Exposure via Environment Variables
- **Threat**: Accidental leakage of database passwords, JWT secrets, or internal API keys.
- **Safeguard**: The only public environment variable is `NEXT_PUBLIC_API_URL` (pointing to the public backend gateway).
- **Audit**: Inspected all frontend files; zero secret keys or private keys are exposed.

### 2.3. Participant Token Lifecycle & Privacy
- **Threat**: Leaking participant self-service tokens or cross-contaminating participant sessions.
- **Safeguard**:
  - Participant tokens minted via `/api/v1/participants/:id/access-token` are scoped strictly to the specific participant ID with a 7-day TTL.
  - The participant portal (`/participant/[id]`) runs in read-only mode for the participant's own record.
  - Production intelligence and analytics routes strictly deny access to the `participant` role (`HTTP 403 Forbidden`).

### 2.4. Cross-Tenant Data Isolation (No Existence Leakage)
- **Threat**: Attacker discovering valid documentary project UUIDs via enumeration.
- **Safeguard**: Inaccessible or non-existent projects return `HTTP 404 Not Found`, never `HTTP 403`, eliminating project existence disclosures.

### 2.5. Safe File Downloads & MIME Sanitization
- **Threat**: Malicious file execution during export download or document upload.
- **Safeguard**:
  - Report exports (`AnalyticsExportDialog.tsx`) use `Blob` objects with explicit MIME types (`text/csv;charset=utf-8;` or `application/json;charset=utf-8;`).
  - Scanned release documents uploaded via the frontend are checked with ClamAV antivirus before being made available for processing.

