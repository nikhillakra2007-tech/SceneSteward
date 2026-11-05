"""Authentication endpoints. Tokens come from the configured provider;
logout is client-side token discard (+ provider-specific revocation when applicable)."""
from __future__ import annotations

import uuid

from fastapi import APIRouter
from sqlalchemy import select

from app.api.dependencies import CurrentUser, DbSession
from app.core.config import get_settings
from app.core.exceptions import PermissionDenied
from app.core.security import mint_dev_token
from app.models import Project, ProjectMembership, User
from app.schemas.auth import DevTokenRequest, LogoutResponse, MembershipSummary, MeResponse, TokenResponse

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


@router.post("/dev-token", response_model=TokenResponse)
def create_dev_token(payload: DevTokenRequest, db: DbSession) -> TokenResponse:
    settings = get_settings()
    if settings.auth_provider != "dev":
        raise PermissionDenied("Dev login endpoint is disabled outside dev auth provider")

    email = str(payload.email).strip().lower()
    user = db.execute(
        select(User).where(User.email == email, User.auth_provider == "dev")
    ).scalar_one_or_none()

    if user is None:
        user = User(
            email=email,
            full_name=payload.name.strip(),
            auth_provider="dev",
            provider_user_id=str(uuid.uuid4()),
            account_status="active",
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    token = mint_dev_token(
        user_id=user.provider_user_id,
        email=user.email,
        full_name=user.full_name,
        settings=settings,
        ttl_seconds=86400,
    )
    return TokenResponse(access_token=token, token_type="bearer")

