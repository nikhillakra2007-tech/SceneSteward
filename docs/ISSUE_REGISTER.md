# SCENESTEWARD — ISSUE REGISTER
**Document Reference:** `docs/ISSUE_REGISTER.md`  
**Updated Date:** 2026-11-06 (Post-Mission 38 Acceptance)  
**Auditor:** QA & Platform Security Engineering  

---

## Active & Resolved Issue Register

| Issue ID | Severity | Category | Description | Root Cause | Fix / Resolution | Verification | Remaining Risk |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **ISS-001** | P2 | Testing / Playwright | E2E Test A timed out attempting to click persona preset | Test attempted to click header element behind modal overlay | Replaced locator with button inside active modal dialog | Test A passed in 5.2s | None. Standard dialog focus behavior. |
| **ISS-002** | P3 | Testing / Playwright | E2E Test H failed looking for `"AI Advisory & Trends"` tab | Tab text was updated to `"Advisory & Trends"` in analytics page | Updated test locator in `comprehensive_product_experience.spec.ts` | Test H passed in 1.7s | None. Aligned with production DOM. |
| **ISS-003** | P3 | Testing / Playwright | Strict mode violation in Test I on `text=Olivia Director` | Text matched both header name and toast announcement | Added `.first()` to Playwright locator | Test I passed in 1.4s | None. |
| **ISS-004** | P2 | API Integration | Missing field `concern` in clarification request test | Schema requires `concern: str`, test passed `question` | Updated test payload to supply `concern` and `request_type` | Clarification API returned HTTP 201 | None. Confirms strict Pydantic validation. |
| **ISS-005** | P3 | Operational / SMTP | Outbound communication send returns HTTP 503 | No external SMTP/Twilio credentials in local test environment | System fail-closed by design; UI provides "Copy Text to Clipboard" | Verified safe HTTP 503 return without false positive "sent" | Coordinator must route external outreach manually when offline. |
| **ISS-006** | P3 | Configuration | PyJWT `InsecureKeyLengthWarning` for `AUTH_DEV_SECRET` | `AUTH_DEV_SECRET` in `.env` was 26 bytes (< 32-byte RFC 7518 recommendation) | Recommended $\ge 32$-byte high-entropy string in production deployment checklist | Verified; dev auth disabled in production | None in production where Supabase JWKS (RS256) is enforced. |
| **ISS-007** | P2 | Database / RLS | RLS Policy denies UPDATE on `audit_events` resulting in `rowcount: 0` | Table intentionally lacks UPDATE policy; trigger protects owner mutations | Documented multi-layer defense in depth in `AUDIT_INTEGRITY_REPORT.md` | Verified via direct SQL tests on owner and runtime roles | None. Desired security behavior (append-only audit). |
| **ISS-008** | P2 | Testing / Playwright | Playwright Test A locator timed out searching for `Olivia (Director / Owner)` | Dialog button renders preset name (`Olivia Director`) and email (`olivia@example.com`), not label | Updated test to target `button:has-text("olivia@example.com")` within modal | Playwright 11/11 passed in 9.3s | None. Exact locator targeting. |
| **ISS-009** | P3 | Tooling / Disaster Recovery | `verify_isolated_restore.py` raised lifecycle guard exception when executed standalone | Destructive operations fail closed unless `APP_ENV=test` and admin credentials provided | Documented environment variable requirements (`APP_ENV=test`, `DATABASE_URL_ADMIN`) | DR drill executed and verified in 2.33s | None. Enforces fail-closed lifecycle safety. |

---

## Severity Scale
- **P0:** Security vulnerabilities, data corruption, unauthorized sensitive operations. (**0 Active, 0 Total**)
- **P1:** Core workflows broken, database integration failures, incorrect business logic. (**0 Active, 0 Total**)
- **P2:** Incomplete functionality, incorrect validation, API inconsistencies, test failures. (**0 Active, 4 Resolved**)
- **P3:** UI inconsistencies, test locator drift, configuration warnings. (**0 Active, 5 Resolved/Documented**)
- **P4:** Minor documentation and formatting adjustments.
