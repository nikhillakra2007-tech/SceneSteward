# Execution Ledger — GitHub Actions CI Stabilization

| Timestamp (UTC) | Phase / Action | Command / Target | Result | Key Metrics / Notes |
| :--- | :--- | :--- | :---: | :--- |
| 2026-11-05 13:30 | Investigation | GitHub API `/actions/runs` | Identified | Runs 42035003581, 42034978896, 42035052442 inspected. |
| 2026-11-05 13:31 | Log Retrieval | GitHub API `/actions/jobs/127270731398/logs` | Captured | Docker build context missing `/backend/requirements.txt`. |
| 2026-11-05 13:32 | Log Retrieval | GitHub API `/actions/jobs/127270732885/logs` | Captured | Pytest RLS InsufficientPrivilege on table `projects`. |
| 2026-11-05 13:34 | Local Reproduction | `test_beyond_the_silence.py` with CI secret | Reproduced | Reproduced exact RLS failure locally. |
| 2026-11-05 13:35 | Branch Creation | `git checkout -b fix/github-actions-ci-stabilization` | OK | Dedicated single working branch created from `main`. |
| 2026-11-05 13:36 | Backend Fix | `backend/tests/conftest.py` | OK | Added `private.app_secrets` sync to `_verify_schema`. |
| 2026-11-05 13:37 | Standalone Fix | `backend/scripts/verify_documentary_lifecycle.py` | OK | Added fallback route for `DATABASE_URL` and admin sync. |
| 2026-11-05 13:38 | Migration Fix | `backend/migrations/versions/e1f2a3b4c5d6_*.py` | OK | Added `DATABASE_IDENTITY_SECRET` environment check. |
| 2026-11-05 13:39 | Workflow Fix | `.github/workflows/ci.yml` | OK | Fixed Docker build context to `.`; added DB env vars. |
| 2026-11-05 13:40 | Test Suite Execution | `python -m pytest backend/tests` | OK | 208/208 tests passed in 111.11s with CI secret. |
| 2026-11-05 13:42 | Lifecycle Execution | `verify_documentary_lifecycle.py` | OK | 8/8 steps passed cleanly. |
| 2026-11-05 13:43 | Lint Verification | `python -m ruff check backend` | OK | All checks passed. |
| 2026-11-05 13:44 | Documentation | `docs/GITHUB_CI_STABILIZATION/` | OK | Authored all 11 reports and execution ledger. |
