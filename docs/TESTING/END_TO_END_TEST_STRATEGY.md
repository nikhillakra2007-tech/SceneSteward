# SceneSteward — End-to-End Test Strategy & Verification Architecture

## 1. Executive Summary & Purpose

The SceneSteward End-to-End (E2E) Test Strategy establishes verifiable, automated, and reproducible assurance that the platform strictly enforces all documentary ethics invariants, cryptographic trust boundaries, and operational guarantees under staging-equivalent conditions.

The test strategy spans five complementary tiers:
1. **Tier 1: Unit & Domain Model Tests** — Pure logic, PII encryption, cryptographic tokens, and schema validation.
2. **Tier 2: API & Integration Tests** — HTTP endpoints, RLS policies, RBAC matrices, and error envelopes.
3. **Tier 3: Staging E2E Acceptance Test Suite** — Comprehensive user scenarios (A through H) validating full end-to-end workflows.
4. **Tier 4: Documentary Lifecycle Verification** — Executable 8-step lifecycle script validating the full participant journey.
5. **Tier 5: Browser E2E Playwright Suite** — Real browser testing of Next.js frontend interfaces, bilingual switches, and auth modals.

---

## 2. Test Architecture & Tier Distinctions

```
┌─────────────────────────────────────────────────────────────────┐
│ Tier 5: Playwright Browser E2E Tests (Chromium / Firefox / WebKit)│
│ - Identity switching modal, participant portal, bilingual UI    │
├─────────────────────────────────────────────────────────────────┤
│ Tier 4: Documentary Lifecycle Verification (Python Executable)  │
│ - 8-step continuous validation: Elena Rostova -> Miriam Kalu    │
├─────────────────────────────────────────────────────────────────┤
│ Tier 3: Staging E2E Acceptance Suite (Pytest Integration)       │
│ - Scenarios A-H: Non-transitive, silence, withdrawal, malware   │
├─────────────────────────────────────────────────────────────────┤
│ Tier 2: Component Integration Tests (Database, RLS, Storage)    │
│ - 266 passing test cases covering RBAC, outbox, health probes   │
├─────────────────────────────────────────────────────────────────┤
│ Tier 1: Unit Tests & Cryptographic Primitives                   │
│ - Fernet 256, HMAC-SHA256 tokens, Pydantic schemas, choices     │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. Core Ethical Invariants Under Test

SceneSteward enforces four non-negotiable ethical rules that are systematically asserted in every verification tier:

### Invariant 1: Silence is Never Agreement
- **Rule**: If a participant has not explicitly agreed to a consent category (e.g., status is `not_discussed`, missing, or null), the platform MUST treat it as unconsented.
- **Verification**: `test_scenario_c_silence_and_incomplete_consent` verifies that proposed uses touching unsettled categories return `NEEDS_DISCUSSION` and cannot be approved automatically.

### Invariant 2: Non-Transitive Consent
- **Rule**: Agreement to appear in a primary documentary film does NOT grant permission to use likeness or footage in promotional clips, trailers, marketing, or external distribution.
- **Verification**: `test_scenario_b_separate_intended_uses_nontransitive` verifies that agreeing to `documentary_appearance` while declining `promotional_clips` generates explicit `PARTICIPANT_DECLINED` findings.

### Invariant 3: AI Advisory Bounds
- **Rule**: Automated AI agents (Anthropic Claude, consent analysts) provide guidance and findings ONLY. AI agents have ZERO authority to approve, reject, or execute proposed uses.
- **Verification**: `test_scenario_e_human_decision_authority_and_ai_advisory` verifies that AI evaluations never change the approval state.

### Invariant 4: Human Decision Authority & Mandatory Rationale
- **Rule**: Every binding decision on proposed footage or likeness uses requires an authenticated human decider (Director, Producer, Care Lead) providing a mandatory written rationale.
- **Verification**: Attempts to decide without rationale or with rationale shorter than 3 characters return HTTP 422. Completed decisions are locked via optimistic concurrency to prevent double mutation.

---

## 4. Test Scenario Coverage Matrix

| Scenario | Scope | Key Assertion | Automated Test |
| :--- | :--- | :--- | :--- |
| **Scenario A** | Normal Consent Lifecycle | Project -> Participant -> 15 Categories -> Confirm -> Portal -> Comparison -> Review -> Audit | `test_scenario_a_normal_consent_lifecycle` |
| **Scenario B** | Non-Transitive Consent | Agreed to doc appearance, declined promo clips -> Comparison flags decline | `test_scenario_b_separate_intended_uses_nontransitive` |
| **Scenario C** | Silence is Never Agreement | Unsettled categories return uncertainty, never agreement | `test_scenario_c_silence_and_incomplete_consent` |
| **Scenario D** | Revocation & Withdrawal | Participant portal withdrawal notice -> urgent task -> audit event | `test_scenario_d_revocation_and_withdrawal` |
| **Scenario E** | Human Decision Authority | AI cannot decide; human requires mandatory rationale; duplicate rejected | `test_scenario_e_human_decision_authority_and_ai_advisory` |
| **Scenario F** | Document & Malware Lifecycle | Presigned upload -> ClamAV scan -> capability download -> traversal blocked | `test_scenario_f_private_document_lifecycle_and_malware_gate` |
| **Scenario G** | Concurrent Operations | Optimistic locking on participant & review updates -> 409 conflict | `test_scenario_g_concurrent_operations_and_idempotency` |
| **Scenario H** | Immutable Audit Trail | Keyset-paginated timeline records all mutations with immutable metadata | `test_scenario_h_complete_audit_trail_and_export` |
| **Adversarial** | Cross-Tenant Isolation | Tenant Beta receives 403/404 when attempting to access Tenant Alpha resources | `test_cross_tenant_isolation_adversarial` |

---

## 5. Adversarial & Security Testing

In addition to standard functional flows, the E2E test suite executes negative and adversarial attack simulations:
1. **RLS Bypass Attempt**: Verifying that `scenesteward_app` cannot read `private.app_secrets` or access cross-tenant project data even with raw SQL injection vectors.
2. **Path Traversal Attack**: Verifying that directory traversal sequences (`../../etc/shadow`, `/abs/path`) in document storage keys are rejected with HTTP 412/422.
3. **MIME Sniffing & Extension Tampering**: Verifying that dangerous files (e.g. `.exe`, `.sh`) are rejected prior to storage.
4. **Optimistic Locking Conflicts**: Verifying that concurrent writers cannot overwrite state without incrementing the expected version.
5. **Fail-Closed Delivery**: Verifying that external communication delivery fails closed with HTTP 503 rather than recording a false success when providers are absent.
