# 02. GitHub Actions Security Audit

## Audit Target
- File: `.github/workflows/ci.yml`
- Trigger events: `push` (branches: `main`, `develop`), `pull_request` (branches: `main`, `develop`).

## Findings & Risk Analysis

### 1. Default GITHUB_TOKEN Permissions
- **Observation**: The workflow previously lacked an explicit top-level `permissions` block.
- **Risk**: In GitHub repositories where default workflow permissions are set to "Read and write permissions", the auto-generated `GITHUB_TOKEN` is granted write access across contents, issues, pull requests, packages, and deployments. If any action or step was compromised, the token could be leveraged for repository tampering or lateral movement.
- **Remediation**: Added top-level `permissions: contents: read` to enforce least privilege across all workflow jobs. Jobs requiring no write access operate under read-only restrictions.

### 2. Script Injection Surface
- **Observation**: All workflow steps invoke static scripts and commands (e.g. `pytest`, `ruff check`, `npm run build`). No `github.event.*` expressions (such as PR titles, issue bodies, or commit messages) are interpolated directly into shell script execution blocks (`run:`).
- **Risk Level**: Minimal. No shell injection vectors found.

### 3. Secret Exposure in Logs
- **Observation**: CI workflow uses service-container environment variables for local PostgreSQL credentials (`POSTGRES_USER: scenesteward`, `POSTGRES_PASSWORD: ci_test_password`).
- **Risk Level**: Minimal. These credentials are intentionally ephemeral CI test fixture variables, completely decoupled from production credentials.
- **Remediation**: Verified that no production secrets or real API keys are referenced or echoed in workflow step logs.

### 4. Runner Integrity & Pinning
- **Observation**: Actions used:
  - `actions/checkout@v4`
  - `actions/setup-python@v5`
  - `actions/setup-node@v4`
- **Assessment**: Official GitHub Actions pinned to major version tags.
