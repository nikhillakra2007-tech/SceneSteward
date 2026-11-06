# SceneSteward Frontend Subsystem — API Integration Guide

This guide describes how the Next.js frontend integrates with the SceneSteward FastAPI backend across all operational domains.

---

## 1. Centralized API Architecture

All HTTP communications are centralized in `frontend/src/lib/api.ts` through the `apiFetch<T>` utility.

### Configuration
- Base URL is resolved dynamically via `process.env.NEXT_PUBLIC_API_URL` with a fallback to `http://127.0.0.1:8000`.
- Authentication uses Bearer tokens stored in `localStorage` (`scenesteward_token`).
- All requests automatically inject `Authorization: Bearer <token>` when a token is present.
- JSON content types are set automatically for non-FormData payloads.

### Standardized Error Normalization
When the backend responds with a non-2xx status, `apiFetch` extracts and normalizes the error message from the response JSON body:
```typescript
if (!response.ok) {
  let errMessage = `HTTP ${response.status}: ${response.statusText}`;
  try {
    const errJson = await response.json();
    if (errJson.detail) {
      errMessage = typeof errJson.detail === 'string' ? errJson.detail : JSON.stringify(errJson.detail);
    }
  } catch {
    // fallback to status text
  }
  throw new Error(errMessage);
}
```

---

## 2. Domain Method Index

| Domain | Method in `api.ts` | Backend Endpoint | Description |
| :--- | :--- | :--- | :--- |
| **Auth** | `api.loginDev(email, name)` | `POST /api/v1/auth/dev-token` | Authenticates dev persona or custom user; stores token |
| | `api.getMe()` | `GET /api/v1/auth/me` | Fetches active user profile and project memberships |
| | `api.logout()` | N/A | Clears token and resets local session state |
| **Projects** | `api.listProjects()` | `GET /api/v1/projects` | Lists projects accessible under user's RLS boundary |
| | `api.createProject(data)` | `POST /api/v1/projects` | Creates new documentary production workspace |
| | `api.getProject(id)` | `GET /api/v1/projects/{id}` | Retrieves project details |
| **Participants** | `api.listParticipants(id)` | `GET /api/v1/projects/{id}/participants` | Lists roster members (filtered by search/status) |
| | `api.createParticipant(id, data)`| `POST /api/v1/projects/{id}/participants` | Registers participant with preferred language |
| | `api.getParticipant(id)` | `GET /api/v1/participants/{id}` | Retrieves participant profile |
| | `api.issueParticipantToken(id)` | `POST /api/v1/participants/{id}/access-token` | Mints 7-day cryptographically signed self-service token |
| | `api.getParticipantPortalAccess(id, token)` | `GET /api/v1/participants/{id}/portal-access` | Authenticates portal session via signed token |
| | `api.submitClarificationRequest(id, data, token)` | `POST /api/v1/participants/{id}/clarification-requests` | Submits inquiry or formal withdrawal notice |
| **Consent** | `api.getParticipantConsents(id, token)` | `GET /api/v1/participants/{id}/consent-records` | Retrieves 15-category agreement history |
| | `api.createConsentRecord(id, data)` | `POST /api/v1/participants/{id}/consent-records` | Records canonical category agreement choices |
| | `api.confirmConsentRecord(id, data)` | `POST /api/v1/consent-records/{id}/confirm` | Commits participant confirmation |
| **Documents** | `api.listDocuments(id)` | `GET /api/v1/projects/{id}/documents` | Lists scanned release forms and antivirus status |
| | `api.createUploadUrl(id, data)` | `POST /api/v1/participants/{id}/documents/upload-url` | Pre-signs secure upload target |
| | `api.completeUpload(id, data)` | `POST /api/v1/participants/{id}/documents/complete-upload` | Completes upload and triggers ClamAV scan |
| | `api.extractDocument(id)` | `POST /api/v1/documents/{id}/extract` | Runs OCR text extraction on release agreement |
| **Proposed Uses** | `api.listProposedUses(id)` | `GET /api/v1/projects/{id}/proposed-uses` | Lists proposed footage / likeness uses |
| | `api.createProposedUse(id, data)` | `POST /api/v1/projects/{id}/proposed-uses` | Submits proposed use and executes comparison engine |
| | `api.analyseProposedUse(id)` | `POST /api/v1/proposed-uses/{id}/analyse` | Re-executes 63-case comparison engine |
| | `api.getAgentFindings(id)` | `GET /api/v1/proposed-uses/{id}/agent-findings` | Retrieves background AI advisory findings |
| **Reviews** | `api.listReviews(id)` | `GET /api/v1/projects/{id}/reviews` | Lists pending and decided human review queues |
| | `api.recordHumanDecision(id, data)` | `POST /api/v1/reviews/{id}/human-decision` | Records binding decision with mandatory reason |
| **Tasks** | `api.listTasks(id)` | `GET /api/v1/projects/{id}/tasks` | Lists operational care tasks |
| | `api.updateTask(id, data)` | `PATCH /api/v1/tasks/{id}` | Updates task status (`open`, `done`) or priority |
| **Care Outreach** | `api.listCommunications(id)` | `GET /api/v1/projects/{id}/communications` | Lists outreach drafts and approvals |
| | `api.createDraftCommunication(id, data)` | `POST /api/v1/projects/{id}/communications` | Drafts participant communication |
| | `api.approveCommunication(id, notes)` | `POST /api/v1/communications/{id}/approve` | Records human approval for message dispatch |
| | `api.sendCommunication(id)` | `POST /api/v1/communications/{id}/send` | Fails closed (503) if no provider configured |
| **Analytics** | `api.getAnalyticsOverview(filters)` | `GET /api/v1/analytics/overview` | Headline KPIs and executive status summaries |
| | `api.getConsentAnalytics(filters)` | `GET /api/v1/analytics/consent` | Coverage, approval, and resolution rates |
| | `api.getConsentCategoriesBreakdown(filters)` | `GET /api/v1/analytics/consent/categories` | 15 canonical category detailed status matrix |
| | `api.getReviewAnalytics(filters)` | `GET /api/v1/analytics/reviews` | Human review pipeline velocity |
| | `api.getOperationsAnalytics(filters)` | `GET /api/v1/analytics/operations` | Task backlog and interview status |
| | `api.getWithdrawalAnalytics(filters)` | `GET /api/v1/analytics/withdrawals` | Revocations and withdrawal triage |
| | `api.getAdvisoryAnalytics(filters)` | `GET /api/v1/analytics/advisory` | AI advisory concordance and disclaimer |
| | `api.getTrendsAnalytics(filters)` | `GET /api/v1/analytics/trends` | Time-series event aggregations |
| | `api.exportAnalytics(payload)` | `POST /api/v1/analytics/exports` | Generates RFC 4180 CSV / JSON report |

---

## 3. Security Invariants Enforced

1. **No Client-Side Authority**: Frontend identity selections (e.g. quick persona toggles) are purely dev conveniences; the backend independently checks and authorizes all operations via signed JWT tokens.
2. **Participant Portal Boundary**: Participants accessing `/participant/[id]` with signed portal tokens are denied access to production analytics (`HTTP 403 Forbidden`).
3. **Cross-Tenant Fail-Closed**: Cross-tenant project accesses fail closed with `HTTP 404 Not Found`, preventing project enumeration or identification leakage.

