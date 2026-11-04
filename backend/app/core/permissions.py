"""Project-scoped RBAC. Authorization is always enforced server-side.

Roles (project_memberships.role):
  project_owner, producer, director, editor, participant_care_lead,
  viewer, participant, service_agent

Permission checks happen on EVERY protected operation:
  authenticated -> active membership -> role permission -> resource scope
  (resource belongs to the project; and to the participant where relevant).
"""
from __future__ import annotations

PROJECT_OWNER = "project_owner"
PRODUCER = "producer"
DIRECTOR = "director"
EDITOR = "editor"
PARTICIPANT_CARE_LEAD = "participant_care_lead"
VIEWER = "viewer"
PARTICIPANT = "participant"
SERVICE_AGENT = "service_agent"

ALL_ROLES = {
    PROJECT_OWNER, PRODUCER, DIRECTOR, EDITOR, PARTICIPANT_CARE_LEAD,
    VIEWER, PARTICIPANT, SERVICE_AGENT,
}
# Roles that can administer a project (members, roles, ownership)
ADMIN_ROLES = {PROJECT_OWNER}
# Roles that can write project content (not consent, not contacts)
PROJECT_WRITE_ROLES = {PROJECT_OWNER, PRODUCER, DIRECTOR}
# Roles allowed to manage participant rosters and consent lifecycle
PARTICIPANT_WRITE_ROLES = {PROJECT_OWNER, PRODUCER, PARTICIPANT_CARE_LEAD}
# Sensitive reads: contact details, consent records, release documents
SENSITIVE_READ_ROLES = {PROJECT_OWNER, PRODUCER, PARTICIPANT_CARE_LEAD}
# Consent confirmation requires explicit authority (never agents, never editors)
CONSENT_CONFIRM_ROLES = {PROJECT_OWNER, PRODUCER, PARTICIPANT_CARE_LEAD}
# Final human decision on a review
REVIEW_DECIDE_ROLES = {PROJECT_OWNER, PRODUCER, PARTICIPANT_CARE_LEAD}
# Story elements & proposed uses
STORY_WRITE_ROLES = {PROJECT_OWNER, PRODUCER, DIRECTOR, EDITOR}
# Any role except service/viewer/participant can act on ordinary tasks
TASK_WRITE_ROLES = {PROJECT_OWNER, PRODUCER, DIRECTOR, EDITOR, PARTICIPANT_CARE_LEAD}
# Internal review resolution (resolve endpoint)
REVIEW_RESOLVE_ROLES = {PROJECT_OWNER, PRODUCER, PARTICIPANT_CARE_LEAD}
# Read access for ordinary project content
READ_ROLES = {PROJECT_OWNER, PRODUCER, DIRECTOR, EDITOR, PARTICIPANT_CARE_LEAD, VIEWER}

READ_ONLY_ROLES = {VIEWER}

# Timeline entries carrying consent/contact sensitivity; hidden from viewers.
SENSITIVE_ENTITY_TYPES = {
    "participant_contact_record", "consent_record", "consent_choice",
    "release_document",
}


def can(role: str, permission: str) -> bool:
    table = {
        "project:write": PROJECT_WRITE_ROLES,
        "project:members_manage": ADMIN_ROLES,
        "participant:write": PARTICIPANT_WRITE_ROLES,
        "participant:sensitive_read": SENSITIVE_READ_ROLES,
        "consent:write": PARTICIPANT_WRITE_ROLES,
        "consent:confirm": CONSENT_CONFIRM_ROLES,
        "review:decide": REVIEW_DECIDE_ROLES,
        "review:resolve": REVIEW_RESOLVE_ROLES,
        "story:write": STORY_WRITE_ROLES,
        "task:write": TASK_WRITE_ROLES,
        "project:read": READ_ROLES,
    }
    allowed = table.get(permission)
    return bool(allowed) and role in allowed
