# SceneSteward Authorization Matrix

Complete role-based access control (RBAC) matrix across all 8 supported roles and major operations.

## Role Definitions

1. `project_owner`: Full administrative authority over project, membership, data, and decisions.
2. `producer`: Production management, participant creation, review decisions, and communication drafting.
3. `director`: Creative narrative lead, story element author, and proposed use initiator.
4. `editor`: Read-only narrative context and story element exploration; no participant or consent mutation.
5. `participant_care_lead`: Participant welfare advocate, contact access, consent confirmation, and communication approval.
6. `viewer`: Read-only access to basic project metadata; contact details and sensitive timeline entries hidden.
7. `participant`: Subject access; strictly scoped to self-owned participant record and documents.
8. `service_agent`: Internal automation and Switch bridge; automated event processing.

---

## Permission Matrix

| Operation / Endpoint Group | Owner | Producer | Director | Editor | Care Lead | Viewer | Participant (Self) | Service Agent |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **Project: Update Metadata** | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Project: Manage Members** | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Participant: Create & Edit** | ✅ | ✅ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ |
| **Participant: View Profile** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ (Self) | ✅ |
| **Contact Data: Read Plaintext** | ✅ | ✅ | ❌ | ❌ | ✅ | ❌ | ✅ (Self) | ❌ |
| **Contact Data: Add Record** | ✅ | ✅ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ |
| **Documents: Request Upload URL** | ✅ | ✅ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ |
| **Documents: View & Download** | ✅ | ✅ | ❌ | ❌ | ✅ | ❌ | ✅ (Self) | ❌ |
| **Documents: Trigger Extraction** | ✅ | ✅ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ |
| **Consent: Draft Record** | ✅ | ✅ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ |
| **Consent: Confirm Record** | ✅ | ✅ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ |
| **Consent: View History** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ (Self) | ✅ |
| **Story Elements: Create & Edit** | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Proposed Use: Submit & Edit** | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Proposed Use: Run AI Analysis**| ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Agent Findings: View Diagnostic**| ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ |
| **Human Decision: Complete Review**| ✅ | ✅ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ |
| **Communications: Draft Message**| ✅ | ✅ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ |
| **Communications: Approve Draft**| ✅ | ✅ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ |
| **Communications: Send Outbound**| ✅ | ✅ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ |
| **Timeline: Read Full Audit** | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ (Filtered) | ❌ | ✅ |
| **Outbox: Claim Events** | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ (System) |

