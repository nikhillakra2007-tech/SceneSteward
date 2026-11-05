"""FastAPI dependencies: authentication, membership, role gates, resource scope.

Authorization order (never skipped):
  1. valid bearer token  2. existing, active user  3. active project membership
  4. role permission     5. resource belongs to project/participant
"""
from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import Depends, Header, Path
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db, set_identity
from app.core.exceptions import NotFoundError, PermissionDenied, Unauthenticated
from app.core.security import decode_token
from app.models import Participant, Project, ProjectMembership, User

DbSession = Annotated[Session, Depends(get_db)]


def get_current_user(
    db: DbSession,
    authorization: Annotated[str | None, Header()] = None,
) -> User:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise Unauthenticated("Missing bearer token")
    claims = decode_token(authorization.split(" ", 1)[1].strip())

    stmt = select(User).where(
        User.auth_provider == claims.provider,
        User.provider_user_id == claims.subject,
    )
    user = db.execute(stmt).scalar_one_or_none()
    if user is None:
        if claims.provider == "supabase" and claims.email:
            # JIT provisioning from a verified identity (first sign-in).
            user = User(
                email=claims.email.lower(),
                full_name=(claims.full_name or claims.email.split("@", 1)[0])[:200],
                auth_provider=claims.provider,
                provider_user_id=claims.subject,
                account_status="active",
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        else:
            raise Unauthenticated("Unknown user; provision the account first", code="user_not_provisioned")
    if user.account_status != "active":
        raise PermissionDenied("Account is not active", code="account_inactive")
    set_identity(user.id, db)
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def get_optional_user(
    db: DbSession,
    authorization: Annotated[str | None, Header()] = None,
) -> User | None:
    if not authorization or not authorization.lower().startswith("bearer "):
        return None
    try:
        return get_current_user(db, authorization)
    except (Unauthenticated, PermissionDenied):
        return None


OptionalUser = Annotated[User | None, Depends(get_optional_user)]


def get_membership(db: Session, project_id: uuid.UUID, user: User) -> ProjectMembership:
    stmt = select(ProjectMembership).where(
        ProjectMembership.project_id == project_id,
        ProjectMembership.user_id == user.id,
    )
    membership = db.execute(stmt).scalar_one_or_none()
    # Do not reveal whether the project exists to non-members.
    if membership is None or membership.membership_status != "active":
        raise NotFoundError("Project not found")
    return membership


def require_membership(project_id: uuid.UUID, db: DbSession, user: CurrentUser) -> ProjectMembership:
    return get_membership(db, project_id, user)


def require_roles(*roles: str):
    def dependency(
        project_id: Annotated[uuid.UUID, Path()],
        db: DbSession,
        user: CurrentUser,
    ) -> ProjectMembership:
        membership = get_membership(db, project_id, user)
        if membership.role not in roles:
            raise PermissionDenied("This role cannot perform that operation")
        return membership
    return dependency


def get_project(db: Session, project_id: uuid.UUID) -> Project:
    project = db.get(Project, project_id)
    if project is None:
        raise NotFoundError("Project not found")
    return project


def get_participant(db: Session, participant_id: uuid.UUID) -> Participant:
    participant = db.get(Participant, participant_id)
    if participant is None:
        raise NotFoundError("Participant not found")
    return participant


def get_project_participant(db: Session, project_id: uuid.UUID, participant_id: uuid.UUID) -> Participant:
    """Fetch a participant AND enforce it belongs to the given project."""
    participant = get_participant(db, participant_id)
    if participant.project_id != project_id:
        # Same not-found semantics: no existence oracle across projects.
        raise NotFoundError("Participant not found")
    return participant


def check_participant_self_access(participant: Participant, user: User) -> bool:
    return participant.user_id is not None and participant.user_id == user.id
