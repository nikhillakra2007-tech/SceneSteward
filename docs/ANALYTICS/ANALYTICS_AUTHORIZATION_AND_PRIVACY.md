# SceneSteward Analytics Subsystem — Authorization and Privacy Architecture

This document describes the role-based access control (RBAC), multi-tenant isolation, and data privacy safeguards governing the Analytics Subsystem in SceneSteward.

---

## 1. Multi-Tenant Isolation Model

SceneSteward is a multi-tenant documentary production platform. Tenant boundaries are enforced through a layered defense-in-depth model:

1. **PostgreSQL Row-Level Security (RLS)**:
   - All underlying tables (`projects`, `participants`, `interviews`, `consent_records`, `human_reviews`, `tasks`, `withdrawals`, `audit_log`) have active RLS policies.
   - At connection time or transaction start, the user context (`app.current_user_id`, `app.current_user_role`) is bound to the database session.
   - All live SQL queries in `backend/app/analytics/service.py` execute within this RLS context, guaranteeing that a tenant can never aggregate or observe rows outside their authorized productions.

2. **Application Boundary Check (No Existence Leakage)**:
   - When a specific `project_id` filter is supplied, `require_analytics_read_access` verifies project membership.
   - If the project does not exist or belongs to another tenant, the API returns **HTTP 404 Not Found**, never HTTP 403.
   - This prevents enumeration attacks and leaks of project identifiers.

---

## 2. Role-Based Access Control (RBAC) Matrix

The analytics subsystem defines two explicit privilege tiers:

```
ANALYTICS_READ_ROLES   = {UserRole.ADMIN, UserRole.DIRECTOR, UserRole.PRODUCER, UserRole.CREW}
ANALYTICS_EXPORT_ROLES = {UserRole.ADMIN, UserRole.DIRECTOR, UserRole.PRODUCER}
```

| Role | Analytics Dashboard Access | API Query Endpoints | CSV / JSON Data Export | Participant Privacy Masking |
| :--- | :--- | :--- | :--- | :--- |
| **Admin** | Full Platform / Project | Allowed | Allowed | Direct access |
| **Director** | Assigned Projects | Allowed | Allowed | Direct access |
| **Producer** | Assigned Projects | Allowed | Allowed | Direct access |
| **Crew** | Assigned Projects | Allowed | **Denied (HTTP 403)** | Aggregate metrics only |
| **Participant** | **Denied (HTTP 403)** | **Denied (HTTP 403)** | **Denied (HTTP 403)** | N/A |

### Why Participant Access is Denied (HTTP 403)
Documentary participants interact with SceneSteward via the dedicated Participant Care Portal (`/participant/[id]`), where they review their own interview timeline, personal consent choices, and withdrawal requests.
Allowing participants access to aggregated production intelligence, internal review notes, crew tasks, or overall project consent metrics would violate participant confidentiality, documentary trade secrets, and GDPR / privacy principles. Any request by a `participant` token to `/api/v1/analytics/*` is denied with `HTTP 403 Forbidden`.

---

## 3. Data Privacy and Participant Confidentiality

### 3.1. Aggregation-First Architecture
The analytics queries return aggregated statistics rather than individual personally identifiable information (PII):
- Headcount totals, percentages, and status counts.
- Category breakdown counts ($N_{\text{agreed}}, N_{\text{declined}}, N_{\text{undecided}}, N_{\text{not\_discussed}}$).
- Cycle times (average hours for review completion).

### 3.2. Export Sanitization
When report exports (`/api/v1/analytics/exports`) are generated:
- Export files contain structured operational metrics and category totals.
- No raw biometric identifiers, phone numbers, or private contact details are included in the analytics export.
- Participant IDs (UUIDs) are used strictly when necessary for audit tracing, preserving pseudonymization.

### 3.3. Immutable Audit Logging
Export operations are high-privilege compliance events. Whenever an export is generated:
- An entry is appended to `audit_log` with `action="export_generated"`.
- The actor's user ID, IP address, user agent, export format, report type, filter parameters, and timestamp are recorded.
- Audit logs are append-only and cannot be updated or deleted.

