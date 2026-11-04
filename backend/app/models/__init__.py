"""Model imports so Alembic and tests see every table."""
from app.models.agents import AgentRun
from app.models.audit import AuditEvent
from app.models.base import Base
from app.models.communications import ParticipantCommunication
from app.models.consent import ConsentChoice, ConsentRecord
from app.models.documents import DocumentPage, ReleaseDocument
from app.models.integrations import IntegrationEvent
from app.models.participants import Participant, ParticipantContactRecord
from app.models.projects import Project, ProjectMembership
from app.models.reviews import Review
from app.models.story import StoryElement
from app.models.switch import SwitchRoomLink
from app.models.tasks import Task
from app.models.users import User
from app.models.uses import ProposedUse, ProposedUseAnalysis

__all__ = [
    "AgentRun",
    "AuditEvent",
    "Base",
    "ConsentChoice",
    "ConsentRecord",
    "DocumentPage",
    "IntegrationEvent",
    "Participant",
    "ParticipantCommunication",
    "ParticipantContactRecord",
    "Project",
    "ProjectMembership",
    "ProposedUse",
    "ProposedUseAnalysis",
    "ReleaseDocument",
    "Review",
    "StoryElement",
    "SwitchRoomLink",
    "Task",
    "User",
]
