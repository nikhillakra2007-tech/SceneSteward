# SceneSteward Analytics Subsystem — API Reference

This document provides the definitive specification for all Analytics API endpoints implemented in SceneSteward v1.0.0 (`/api/v1/analytics/*`).

---

## 1. Authentication & Base URL

All requests must be authenticated using a JSON Web Token (JWT) in the `Authorization` header:
```http
Authorization: Bearer <jwt_token>
```

**Base Path:** `/api/v1/analytics`

All endpoints enforce multi-tenant isolation through PostgreSQL Row-Level Security (RLS) and FastAPI dependency injection (`require_analytics_read_access`, `require_analytics_export_access`).

---

## 2. Endpoints Overview

| Method | Endpoint | Description | Permitted Roles |
| :--- | :--- | :--- | :--- |
| `GET` | `/overview` | Aggregated executive KPIs across platform or project | Admin, Director, Producer, Crew |
| `GET` | `/projects` | Per-project high-level analytics summary cards | Admin, Director, Producer, Crew |
| `GET` | `/consent` | Detailed consent statistics & aggregate metrics | Admin, Director, Producer, Crew |
| `GET` | `/consent/categories` | 15 canonical category detailed status matrix | Admin, Director, Producer, Crew |
| `GET` | `/reviews` | Human review & verification pipeline metrics | Admin, Director, Producer, Crew |
| `GET` | `/operations` | Tasks, interviews, and participant care operations | Admin, Director, Producer, Crew |
| `GET` | `/withdrawals` | Participant withdrawal, revocation, and triage tracking | Admin, Director, Producer, Crew |
| `GET` | `/advisory` | AI advisory vs human review concordance metrics | Admin, Director, Producer, Crew |
| `GET` | `/trends` | Time-series aggregations (consent & review activity) | Admin, Director, Producer, Crew |
| `POST` | `/exports` | RFC 4180 CSV / JSON report generation | Admin, Director, Producer |

*Note: The `participant` role is strictly forbidden from accessing all analytics endpoints (HTTP 403 Forbidden).*

---

## 3. Query Parameters

All analytics query endpoints accept the following standard filtering parameters:

| Parameter | Type | Required | Description | Example |
| :--- | :--- | :--- | :--- | :--- |
| `project_id` | `UUID` | No | Filters analytics to a single project. Returns 404 if project is not found or inaccessible. | `a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11` |
| `from_date` | `datetime` | No | Start timestamp (inclusive, UTC). | `2026-01-01T00:00:00Z` |
| `to_date` | `datetime` | No | End timestamp (inclusive, UTC). | `2026-12-31T23:59:59Z` |

Validation rule: If both `from_date` and `to_date` are supplied, `from_date` must be less than or equal to `to_date`, or HTTP 422 Unprocessable Entity is returned.

---

## 4. Endpoint Specifications

### 4.1. `GET /api/v1/analytics/overview`
Retrieves executive headline KPIs.

**Response Schema (`AnalyticsOverviewResponse`):**
```json
{
  "scope": {
    "project_id": null,
    "project_title": "All Projects",
    "from_date": null,
    "to_date": null,
    "generated_at": "2026-11-06T12:00:00Z"
  },
  "headline": {
    "total_projects": 3,
    "active_participants": 24,
    "total_interviews": 18,
    "discussion_coverage_rate": 82.5,
    "overall_approval_rate": 68.2,
    "overall_resolution_rate": 78.4,
    "pending_reviews": 5,
    "open_operational_tasks": 12,
    "active_withdrawals": 1
  },
  "consent_summary": { ... },
  "review_summary": { ... },
  "operations_summary": { ... },
  "withdrawal_summary": { ... }
}
```

---

### 4.2. `GET /api/v1/analytics/consent`
Detailed breakdown of consent metrics, including mathematical rates.

**Response Schema (`ConsentMetricsResponse`):**
```json
{
  "scope": { ... },
  "total_participants": 10,
  "total_canonical_categories": 15,
  "total_applicable_categories": 150,
  "total_discussed_categories": 120,
  "total_agreed_choices": 95,
  "total_declined_choices": 15,
  "total_undecided_choices": 10,
  "total_not_discussed_categories": 30,
  "discussion_coverage_rate": 80.0,
  "approval_rate": 63.33,
  "resolution_rate": 73.33,
  "withdrawn_participants_count": 1,
  "categories_breakdown": [ ... ]
}
```

---

### 4.3. `GET /api/v1/analytics/consent/categories`
Returns the status distribution across all 15 canonical categories.

**Response Schema (`List[CategoryBreakdown]`):**
```json
[
  {
    "category": "interview_recording",
    "display_name": "Interview Recording",
    "agreed_count": 10,
    "declined_count": 0,
    "undecided_count": 0,
    "not_discussed_count": 0,
    "total_participants": 10,
    "coverage_rate": 100.0,
    "approval_rate": 100.0
  },
  {
    "category": "voice_cloning",
    "display_name": "Voice Cloning (Synthetic Audio)",
    "agreed_count": 2,
    "declined_count": 7,
    "undecided_count": 1,
    "not_discussed_count": 0,
    "total_participants": 10,
    "coverage_rate": 100.0,
    "approval_rate": 20.0
  }
]
```

---

### 4.4. `GET /api/v1/analytics/reviews`
Operational throughput and status of human review verification pipeline.

**Response Schema (`ReviewMetricsResponse`):**
```json
{
  "scope": { ... },
  "pending_count": 4,
  "in_review_count": 2,
  "approved_count": 35,
  "rejected_count": 3,
  "changes_requested_count": 1,
  "total_reviews": 45,
  "completion_rate": 86.67,
  "avg_review_hours": 14.5
}
```

---

### 4.5. `GET /api/v1/analytics/operations`
Interviews, tasks, participant care status, and urgent operational bottlenecks.

**Response Schema (`OperationsMetricsResponse`):**
```json
{
  "scope": { ... },
  "total_interviews": 12,
  "interviews_by_status": {
    "completed": 8,
    "in_progress": 2,
    "scheduled": 2
  },
  "total_tasks": 25,
  "open_tasks": 10,
  "completed_tasks": 15,
  "blocked_tasks": 1,
  "urgent_open_tasks": 2,
  "task_completion_rate": 60.0,
  "participants_with_open_tasks": 4
}
```

---

### 4.6. `GET /api/v1/analytics/withdrawals`
Complete tracking of participant withdrawals and revocation workflows.

**Response Schema (`WithdrawalMetricsResponse`):**
```json
{
  "scope": { ... },
  "total_participants": 20,
  "active_withdrawals": 1,
  "confirmed_withdrawals": 2,
  "pending_review_withdrawals": 1,
  "completed_withdrawals": 3,
  "withdrawal_rate": 10.0,
  "urgency_breakdown": {
    "high": 1,
    "medium": 0,
    "low": 0
  }
}
```

---

### 4.7. `GET /api/v1/analytics/advisory`
Metrics quantifying agreement and divergence between automated AI advisory extractions and human editorial decisions.

**Response Schema (`AdvisoryMetricsResponse`):**
```json
{
  "scope": { ... },
  "total_advisories": 25,
  "human_agreed_with_ai": 21,
  "human_overruled_ai": 4,
  "concordance_rate": 84.0,
  "avg_ai_confidence": 0.91,
  "advisory_disclaimer": "AI recommendations are strictly advisory and do not represent approved consent. Human editorial decisions govern all legal and ethical clearances."
}
```

---

### 4.8. `GET /api/v1/analytics/trends`
Historical time-series tracking grouped by period (`day`, `week`, or `month`).

**Query Parameters:**
- `interval`: string (`day`, `week`, `month`, default: `day`).

**Response Schema (`TrendsResponse`):**
```json
{
  "scope": { ... },
  "interval": "day",
  "points": [
    {
      "period": "2026-11-01",
      "consent_records": 12,
      "reviews_completed": 8,
      "withdrawals_initiated": 0,
      "tasks_resolved": 5
    }
  ]
}
```

---

### 4.9. `POST /api/v1/analytics/exports`
Generates verifiable, signed compliance and intelligence exports in CSV or JSON format.

**Request Body (`ExportRequestIn`):**
```json
{
  "report_type": "overview",
  "format": "csv",
  "project_id": "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11",
  "start_date": "2026-01-01T00:00:00Z",
  "end_date": "2026-12-31T23:59:59Z"
}
```

**Behavior:**
- Generates compliant RFC 4180 CSV with standard CRLF lines and double-quote escapes, or structured JSON.
- Appends RFC 4180 disclaimer and cryptographic SHA-256 integrity hash in headers.
- Emits immutable audit log entry in PostgreSQL: `action="export_generated"`, `entity_type="analytics_report"`.
- Denied to `crew` and `participant` roles (requires `admin`, `director`, or `producer`).

---

## 5. HTTP Error Statuses

| Status Code | Reason | Cause |
| :--- | :--- | :--- |
| `401 Unauthorized` | Missing or invalid JWT token | Token expired, invalid signature, or missing header |
| `403 Forbidden` | Insufficient role permissions | Role is `participant` or role lacks export rights (`crew`) |
| `404 Not Found` | Project not found or tenant isolated | Project ID does not exist or user has no access to it |
| `422 Unprocessable Entity`| Query validation failure | `from_date > to_date` or invalid UUID format |
| `500 Internal Error` | Database execution failure | Unhandled database connection or SQL query exception |

