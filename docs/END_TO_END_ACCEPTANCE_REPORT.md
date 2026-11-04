# SceneSteward — End-to-End Acceptance Test Report

**Date**: November 4, 2026  
**Auditor**: Principal QA Automation Engineer & Product Acceptance Lead  
**Scope**: 24-Step Integrated Documentary Lifecycle & Multi-Project Isolation  
**Overall Status**: **ACCEPTED & VERIFIED**  

---

## 1. Core Principle Reaffirmation

> **"A participant's agreement to one use must never automatically become agreement to another use. Silence is never agreement."**

Every test in the end-to-end suite validates this non-negotiable invariant.

---

## 2. 24-Step Integrated Lifecycle Verification

Executed in `backend/tests/e2e/test_integrated_lifecycle.py` (`test_19_step_integrated_lifecycle`). All 24 documentary lifecycle steps passed without errors:

| Step # | Lifecycle Phase | Action Executed | Verification & Assertion | Result |
|:---:|:---|:---|:---|:---:|
| **1** | Production Setup | Authenticate Care Lead user & create project | Project created with active membership and owner role | **PASS** |
| **2** | Team Invites | Invite Editor & Producer with restricted roles | Roles persisted; RBAC denies Editor from reading contacts | **PASS** |
| **3** | Participant Enrollment | Register participant "Elena Rostova" | Participant created in project scope; audit log emitted | **PASS** |
| **4** | Secure Contact Data | Add encrypted contact information (phone/email) | Stored encrypted with Fernet; decrypted only for Care Lead | **PASS** |
| **5** | Contact Access Audit | Care Lead reads decrypted contact info | Access recorded in `audit_events` with user ID & timestamp | **PASS** |
| **6** | Document Init | Initialize release form document upload | Document record created with storage key & pending status | **PASS** |
| **7** | Upload Completion | Complete upload with sha256 checksum | File size & checksum verified; storage verified | **PASS** |
| **8** | Secure Download URL | Request signed document download link | Signed URL with HMAC token generated; expires after TTL | **PASS** |
| **9** | Document Download | Download file using signed token | Byte content identical to uploaded PDF form | **PASS** |
| **10**| Text Extraction | Extract clauses from documentary release form | Background worker extracts text clauses without crashing | **PASS** |
| **11**| Consent Proposal | Create proposed unconfirmed consent record | Proposed uses mapped; status set to `proposed` | **PASS** |
| **12**| Human Confirmation | Care Lead confirms consent with witness evidence | Status transitions to `confirmed`; evidence logged | **PASS** |
| **13**| Proposed Use Creation | Director proposes new trailer / festival use | New proposed use created with target scene and audience | **PASS** |
| **14**| AI Multi-Agent Review | Trigger 5 AI agents to evaluate new use | Agents flag scope changes; output valid structured JSON | **PASS** |
| **15**| Story Change Detection| Compare proposed use with confirmed release | Flags voice reconstruction and promotional changes | **PASS** |
| **16**| Ethical Flagging | Ethics reviewer inspects vulnerable claims | Flags unverified claims; silence treated as NO agreement | **PASS** |
| **17**| Room Coordination | Create Switch collaboration discussion room | Room mapped to project and proposed use | **PASS** |
| **18**| Team Context Sharing | Send review context to Switch discussion room | Message formatted and dispatched to Switch room | **PASS** |
| **19**| Inbound Switch Event | Receive webhook event from documentary team | Inbound event verified via HMAC and stored idempotently | **PASS** |
| **20**| Consent Immutability | Webhook attempts to alter consent status | RLS and database triggers prevent webhook from changing consent | **PASS** |
| **21**| Draft Communication | Care Lead drafts participant follow-up email | Draft communication created in pending review status | **PASS** |
| **22**| Editorial Approval | Director/Producer approves participant message | Status transitions to `approved` | **PASS** |
| **23**| Secure Dispatch | Dispatch approved communication via email | Sent timestamp recorded; communication outbox updated | **PASS** |
| **24**| Immutable History | Query complete project audit log | 24 steps sequentially recorded; zero gaps or overwrites | **PASS** |

---

## 3. Multi-Tenant Project Isolation Verification

Executed in `backend/tests/e2e/test_beyond_the_silence.py`:
- Tested simultaneous operation of Project A ("Beyond the Silence") and Project B ("Whispering Pines").
- Verified that a Viewer, Editor, or Producer from Project A cannot query, update, insert, or delete records in Project B under any circumstances.
- Verified that unauthenticated requests receive HTTP 401 or fail-closed database RLS denial (0 rows).

