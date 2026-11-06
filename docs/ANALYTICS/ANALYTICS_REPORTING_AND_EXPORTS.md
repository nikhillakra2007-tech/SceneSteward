# SceneSteward Analytics Subsystem — Reporting and Exports

This document details the generation, cryptographic integrity, formatting, and auditability of SceneSteward compliance and operational reports.

---

## 1. Export Capabilities & Supported Formats

SceneSteward provides authorized team members (`admin`, `director`, `producer`) the ability to export structured analytics reports in two formats:

1. **RFC 4180 Compliant CSV**:
   - Explicit comma separators, CRLF line terminators (`\r\n`), and double-quote escapes (`""`) for fields containing commas or quotes.
   - Excel and spreadsheet compatible with UTF-8 BOM encoding.
   - Includes standard metadata header block (scope, timestamps, generator).
2. **Standard JSON**:
   - Machine-readable hierarchical JSON structure matching the API schemas.
   - Ideal for downstream archival, ETL pipelines, or compliance auditing.

---

## 2. Available Report Types

| Report Type | Key Contents | Target Audience |
| :--- | :--- | :--- |
| `overview` | Headline KPIs, consent totals, review velocity, open tasks, withdrawals | Executive Producers, Legal Counsel |
| `consent_matrix` | Complete 15-category matrix breakdown ($N_{\text{agreed}}, N_{\text{declined}}, N_{\text{undecided}}, N_{\text{not\_discussed}}$) | Legal Clearance, Production Supervisors |
| `reviews` | Review pipeline status, turnaround times, and reviewer throughput | Editorial Leads, Post-Production Supervisors |
| `operations` | Task backlog, interview status, urgent blockers, participant care items | Line Producers, Production Coordinators |
| `withdrawals` | Active withdrawal triage, urgency levels, revoked items | Production Counsel, Rights Managers |

---

## 3. Cryptographic Integrity and Immutability

To ensure exported reports cannot be altered or disputed after generation:

1. **SHA-256 Digest**:
   - Every generated report file is hashed with SHA-256.
   - The hex digest is returned in the HTTP response header `X-Report-SHA256`.
2. **Immutable Audit Trail**:
   - At the moment of export generation, `backend/app/analytics/export_service.py` records an immutable audit log entry in the PostgreSQL `audit_log` table:
     ```python
     await audit.record(
         db=db,
         action="export_generated",
         actor_id=user.id,
         entity_type="analytics_report",
         entity_id=uuid.uuid4(),
         participant_id=None,
         details={
             "report_type": report_type,
             "format": format,
             "project_id": str(project_id) if project_id else "all",
             "sha256": report_sha256,
             "size_bytes": len(content_bytes)
         }
     )
     ```
3. **Traceability**:
   - If an exported report is presented for legal clearance, auditors can verify the exact SHA-256 hash against SceneSteward's immutable PostgreSQL audit log to prove authenticity and non-tampering.

---

## 4. How to Generate an Export

### Via Web Interface
1. Open `/analytics`.
2. Select your desired Project and Time Range filters.
3. Click the **Export Report** button in the header.
4. In the dialog:
   - Select **Report Type** (e.g. *15 Canonical Categories Matrix*).
   - Select **File Format** (*CSV Spreadsheet* or *JSON Data*).
   - Click **Download Report**.
5. The browser initiates a direct stream download with an audit-stamped filename:
   `scenesteward_analytics_<report_type>_<timestamp>.<ext>`.

### Via REST API
```bash
curl -X GET "https://app.scenesteward.com/api/v1/analytics/exports?report_type=consent_matrix&format=csv&project_id=a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11" \
     -H "Authorization: Bearer <your_access_token>" \
     -o consent_matrix_report.csv
```

