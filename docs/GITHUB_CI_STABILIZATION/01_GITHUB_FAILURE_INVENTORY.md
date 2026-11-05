# 01. GitHub Actions Failure Inventory

## Workflow Runs Inspected
- **Run ID**: `42035003581` (Commit `460f96e` on `main`)
- **Run ID**: `42034978896` (Commit `3b2a6eb` on `audit/final-independent-verification-and-remediation`)
- **Run ID**: `42035052442` (Commit `460f96e` on `develop`)

## Detailed Job Failure Matrix

| Workflow | Run ID | Job | Failing Step | Error Output / Symptom | Classification |
| :--- | :---: | :--- | :--- | :--- | :--- |
| **SceneSteward CI** | 42035003581 | `Docker Infrastructure & Configuration Validation` (127270731398) | Step 4: `Test Backend Container Build` | `ERROR: failed to calculate checksum of ref ...: "/backend/requirements.txt": not found` | Docker Build Context Defect |
| **SceneSteward CI** | 42035003581 | `Backend Security, Lints & Test Suite` (127270732885) | Step 10: `Run Pytest Suite (Unit, Matrix, Security & Integration)` | `psycopg.errors.InsufficientPrivilege: new row violates row-level security policy for table "projects"` (HTTP 500 on `POST /api/v1/projects`) | Environment / Database Identity Secret Mismatch |
| **SceneSteward CI** | 42035003581 | `Backend Security, Lints & Test Suite` (127270732885) | Step 11: `Verify 8-Step Documentary Lifecycle` | Skipped due to previous step failure | Cascade failure |
| **SceneSteward CI** | 42035003581 | `Frontend Type Check & Production Build` (127270732681) | None | Job passed cleanly (`npm ci` + Next.js 14 production build) | PASS |
