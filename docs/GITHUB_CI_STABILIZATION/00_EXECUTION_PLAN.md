# 00. Execution Plan — GitHub CI/CD Stabilization

## Mission Context
- **Target Repository**: `https://github.com/nikhillakra2007-tech/SceneSteward`
- **Initial Baseline SHA**: `460f96e1d4ae46ca4bf5426a529799aa5806d0c9`
- **Working Branch**: `fix/github-actions-ci-stabilization`
- **Objective**: Independently investigate all failing GitHub Actions checks, diagnose root causes from real runner logs, implement targeted fixes, verify locally and remotely, open exactly ONE PR, wait for all required checks to turn green, and merge into `main` before synchronizing `develop`.

## Absolute Git Workflow
1. Working branch created from latest `main`: `fix/github-actions-ci-stabilization`.
2. All fixes applied to this single branch.
3. Single PR opened targeting `main`: `Fix: Stabilize GitHub Actions and CI/CD Validation`.
4. Continuous monitoring of remote GitHub Action runs until all checks pass.
5. Squash-merge into `main` and fast-forward/sync `develop`.

## Execution Phases
- **Phase 1**: Remote log retrieval and failure inventory (Runs 42035003581, 42034978896, 42035052442).
- **Phase 2**: Root-cause analysis (Docker build context and HMAC identity secret database mismatch).
- **Phase 3**: Backend and RLS CI stabilization (`backend/tests/conftest.py`, `backend/scripts/verify_documentary_lifecycle.py`, migration `e1f2a3b4c5d6`).
- **Phase 4**: Docker infrastructure stabilization (`.github/workflows/ci.yml`).
- **Phase 5**: Local validation (Full pytest suite 208/208, Ruff lint 100%, 8-step documentary lifecycle).
- **Phase 6**: Pull request, remote verification, and clean merge.
