"""Seed the synthetic 'Beyond the Silence' demo scenario (fictional data only).

Creates: 6 demo users, project, memberships (owner/producer/director/editor/
care_lead/viewer), one participant, one confirmed consent record v1
(interview + appearance agreed; promotional trailer & voice reconstruction NOT
discussed), one story element, one encrypted contact record.

Idempotent by project title. Prints the created ids at the end.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import uuid
from datetime import UTC

from app.core.config import get_settings
from app.core.database import get_session_factory
from app.core.security import encrypt_secret
from app.models import (
    ConsentChoice,
    ConsentRecord,
    Participant,
    ParticipantContactRecord,
    Project,
    ProjectMembership,
    StoryElement,
    User,
)

PROJECT_TITLE = "Beyond the Silence"

USERS = [
    ("oscar@example.com", "Oscar Owner", "project_owner"),
    ("priya@example.com", "Priya Producer", "producer"),
    ("dana@example.com", "Dana Director", "director"),
    ("eli@example.com", "Eli Editor", "editor"),
    ("nora@example.com", "Nora Care Lead", "participant_care_lead"),
    ("vera@example.com", "Vera Viewer", "viewer"),
]


def main() -> int:
    from app.core.database import system_context
    with system_context():  # trusted seed scope (creates rows across all tables)
        return _seed()


def _seed() -> int:
    settings = get_settings()
    if settings.auth_provider != "dev":
        print("Refusing: seed script is for local dev (AUTH_PROVIDER=dev).", file=sys.stderr)
        return 2
    session = get_session_factory()()
    try:
        existing = session.query(Project).filter(Project.title == PROJECT_TITLE).first()
        if existing:
            print(f"Project already seeded: {existing.id}")
            return 0

        users = {}
        for email, name, _role in USERS:
            u = session.query(User).filter(User.email == email, User.auth_provider == "dev").first()
            if u is None:
                u = User(email=email, full_name=name, auth_provider="dev",
                         provider_user_id=str(uuid.uuid4()), account_status="active")
                session.add(u)
            users[email] = u
        session.flush()

        owner = users["oscar@example.com"]
        project = Project(
            title=PROJECT_TITLE,
            description="A fictional documentary about a river-restoration volunteer, following one season of work and memory.",
            purpose="Portrait of community-led river restoration",
            themes=["environment", "memory", "community"],
            intended_audiences=["festival", "public broadcast"],
            distribution_plan="Festival premiere, then public-service broadcast",
            created_by=owner.id, status="active",
        )
        session.add(project)
        session.flush()

        for email, _name, role in USERS:
            session.add(ProjectMembership(project_id=project.id, user_id=users[email].id,
                                          role=role, membership_status="active",
                                          invited_by=owner.id))
        session.flush()

        participant = Participant(
            project_id=project.id,
            display_name="Amara Okoro (fictional)",
            preferred_language="en",
            preferred_contact_method="email",
            accessibility_requirements={"captions": True, "large_print_materials": True},
            privacy_preferences={"no_home_address_filming": True},
        )
        session.add(participant)
        session.flush()

        session.add(ParticipantContactRecord(
            participant_id=participant.id,
            contact_type="email",
            encrypted_contact_data=encrypt_secret("amara.okoro@fictional.example.com"),
        ))

        from datetime import datetime
        now = datetime.now(UTC)
        # Fully construct the confirmed record in ONE insert — confirmed rows are
        # immutable by trigger, so they can never be patched afterwards.
        record = ConsentRecord(
            participant_id=participant.id, project_id=project.id, version_number=1,
            record_status="confirmed", source_type="verbal_recorded",
            explanation="Recorded on 2026-09-12; participant confirmed on camera.",
            recorded_by=owner.id, participant_confirmation="confirmed",
            confirmed_at=now,
        )
        session.add(record)
        session.flush()
        record.choices = [
            ConsentChoice(category="interview_recording", choice="agreed",
                          explanation="Agreed to be interviewed on camera",
                          evidence_reference="release-form:A-01#interview",
                          source_type="verbal_recorded", confirmed_by=owner.id, confirmed_at=now),
            ConsentChoice(category="documentary_appearance", choice="agreed",
                          explanation="Agreed to appear in the documentary",
                          evidence_reference="release-form:A-01#appearance",
                          source_type="verbal_recorded", confirmed_by=owner.id, confirmed_at=now),
        ]

        session.add(StoryElement(
            project_id=project.id,
            title="The riverbed at dawn",
            scene_reference="SCENE-04",
            description="Amara walks the exposed riverbed before first light; voiceover about the flood of 2019.",
            identifying_details=["voice print", "distinctive gait", "scar on left hand"],
            sensitivity_level="highly_sensitive",
            created_by=users["dana@example.com"].id,
        ))
        session.commit()

        print("Seeded synthetic demo data:")
        print(f"  project_id       = {project.id}")
        print(f"  participant_id   = {participant.id}")
        print(f"  consent_record   = {record.id} (v1, confirmed)")
        print("  users            = oscar/priya/dana/eli/nora/vera @example.com")
        print("Mint tokens with:  python scripts/dev_token.py --email oscar@example.com --name \"Oscar Owner\"")
        return 0
    finally:
        session.close()


if __name__ == "__main__":
    raise SystemExit(main())
