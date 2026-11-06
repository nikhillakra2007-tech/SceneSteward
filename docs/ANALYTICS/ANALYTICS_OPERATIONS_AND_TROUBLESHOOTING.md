# SceneSteward Analytics Subsystem — Operations & Troubleshooting Guide

This guide covers operational maintenance, health monitoring, error diagnostics, and incident resolution for the SceneSteward Analytics Subsystem.

---

## 1. Operational Architecture & Dependencies

The Analytics Subsystem runs entirely within the standard SceneSteward backend container and frontend Next.js application:

- **Runtime**: FastAPI (Python 3.12+), Next.js 14 (Node 20+).
- **Database**: PostgreSQL 16 with Row-Level Security (RLS).
- **Logging**: Python standard logging (`app.analytics.*`) and structured PostgreSQL audit logging (`audit_log`).
- **Dependencies**: No external analytics daemon or external microservice is required.

---

## 2. Health & Performance Monitoring

### Monitoring Query Performance
In production, monitor analytics query execution times using PostgreSQL `pg_stat_statements`:
```sql
SELECT 
    query, 
    calls, 
    total_exec_time / calls AS avg_exec_time_ms, 
    rows / calls AS avg_rows
FROM pg_stat_statements
WHERE query LIKE '%consent_records%' OR query LIKE '%human_reviews%'
ORDER BY total_exec_time DESC
LIMIT 10;
```
If `avg_exec_time_ms` exceeds 100ms for projects with fewer than 5,000 participants, run `VACUUM ANALYZE consent_records;`.

---

## 3. Common Troubleshooting Scenarios

### Scenario 1: User Receives 403 Forbidden on `/api/v1/analytics/*`
- **Cause**: The authenticated user has the `participant` role, or a `crew` member is attempting to generate an export.
- **Remedy**:
  - For participants: Confirm that the user is intended to view the participant portal (`/participant/[id]`) rather than production analytics. Participants are strictly barred by policy from accessing production analytics.
  - For crew members requesting exports: If export privileges are needed, an `admin` must update their project role to `director` or `producer`.

### Scenario 2: User Receives 404 Not Found When Querying a Project
- **Cause**: The project ID does not exist, or the user does not have membership in the project's tenant.
- **Verification**: Check if the project is assigned to the user:
  ```sql
  SELECT * FROM project_memberships WHERE project_id = :project_id AND user_id = :user_id;
  ```
- **Remedy**: Ensure the user has been granted access to the project by a director or administrator.

### Scenario 3: Category Coverage Rate Appears Lower Than Expected
- **Cause**: The denominator for discussion coverage is strictly $N_{\text{active\_participants}} \times 15$. If new participants were onboarded but only their baseline interview took place, categories not yet discussed remain in the denominator as `not_discussed`.
- **Explanation**: This is correct by design (silence is never consent). As interviews and category reviews proceed, the discussion coverage will increase.

### Scenario 4: Export Download Fails in Browser
- **Cause**: Network timeout on large datasets or popup blocker preventing blob download.
- **Remedy**:
  - Check browser console for network errors.
  - Verify authorization token has not expired.
  - Check server logs for `export_service` exceptions.

---

## 4. Runbook: Verifying Audit Records for Exports

Whenever compliance auditors request proof of report generation:
```sql
SELECT 
    id, 
    actor_id, 
    action, 
    entity_type, 
    details, 
    created_at
FROM audit_log
WHERE action = 'export_generated'
ORDER BY created_at DESC
LIMIT 20;
```
Match the `details->>'sha256'` value against the SHA-256 hash of the exported file in question to certify authenticity.

