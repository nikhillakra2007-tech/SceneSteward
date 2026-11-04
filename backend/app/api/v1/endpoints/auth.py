"""Authentication endpoints. Tokens come from the configured provider;
logout is client-side token discard (+ provider-specific revocation when applicable)."""
from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import select

from app.api.dependencies import CurrentUser, DbSession
from app.models import Project, ProjectMembership
from app.schemas.auth import LogoutResponse, MembershipSummary, MeResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/me", response_model=MeResponse)
def me(db: DbSession, user: CurrentUser) -> MeResponse:
    stmt = (
        select(ProjectMembership, Project.title)
        .join(Project, Project.id == ProjectMembership.project_id)
        .where(ProjectMembership.user_id == user.id,
               ProjectMembership.membership_status == "active")
        .order_by(Project.title)
    )
    rows = db.execute(stmt).all()
    return MeResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        auth_provider=user.auth_provider,
        account_status=user.account_status,
        last_login_at=user.last_login_at,
        memberships=[
            MembershipSummary(project_id=m.project_id, project_title=title,
                              role=m.role, membership_status=m.membership_status)
            for m, title in rows
        ],
    )


@router.post("/logout", response_model=LogoutResponse)
def logout(user: CurrentUser) -> LogoutResponse:
    # Stateless JWTs cannot be revoked server-side without a denylist;
    # clients must discard the token. Supabase sessions are revoked client-side
    # via supabase.auth.sign_out().
    return LogoutResponse()
