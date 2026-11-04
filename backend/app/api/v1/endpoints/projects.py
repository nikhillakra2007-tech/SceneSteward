"""Projects: CRUD + membership management (owner-managed)."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import func, select

from app.api.dependencies import CurrentUser, DbSession, get_membership, get_project
from app.core import permissions
from app.core.exceptions import ConflictError, NotFoundError, PreconditionFailed
from app.models import Project, ProjectMembership, User
from app.schemas.common import Page
from app.schemas.projects import (
    MemberAdd,
    MemberOut,
    MemberUpdate,
    ProjectCreate,
    ProjectOut,
    ProjectUpdate,
)
from app.services import audit
from app.utils.pagination import PageParams, page_params

router = APIRouter(prefix="/projects", tags=["projects"])


def _out(p: Project) -> ProjectOut:
    return ProjectOut.model_validate(p)


@router.post("", response_model=ProjectOut, status_code=201)
def create_project(payload: ProjectCreate, db: DbSession, user: CurrentUser) -> ProjectOut:
    project = Project(
        title=payload.title.strip(), description=payload.description, purpose=payload.purpose,
        themes=payload.themes, intended_audiences=payload.intended_audiences,
        distribution_plan=payload.distribution_plan, created_by=user.id, status="active",
    )
    db.add(project)
    db.flush()
    db.add(ProjectMembership(project_id=project.id, user_id=user.id, role="project_owner",
                             membership_status="active"))
    audit.record(db, project_id=project.id, participant_id=None,
                 actor_type="user", actor_id=str(user.id),
                 action="project.created", entity_type="project", entity_id=project.id,
                 new_value={"title": project.title})
    db.commit()
    db.refresh(project)
    return _out(project)


@router.get("", response_model=Page[ProjectOut])
def list_projects(db: DbSession, user: CurrentUser, page: Annotated[PageParams, Depends(page_params)]) -> Page[ProjectOut]:
    base = select(Project).join(ProjectMembership, ProjectMembership.project_id == Project.id).where(
        ProjectMembership.user_id == user.id,
        ProjectMembership.membership_status == "active",
        Project.status != "archived",
    )
    total = db.execute(select(func.count()).select_from(base.subquery())).scalar_one()
    rows = db.execute(base.order_by(Project.updated_at.desc()).limit(page.limit).offset(page.offset)).scalars().all()
    return Page(items=[_out(p) for p in rows], total=total, limit=page.limit, offset=page.offset)


@router.get("/{project_id}", response_model=ProjectOut)
def get_project_endpoint(project_id: uuid.UUID, db: DbSession, user: CurrentUser) -> ProjectOut:
    get_membership(db, project_id, user)
    return _out(get_project(db, project_id))


@router.patch("/{project_id}", response_model=ProjectOut)
def update_project(project_id: uuid.UUID, payload: ProjectUpdate, db: DbSession, user: CurrentUser) -> ProjectOut:
    membership = get_membership(db, project_id, user)
    if membership.role not in permissions.PROJECT_WRITE_ROLES:
        from app.core.exceptions import PermissionDenied
        raise PermissionDenied("This role cannot edit the project")
    project = get_project(db, project_id)
    if project.version != payload.expected_version:
        raise ConflictError("Project was modified by another writer; reload and retry", code="version_conflict")
    previous = {"title": project.title, "status": project.status}
    for field in ("title", "description", "purpose", "themes", "intended_audiences", "distribution_plan", "status"):
        value = getattr(payload, field)
        if value is not None:
            setattr(project, field, value)
    project.version += 1
    project.updated_at = datetime.now(UTC)
    audit.record(db, project_id=project.id, participant_id=None,
                 actor_type="user", actor_id=str(user.id),
                 action="project.updated", entity_type="project", entity_id=project.id,
                 previous_value=previous,
                 new_value={k: getattr(project, k) for k in ("title", "status")})
    db.commit()
    db.refresh(project)
    return _out(project)


# --- members ------------------------------------------------------------------

def _member_out(db, membership: ProjectMembership) -> MemberOut:
    user = db.get(User, membership.user_id)
    out = MemberOut.model_validate(membership)
    out.email = user.email if user else None
    out.full_name = user.full_name if user else None
    return out


@router.get("/{project_id}/members", response_model=list[MemberOut])
def list_members(project_id: uuid.UUID, db: DbSession, user: CurrentUser) -> list[MemberOut]:
    get_membership(db, project_id, user)
    rows = db.execute(
        select(ProjectMembership).where(ProjectMembership.project_id == project_id)
        .order_by(ProjectMembership.created_at.asc())
    ).scalars().all()
    return [_member_out(db, m) for m in rows]


@router.post("/{project_id}/members", response_model=MemberOut, status_code=201)
def add_member(project_id: uuid.UUID, payload: MemberAdd, db: DbSession, user: CurrentUser) -> MemberOut:
    membership = get_membership(db, project_id, user)
    if membership.role not in permissions.ADMIN_ROLES:
        from app.core.exceptions import PermissionDenied
        raise PermissionDenied("Only the project owner can invite members")
    email = payload.email.strip().lower()
    target = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
    if target is None:
        raise NotFoundError("No account exists for that email; ask them to sign in once, then invite again")
    existing = db.execute(
        select(ProjectMembership).where(ProjectMembership.project_id == project_id,
                                        ProjectMembership.user_id == target.id)
    ).scalar_one_or_none()
    if existing and existing.membership_status == "active":
        raise ConflictError("User is already a member", code="already_member")
    if existing:  # previously removed/invited → reactivate
        existing.role = payload.role
        existing.membership_status = "active"
        existing.invited_by = user.id
        member = existing
    else:
        member = ProjectMembership(project_id=project_id, user_id=target.id, role=payload.role,
                                   membership_status="active", invited_by=user.id)
        db.add(member)
    audit.record(db, project_id=project_id, participant_id=None,
                 actor_type="user", actor_id=str(user.id),
                 action="member.added", entity_type="project_membership", entity_id=member.id,
                 new_value={"user_id": str(target.id), "role": payload.role})
    db.commit()
    db.refresh(member)
    return _member_out(db, member)


def _count_active_owners(db, project_id: uuid.UUID) -> int:
    return db.execute(
        select(func.count()).select_from(ProjectMembership).where(
            ProjectMembership.project_id == project_id,
            ProjectMembership.role == "project_owner",
            ProjectMembership.membership_status == "active",
        )
    ).scalar_one()


@router.patch("/{project_id}/members/{member_id}", response_model=MemberOut)
def update_member(project_id: uuid.UUID, member_id: uuid.UUID, payload: MemberUpdate,
                  db: DbSession, user: CurrentUser) -> MemberOut:
    membership = get_membership(db, project_id, user)
    if membership.role not in permissions.ADMIN_ROLES:
        from app.core.exceptions import PermissionDenied
        raise PermissionDenied("Only the project owner can change roles")
    member = db.get(ProjectMembership, member_id)
    if member is None or member.project_id != project_id:
        raise NotFoundError("Membership not found")
    demoting_owner = member.role == "project_owner" and (
        (payload.role is not None and payload.role != "project_owner")
        or (payload.membership_status is not None and payload.membership_status != "active")
    )
    if demoting_owner and _count_active_owners(db, project_id) <= 1:
        raise PreconditionFailed("Cannot demote or deactivate the last active project owner",
                                 code="last_owner")
    previous = {"role": member.role, "membership_status": member.membership_status}
    if payload.role is not None:
        member.role = payload.role
    if payload.membership_status is not None:
        member.membership_status = payload.membership_status
    audit.record(db, project_id=project_id, participant_id=None,
                 actor_type="user", actor_id=str(user.id),
                 action="member.updated", entity_type="project_membership", entity_id=member.id,
                 previous_value=previous,
                 new_value={"role": member.role, "membership_status": member.membership_status})
    db.commit()
    db.refresh(member)
    return _member_out(db, member)


@router.delete("/{project_id}/members/{member_id}", status_code=204)
def remove_member(project_id: uuid.UUID, member_id: uuid.UUID, db: DbSession, user: CurrentUser) -> None:
    membership = get_membership(db, project_id, user)
    if membership.role not in permissions.ADMIN_ROLES:
        from app.core.exceptions import PermissionDenied
        raise PermissionDenied("Only the project owner can remove members")
    member = db.get(ProjectMembership, member_id)
    if member is None or member.project_id != project_id:
        raise NotFoundError("Membership not found")
    if member.role == "project_owner" and _count_active_owners(db, project_id) <= 1:
        raise PreconditionFailed("Cannot remove the last active project owner", code="last_owner")
    member.membership_status = "removed"  # soft removal preserves history + audit
    audit.record(db, project_id=project_id, participant_id=None,
                 actor_type="user", actor_id=str(user.id),
                 action="member.removed", entity_type="project_membership", entity_id=member.id,
                 new_value={"user_id": str(member.user_id)})
    db.commit()
