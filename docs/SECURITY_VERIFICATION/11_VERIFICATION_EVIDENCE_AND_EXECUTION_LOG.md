# SceneSteward — Verification Evidence & Execution Log

## 1. Test Suite Execution

### Backend Pytest Suite
```
============================= test session starts =============================
platform win32 -- Python 3.12.10, pytest-9.2.0, pluggy-1.7.0
rootdir: C:\Users\nikhi\OneDrive\Desktop\coding\FLIPTHESWITCH\backend
configfile: pyproject.toml
plugins: anyio-4.16.0
collected 241 items

backend\tests\agents\test_agents.py ...........                          [  4%]
backend\tests\e2e\test_beyond_the_silence.py ..                          [  5%]
backend\tests\e2e\test_complete_documentary_workflow.py .                [  5%]
backend\tests\e2e\test_integrated_lifecycle.py .                         [  6%]
backend\tests\integration\test_auth.py ............                      [ 11%]
backend\tests\integration\test_communications.py ..                      [ 12%]
backend\tests\integration\test_document_intelligence_api.py ..           [ 12%]
backend\tests\integration\test_documents.py ............                 [ 17%]
backend\tests\integration\test_extraction.py .....                       [ 19%]
backend\tests\integration\test_failure_modes.py ......                   [ 22%]
backend\tests\integration\test_metrics.py ..                             [ 23%]
backend\tests\integration\test_migrations.py ....                        [ 24%]
backend\tests\integration\test_reporting_and_notifications.py ...        [ 26%]
backend\tests\integration\test_switch.py ........                        [ 29%]
backend\tests\integration\test_tenant_isolation.py .....                 [ 31%]
backend\tests\security\test_ethical_consent_invariants.py ............   [ 36%]
backend\tests\security\test_lifecycle_guards.py ..........               [ 40%]
backend\tests\security\test_rbac.py ..........                           [ 44%]
backend\tests\security\test_rls_isolation.py ........                    [ 48%]
backend\tests\security\test_secret_lifecycle.py ....                     [ 49%]
backend\tests\security\test_trust_boundary.py ..............             [ 55%]
backend\tests\unit\test_comparison_engine.py ..........                  [ 59%]
backend\tests\unit\test_config_security.py .......                       [ 62%]
backend\tests\unit\test_consent_engine_matrix.py ....................... [ 72%]
........................................                                 [ 88%]
backend\tests\unit\test_document_intelligence.py ......                  [ 91%]
backend\tests\unit\test_encryption.py .......                            [ 94%]
backend\tests\unit\test_health_probes.py ..                              [ 95%]
backend\tests\unit\test_independent_adversarial_consent.py .....         [ 97%]
backend\tests\unit\test_rate_limiter.py .......                          [100%]

============================ 241 passed in 56.41s =============================
```

### Ruff Linter Check
```
backend\.venv\Scripts\python -m ruff check backend
All checks passed!
```

### 8-Step Documentary Lifecycle Verification
```
===========================================================================
 SCENESTEWARD VERIFICATION SUMMARY: 8/8 STEPS PASSED
 ALL CONSENT INVARIANTS, SECURITY BOUNDARIES, AND HUMAN GATES VERIFIED.
===========================================================================
```

### Frontend Production Build
```
Route (app)                              Size     First Load JS
┌ ○ /                                    4.97 kB         102 kB
├ ○ /_not-found                          873 B          88.2 kB
├ ƒ /participant/[id]                    8.32 kB         106 kB
├ ○ /projects                            4.54 kB         102 kB
└ ƒ /projects/[id]                       11.7 kB         109 kB
+ First Load JS shared by all            87.3 kB

○  (Static)   prerendered as static content
ƒ  (Dynamic)  server-rendered on demand

Build exited with code 0.
```

### Docker Compose Configuration Validation
```
docker compose -f docker-compose.staging.yml config --quiet
Exited with code 0.
```
