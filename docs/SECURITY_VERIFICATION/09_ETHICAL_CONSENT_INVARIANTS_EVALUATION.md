# SceneSteward — Ethical Consent Invariants Evaluation

## 1. The 12 Ethical & Consent Invariants

Automated tests in `backend/tests/security/test_ethical_consent_invariants.py` formally verify that SceneSteward adheres to its ethical principles:

| Invariant # | Principle | Enforcement Mechanism | Test Status |
|:---:|:---|:---|:---:|
| **1** | **Silence is Never Consent** | If a consent record does not explicitly address a category, comparison engine outputs `NEEDS_DISCUSSION`, never `RECORDED_CHOICE_MATCH`. | **VERIFIED** |
| **2** | **Missing Records Fail Closed** | If participant has no confirmed record, comparison engine outputs `OUTCOME_MISSING_RECORD` / `NEEDS_DISCUSSION`. | **VERIFIED** |
| **3** | **No Cross-Use Implication** | Agreement to interview or archival use never implies trailer, marketing, or synthetic voice rights. | **VERIFIED** |
| **4** | **Entity & Project Isolation** | Participant consent from Project A is strictly inaccessible and non-transferable to Project B. | **VERIFIED** |
| **5** | **Revocation Fails Closed** | When consent is declined or revoked, `get_latest_confirmed()` returns `None`. | **VERIFIED** |
| **6** | **Ambiguity Flags Review Blocker** | Ambiguous or incomplete proposed use metadata results in `UNRESOLVED` requiring human review. | **VERIFIED** |
| **7** | **AI Advisory Agents Cannot Authorize** | Agent outputs require `requires_human_review = True`; review decision state machine strictly requires human actor ID. | **VERIFIED** |
| **8** | **Comms Require Human Approval** | Outbound messages cannot transition to `sent` without prior human approval. | **VERIFIED** |
| **9** | **Append-Only Audit Trail** | Audit events record cryptographic correlation IDs, immutable timestamps, and auto-redact secrets. | **VERIFIED** |
| **10** | **Unconfigured Providers Fail Closed** | Communications delivery without a configured provider returns 503 / PreconditionFailed, never fake success. | **VERIFIED** |
| **11** | **Deterministic Comparison** | Repeated invocations of comparison engine on identical inputs yield 100% byte-for-byte identical outcomes. | **VERIFIED** |
| **12** | **RLS Trust Under SQL Injection** | SQL injection attempts in session GUCs or headers cannot bypass HMAC trust boundary. | **VERIFIED** |
