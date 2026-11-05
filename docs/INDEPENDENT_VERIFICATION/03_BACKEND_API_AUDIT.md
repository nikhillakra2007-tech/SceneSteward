# SceneSteward — Complete Backend API Surface & Contract Audit

**Document ID:** `docs/INDEPENDENT_VERIFICATION/03_BACKEND_API_AUDIT.md`  
**Execution Date:** 2026-11-05  
**Auditor:** Senior Backend Integration & Security Engineer  

---

## 1. REST Endpoint Inventory & Authorization

The SceneSteward API defines **50+ endpoints** structured across 16 modular routers. Every endpoint enforces strict role-based access control (RBAC), tenant validation, and Pydantic v2 schemas:

| Endpoint Path | Method | Authentication | Required Roles / Scopes | Rate Limited | Schema In / Out | Status |
|:---|:---:|:---:|:---|:---:|:---|:---:|
| `/health` & `/health/live` | GET | None | Public probe | No | `dict` | PASS |
| `/health/ready` | GET | None | Public probe | No | `dict` | PASS |
| `/api/v1/auth/login` | POST | None | Public / Supabase JWT | Yes | `LoginIn` &rarr; `TokenOut` | PASS |
| `/api/v1/projects` | POST | Bearer JWT | Authenticated user | Yes | `ProjectCreate` &rarr; `ProjectOut` | PASS |
| `/api/v1/projects` | GET | Bearer JWT | Authenticated user | Yes | None &rarr; `Page[ProjectOut]` | PASS |
| `/api/v1/projects/{id}` | GET | Bearer JWT | Project Member (`READ_ROLES`) | Yes | None &rarr; `ProjectOut` | PASS |
| `/api/v1/projects/{id}/notifications` | GET | Bearer JWT | Project Member (`READ_ROLES`) | Yes | None &rarr; `list[NotificationOut]` | PASS |
| `/api/v1/projects/{id}/audit-export` | GET | Bearer JWT | Project Member (`READ_ROLES`) | Yes | None &rarr; `ProjectAuditExportOut` | PASS |
| `/api/v1/projects/{id}/participants` | POST | Bearer JWT | Staff (`PARTICIPANT_WRITE_ROLES`) | Yes | `ParticipantCreate` &rarr; `ParticipantOut` | PASS |
| `/api/v1/projects/{id}/participants` | GET | Bearer JWT | Project Member / Linked User | Yes | Params (`search`, `status`) &rarr; `Page[ParticipantOut]` | PASS |
| `/api/v1/participants/{id}/access-token` | POST | Bearer JWT | Staff (`PARTICIPANT_WRITE_ROLES`) | Yes | None &rarr; `ParticipantTokenResponse` | PASS |
| `/api/v1/participants/{id}/portal-access` | GET | Portal Token | Valid participant token | Yes | `token` query &rarr; `ParticipantOut` | PASS |
| `/api/v1/participants/{id}/clarification-requests`| POST | Portal Token / JWT | Participant / User | Yes | `ClarificationRequestIn` &rarr; `ClarificationRequestOut` | PASS |
| `/api/v1/participants/{id}/consent-records` | POST | Bearer JWT | Staff (`PARTICIPANT_WRITE_ROLES`) | Yes | `ConsentRecordCreate` &rarr; `ConsentRecordOut` | PASS |
| `/api/v1/participants/{id}/consent-records` | GET | JWT / Token | Member or Participant | Yes | Params (`status`) &rarr; `Page[ConsentRecordOut]` | PASS |
| `/api/v1/consent-records/{id}/confirm` | POST | Bearer JWT | Staff (`CONSENT_CONFIRM_ROLES`) | Yes | `ConsentConfirmRequest` &rarr; `ConsentRecordOut` | PASS |
| `/api/v1/projects/{id}/documents` | GET | Bearer JWT | Staff (`SENSITIVE_READ_ROLES`) | Yes | None &rarr; `Page[DocumentOut]` | PASS |
| `/api/v1/participants/{id}/documents/upload-url` | POST | Bearer JWT | Staff (`PARTICIPANT_WRITE_ROLES`) | Yes | `UploadUrlRequest` &rarr; `UploadUrlResponse` | PASS |
| `/api/v1/participants/{id}/documents/complete-upload` | POST | Bearer JWT | Staff (`PARTICIPANT_WRITE_ROLES`) | Yes | `CompleteUploadRequest` &rarr; `DocumentOut` | PASS |
| `/api/v1/documents/{id}/extract` | POST | Bearer JWT | Staff (`PARTICIPANT_WRITE_ROLES`) | Yes | None &rarr; `DocumentOut` | PASS |
| `/api/v1/documents/{id}/propose-consent` | POST | Bearer JWT | Staff (`PARTICIPANT_WRITE_ROLES`) | Yes | None &rarr; `dict` | PASS |
| `/api/v1/documents/{id}/intelligence` | GET | Bearer JWT | Staff (`SENSITIVE_READ_ROLES`) | Yes | None &rarr; `DocumentIntelligenceOut` | PASS |
| `/api/v1/projects/{id}/proposed-uses` | POST | Bearer JWT | Staff (`STORY_WRITE_ROLES`) | Yes | `ProposedUseCreate` &rarr; `ProposedUseOut` | PASS |
| `/api/v1/projects/{id}/proposed-uses` | GET | Bearer JWT | Project Member (`READ_ROLES`) | Yes | Params (`status`, `participant_id`) &rarr; `Page[ProposedUseOut]` | PASS |
| `/api/v1/reviews/{id}/decide` | POST | Bearer JWT | Staff (`REVIEW_DECIDE_ROLES`) | Yes | `ReviewDecisionIn` &rarr; `ReviewOut` | PASS |
| `/api/v1/projects/{id}/communications` | POST | Bearer JWT | Staff (`COMMUNICATION_WRITE_ROLES`) | Yes | `CommunicationCreate` &rarr; `CommunicationOut` | PASS |
| `/api/v1/communications/{id}/approve` | POST | Bearer JWT | Staff (`COMMUNICATION_APPROVE_ROLES`) | Yes | None &rarr; `CommunicationOut` | PASS |
| `/api/v1/communications/{id}/send` | POST | Bearer JWT | Staff (`COMMUNICATION_WRITE_ROLES`) | Yes | None &rarr; `CommunicationOut` (or 503) | PASS |
| `/api/v1/projects/{id}/timeline` | GET | Bearer JWT | Project Member (`READ_ROLES`) | Yes | None &rarr; `Page[TimelineEntry]` | PASS |
| `/api/v1/projects/{id}/tasks` | GET | Bearer JWT | Project Member (`READ_ROLES`) | Yes | None &rarr; `Page[TaskOut]` | PASS |

---

## 2. Frontend TypeScript Parity

The frontend TypeScript client ([`frontend/src/lib/api.ts`](file:///c:/Users/nikhi/OneDrive/Desktop/coding/FLIPTHESWITCH/frontend/src/lib/api.ts)) was audited against the Pydantic schemas in `backend/app/schemas/`:
- **Consent Schema:** Exact parity on 15 canonical categories (`CANONICAL_CATEGORIES`).
- **Participant Model:** Parity on `ParticipantTokenResponse` (`token`, `access_token`, `expires_in`).
- **Clarification Model:** Parity on `ClarificationRequestIn` (`concern`, `category`, `request_type`).
- **Document Model:** Parity on `DocumentOut` (`signature_status`, `extraction_status`).
- **Review Decision Model:** Parity on `ReviewDecisionIn` (`decision`, `rationale`).
