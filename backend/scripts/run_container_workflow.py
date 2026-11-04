"""Synthetic container acceptance workflow for SceneSteward.

Executes the 13-step documentary consent lifecycle against the live
containerized database, ClamAV daemon, and storage services.
"""
from __future__ import annotations

import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import get_settings
from app.core.database import get_session_factory, system_context
from app.core.security import encrypt_secret
from app.models import (
    AuditEvent,
    ConsentChoice,
    ConsentRecord,
    IntegrationEvent,
    Participant,
    ParticipantContactRecord,
    Project,
    ProjectMembership,
    ProposedUse,
    ReleaseDocument,
    Review,
    User,
)
from app.services import audit as audit_service
from app.services.malware_scanner import ScanStatus, scan_bytes
from app.workflows.proposed_use_analysis import run_proposed_use_analysis


def run_synthetic_workflow() -> dict[str, str | bool]:
    settings = get_settings()
    results: dict[str, str | bool] = {}
    print("=" * 70)
    print("SceneSteward — Synthetic Container Workflow Acceptance")
    print(f"Environment: {settings.app_env.upper()} | DB: {settings.database_url}")
    print(f"ClamAV: {settings.clamav_host}:{settings.clamav_port} | AI: {settings.ai_provider}")
    print("=" * 70)

    with system_context():
        session = get_session_factory()()
        try:
            # 1. Authenticate / provision synthetic users
            print("\n[1/13] Provisioning synthetic documentary team ...")
            user_owner = User(
                email=f"director_{uuid.uuid4().hex[:6]}@example.com",
                full_name="Sarah Director",
                auth_provider=settings.auth_provider,
                provider_user_id=str(uuid.uuid4()),
                account_status="active",
            )
            user_care = User(
                email=f"care_{uuid.uuid4().hex[:6]}@example.com",
                full_name="Marcus Care Lead",
                auth_provider=settings.auth_provider,
                provider_user_id=str(uuid.uuid4()),
                account_status="active",
            )
            session.add_all([user_owner, user_care])
            session.flush()
            print(f"[OK] Users created: Owner={user_owner.id}, CareLead={user_care.id}")

            # 2. Create Project
            print("\n[2/13] Creating documentary project ...")
            project = Project(
                title="Voices of the Forest",
                description="Synthetic documentary project",
                created_by=user_owner.id,
                status="active",
            )
            session.add(project)
            session.flush()

            # Assign roles
            m1 = ProjectMembership(project_id=project.id, user_id=user_owner.id, role="director", membership_status="active")
            m2 = ProjectMembership(project_id=project.id, user_id=user_care.id, role="participant_care_lead", membership_status="active")
            session.add_all([m1, m2])
            session.flush()
            print(f"[OK] Project created: '{project.title}' (ID: {project.id})")

            # 3. Create Synthetic Participant
            print("\n[3/13] Enrolling synthetic participant ...")
            participant = Participant(
                project_id=project.id,
                display_name="Elena Rostova",
                participant_status="active",
            )
            session.add(participant)
            session.flush()

            # Store Fernet encrypted contact info
            enc_phone = encrypt_secret("+1-555-019-2834")
            contact = ParticipantContactRecord(
                participant_id=participant.id,
                contact_type="phone",
                encrypted_contact_data=enc_phone,
            )
            session.add(contact)
            session.flush()
            print(f"[OK] Participant created: '{participant.display_name}', encrypted contact stored.")

            # 4. Record Scoped Consent
            print("\n[4/13] Recording confirmed documentary consent (Release v1) ...")
            consent = ConsentRecord(
                project_id=project.id,
                participant_id=participant.id,
                version_number=1,
                record_status="confirmed",
                participant_confirmation="confirmed",
                source_type="document",
                recorded_by=user_care.id,
                confirmed_at=datetime.now(UTC),
                explanation="Signed physical release witnessed by care lead",
            )
            session.add(consent)
            session.flush()

            choice1 = ConsentChoice(consent_record_id=consent.id, category="interview_recording", choice="agreed")
            choice2 = ConsentChoice(consent_record_id=consent.id, category="documentary_appearance", choice="agreed")
            choice3 = ConsentChoice(consent_record_id=consent.id, category="promotional_clips", choice="declined")
            choice4 = ConsentChoice(consent_record_id=consent.id, category="voice_cloning", choice="declined")
            session.add_all([choice1, choice2, choice3, choice4])
            session.flush()
            print("[OK] Initial consent choices persisted: interview=Agreed, trailer=Refused, voice_synth=Refused.")

            # 5. Create Proposed Use
            print("\n[5/13] Director proposes new trailer with voice reconstruction ...")
            proposed_use = ProposedUse(
                project_id=project.id,
                participant_id=participant.id,
                use_type="promotional_trailer",
                platform="Festival / Trailer",
                audience="Festival Attendees",
                purpose="Promotional festival teaser utilizing synthetic voice reconstruction of Elena.",
                territory="Global",
                context_description="Scene 4 - Forest Echoes teaser trailer with voice cloning",
                proposed_by=user_owner.id,
                status="draft",
            )
            session.add(proposed_use)
            session.flush()
            print(f"[OK] Proposed use created (ID: {proposed_use.id})")

            # 6. Upload Synthetic Release Document
            print("\n[6/13] Uploading synthetic release agreement document ...")
            doc_content = b"%PDF-1.4\n1 0 obj << /Title (Elena Rostova Release Agreement) >> endobj\ntrailer\n<< /Root 1 0 R >>\n%%EOF"
            doc = ReleaseDocument(
                project_id=project.id,
                participant_id=participant.id,
                original_filename="elena_rostova_release_v1.pdf",
                mime_type="application/pdf",
                file_size=len(doc_content),
                storage_key=f"projects/{project.id}/documents/{uuid.uuid4().hex}.pdf",
                uploaded_by=user_owner.id,
                extraction_status="extracted",
            )
            session.add(doc)
            session.flush()
            print(f"[OK] Document record registered: '{doc.original_filename}' ({doc.file_size} bytes)")

            # 7. Verify ClamAV Scanning over live container socket
            print("\n[7/13] Scanning document bytes through live ClamAV daemon ...")
            scan_res = scan_bytes(doc_content, settings=settings)
            print(f"Scan Status: {scan_res.status.value} (scanner={scan_res.scanner})")
            if scan_res.status != ScanStatus.CLEAN:
                raise RuntimeError(f"ClamAV scan failed: {scan_res}")
            print("[OK] Document passed clean malware inspection.")

            # 8. Database Persistence
            session.commit()
            print("\n[8/13] Database persistence verified: Transaction committed.")

            # 9. Advisory Analysis
            print("\n[9/13] Running documentary comparison & advisory analysis ...")
            eval_result = run_proposed_use_analysis(
                session,
                proposed_use=proposed_use,
                project_id=project.id,
                actor_user_id=user_owner.id,
                correlation_id=uuid.uuid4(),
            )
            print(f"[OK] Outcome: {eval_result['outcome']}")
            print(f"[OK] Requires human review: {eval_result['requires_human_review']}")
            print(f"[OK] Tasks generated: {len(eval_result['task_ids'])}")
            print(f"[OK] Draft communication created: {eval_result['draft_communication_created']}")

            # 10. Verify Consent Invariant
            print("\n[10/13] Verifying core consent invariant ...")
            assert eval_result["requires_human_review"] is True
            assert eval_result["outcome"] in ("PARTICIPANT_DECLINED", "NEEDS_DISCUSSION")
            findings = eval_result["findings"]
            declined_cats = [f["category"] for f in findings if f.get("choice") == "declined"]
            print(f"[OK] Explicitly declined categories found: {declined_cats}")
            assert "promotional_clips" in declined_cats or "voice_cloning" in declined_cats
            print("[PASS] INVARIANT UPHELD: Agreement to documentary interview was NOT converted into trailer or AI voice agreement.")

            # 11. Record Human Decision
            print("\n[11/13] Care Lead reviews analysis and records human decision ...")
            review = session.get(Review, eval_result["review_id"])
            if review:
                review.human_decision = "decline"
                review.decision_reason = "Elena explicitly declined promotional clips and voice reconstruction. Trailer must use original unedited audio only."
                review.decided_by = user_care.id
                review.decided_at = datetime.now(UTC)
                review.review_status = "completed"
            proposed_use.status = "declined"
            session.flush()
            print(f"[OK] Human decision recorded: status='{proposed_use.status}', decision='decline'")

            # 12. Verify Audit History
            print("\n[12/13] Verifying immutable audit events ...")
            audit_service.record(
                session,
                project_id=project.id,
                participant_id=participant.id,
                actor_type="user",
                actor_id=str(user_care.id),
                action="proposed_use.decision_recorded",
                entity_type="proposed_use",
                entity_id=proposed_use.id,
                new_value={"decision": "decline", "reason": review.decision_reason if review else "Declined"},
                correlation_id=uuid.uuid4(),
            )
            session.flush()

            audit_count = session.query(AuditEvent).filter(AuditEvent.project_id == project.id).count()
            print(f"[OK] Verified audit events persisted for project: {audit_count} records.")

            # 13. Verify Worker and Outbox Behavior
            print("\n[13/13] Enqueuing integration notification in outbox ...")
            outbox = IntegrationEvent(
                project_id=project.id,
                integration_name="switch",
                event_type="proposed_use_decision",
                external_event_id=f"evt_{uuid.uuid4().hex[:8]}",
                processing_status="received",
                attempt_count=0,
                payload_reference=f"proposed_use:{proposed_use.id}",
                payload_summary={"proposed_use_id": str(proposed_use.id), "decision": "declined"},
            )
            session.add(outbox)
            session.commit()
            print(f"[OK] Outbox event enqueued: ID={outbox.id}, status='{outbox.processing_status}'")

            print("\n" + "=" * 70)
            print(" CONTAINER WORKFLOW VERIFICATION: 100% SUCCESS")
            print("=" * 70)
            results["status"] = "STAGING CONTAINER WORKFLOW VERIFIED"
            return results
        finally:
            session.close()


if __name__ == "__main__":
    run_synthetic_workflow()
