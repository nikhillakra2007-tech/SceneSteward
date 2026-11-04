# SceneSteward API Integration Map

**Date**: November 4, 2026  
**FastAPI Routing Layer**: 48 active REST endpoints under `/api/v1` and `/health`.  
**Authentication**: Bearer JWT tokens via Supabase Auth or verified development tokens.  
**Multi-Tenant Isolation**: PostgreSQL Row-Level Security (RLS) with HMAC-SHA256 identity proof.

---

## Complete Mapping of All 48 REST API Endpoints

| HTTP Method | Route Path | Authorized Roles | Tables Accessed | Audit Action Emitted |
|---|---|---|---|---|
| `GET` | `/health` | Public | None | None |
| `GET` | `/health/ready` | Public | `users` (SELECT 1) | None |
| `GET` | `/api/v1/auth/me` | Authenticated | `users`, `project_memberships` | None |
| `POST` | `/api/v1/auth/logout` | Authenticated | None | `auth.logout` |
| `POST` | `/api/v1/projects` | Authenticated | `projects`, `project_memberships` | `project.created`, `membership.created` |
| `GET` | `/api/v1/projects` | Authenticated | `projects`, `project_memberships` | None |
| `GET` | `/api/v1/projects/{project_id}` | Member | `projects` | None |
| `PATCH` | `/api/v1/projects/{project_id}` | Owner, Producer, Director | `projects` | `project.updated` |
| `POST` | `/api/v1/projects/{project_id}/members` | Owner | `users`, `project_memberships` | `membership.created` |
| `GET` | `/api/v1/projects/{project_id}/members` | Member | `project_memberships`, `users` | None |
| `PATCH` | `/api/v1/projects/{project_id}/members/{member_id}` | Owner | `project_memberships` | `membership.updated` |
| `DELETE` | `/api/v1/projects/{project_id}/members/{member_id}` | Owner | `project_memberships` | `membership.removed` |
| `POST` | `/api/v1/projects/{project_id}/participants` | Owner, Producer, Care Lead | `participants` | `participant.created` |
| `GET` | `/api/v1/projects/{project_id}/participants` | Member | `participants` | None |
| `GET` | `/api/v1/participants/{participant_id}` | Member, Participant (Self) | `participants` | None |
| `PATCH` | `/api/v1/participants/{participant_id}` | Owner, Producer, Care Lead | `participants` | `participant.updated` |
| `GET` | `/api/v1/participants/{participant_id}/history` | Member, Participant (Self) | `consent_records`, `consent_choices` | None |
| `GET` | `/api/v1/participants/{participant_id}/timeline` | Member (sensitive redacted for Viewer) | `audit_events` | None |
| `GET` | `/api/v1/participants/{participant_id}/contacts` | Owner, Producer, Care Lead, Self | `participants` (encrypted contact info) | `participant_contact.read` |
| `POST` | `/api/v1/participants/{participant_id}/contacts` | Owner, Producer, Care Lead | `participants` (encrypted contact info) | `contact.created` |
| `POST` | `/api/v1/participants/{participant_id}/documents/upload-url` | Owner, Producer, Care Lead | `participants` | `document.upload_url_issued` |
| `POST` | `/api/v1/participants/{participant_id}/documents/complete-upload` | Owner, Producer, Care Lead | `release_documents`, `participants` | `document.uploaded` |
| `GET` | `/api/v1/participants/{participant_id}/documents` | Owner, Producer, Care Lead, Self | `release_documents` | None |
| `GET` | `/api/v1/documents/{document_id}` | Owner, Producer, Care Lead, Self | `release_documents` | None |
| `GET` | `/api/v1/documents/{document_id}/download-url` | Owner, Producer, Care Lead, Self | `release_documents` | `document.download_url_issued` |
| `POST` | `/api/v1/documents/{document_id}/extract` | Owner, Producer, Care Lead | `release_documents`, `extracted_terms` | `document.extracted` |
| `POST` | `/api/v1/documents/{document_id}/propose-consent` | Owner, Producer, Care Lead | `release_documents`, `consent_records`, `consent_choices` | `consent_record.proposed` |
| `POST` | `/api/v1/participants/{participant_id}/consent-records` | Owner, Producer, Care Lead | `consent_records`, `consent_choices` | `consent_record.created` |
| `GET` | `/api/v1/participants/{participant_id}/consent-records` | Member, Participant (Self) | `consent_records`, `consent_choices` | None |
| `POST` | `/api/v1/consent-records/{record_id}/confirm` | Owner, Producer, Care Lead | `consent_records` | `consent_record.confirmed` |
| `GET` | `/api/v1/consent-records/{record_id}` | Member, Participant (Self) | `consent_records`, `consent_choices` | None |
| `GET` | `/api/v1/consent-records/{record_id}/history` | Member, Participant (Self) | `consent_records`, `consent_choices` | None |
| `POST` | `/api/v1/projects/{project_id}/story-elements` | Owner, Producer, Director | `story_elements` | `story_element.created` |
| `GET` | `/api/v1/projects/{project_id}/story-elements` | Member | `story_elements` | None |
| `GET` | `/api/v1/story-elements/{story_element_id}` | Member | `story_elements` | None |
| `PATCH` | `/api/v1/story-elements/{story_element_id}` | Owner, Producer, Director | `story_elements` | `story_element.updated` |
| `POST` | `/api/v1/projects/{project_id}/proposed-uses` | Owner, Producer, Director | `proposed_uses` | `proposed_use.created` |
| `GET` | `/api/v1/projects/{project_id}/proposed-uses` | Member | `proposed_uses` | None |
| `GET` | `/api/v1/proposed-uses/{proposed_use_id}` | Member | `proposed_uses` | None |
| `PATCH` | `/api/v1/proposed-uses/{proposed_use_id}` | Owner, Producer, Director | `proposed_uses` | `proposed_use.updated` |
| `POST` | `/api/v1/proposed-uses/{proposed_use_id}/analyse` | Owner, Producer, Director | `proposed_use_analyses`, `agent_runs`, `reviews` | `proposed_use.analysed` |
| `GET` | `/api/v1/proposed-uses/{proposed_use_id}/agent-findings` | Member | `agent_runs` | None |
| `GET` | `/api/v1/projects/{project_id}/reviews` | Member | `reviews` | None |
| `GET` | `/api/v1/reviews/{review_id}` | Member | `reviews` | None |
| `POST` | `/api/v1/reviews/{review_id}/human-decision` | Owner, Producer, Care Lead | `reviews`, `proposed_uses` | `review.human_decision` |
| `POST` | `/api/v1/reviews/{review_id}/request-participant-discussion` | Owner, Producer, Care Lead | `reviews`, `participant_communications` | `review.discussion_requested` |
| `POST` | `/api/v1/reviews/{review_id}/resolve` | Owner, Producer, Care Lead | `reviews`, `proposed_uses` | `review.resolved` |
| `GET` | `/api/v1/projects/{project_id}/tasks` | Member | `switch_tasks` | None |
| `PATCH` | `/api/v1/tasks/{task_id}` | Owner, Producer, Care Lead | `switch_tasks` | `task.updated` |
| `GET` | `/api/v1/projects/{project_id}/communications` | Owner, Producer, Care Lead | `participant_communications` | None |
| `POST` | `/api/v1/projects/{project_id}/communications` | Owner, Producer, Care Lead | `participant_communications` | `communication.draft_created` |
| `POST` | `/api/v1/communications/{communication_id}/approve` | Owner, Producer, Care Lead | `participant_communications` | `communication.approved` |
| `POST` | `/api/v1/communications/{communication_id}/send` | Owner, Producer, Care Lead | `participant_communications` | `communication.send_attempted` |
| `GET` | `/api/v1/projects/{project_id}/timeline` | Member (sensitive filtered for Viewer) | `audit_events` | None |
| `POST` | `/api/v1/agents/runs` | Owner, Producer, Director | `agent_runs` | `agent.triggered` |
| `GET` | `/api/v1/agents/runs/{run_id}` | Member | `agent_runs` | None |
| `GET` | `/api/v1/integrations/status` | Authenticated | None | None |
| `POST` | `/api/v1/integrations/switch/projects/{project_id}/rooms` | Owner, Producer | `switch_tasks` | `switch.room_created` |
| `GET` | `/api/v1/storage/local/download/{token}` | Public (HMAC signed token required) | None | None |
| `PUT` | `/api/v1/storage/local/upload/{token}` | Public (HMAC signed token required) | None | None |
| `GET` | `/api/v1/metrics` | Authenticated / Operator | In-memory counters & DB pools | None |
