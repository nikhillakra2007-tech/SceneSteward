"""End-to-end real Switch verification: invoke the SceneSteward agent worker with a
synthetic inbound event shaped like a real Switch room message, run the full
clearance workflow against PostgreSQL, and verify the assessment is posted back
to the ACTUAL Switch room.

This is a "simulated receive" (the human's Switch post is simulated because the
admin user is not a room member and cannot post via the Gateway without re-
creating the room). The processing, database reads/writes, and Switch message
post are all real.
"""
from __future__ import annotations

import json
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.database import get_session_factory, system_context
from app.integrations.switch.agent_worker import SwitchAgentWorker
from app.models import ConsentRecord, Participant, Project, ProposedUse, Review

ROOM_ID = "aeec10b9-781c-4625-a07a-692279393943"


def main() -> int:
    db = get_session_factory()()
    try:
        with system_context():
            raw = {
                "type": "message",
                "event_id": f"e2e-{uuid.uuid4()}",
                "data": {
                    "room_id": ROOM_ID,
                    "sender": "Elena Director (human)",
                    "body": "SceneSteward, please review footage F-104 from project P-001 for documentary trailer use.",
                },
            }
            worker = SwitchAgentWorker()
            result = worker.process_room_message(db, raw)
            print("WORKER RESULT:", json.dumps(result, indent=2, default=str))
            db.commit()

            # Verify DB state
            project = db.execute(__import__("sqlalchemy").select(Project).where(Project.title.ilike("%Watershed%"))).scalars().first()
            print("PROJECT:", project.id if project else None, project.title if project else None)
            if project:
                participant = db.execute(__import__("sqlalchemy").select(Participant).where(Participant.project_id == project.id)).scalars().first()
                print("PARTICIPANT:", participant.id if participant else None, participant.display_name if participant else None)
                consent = db.execute(__import__("sqlalchemy").select(ConsentRecord).where(ConsentRecord.participant_id == participant.id)).scalars().first() if participant else None
                print("CONSENT:", consent.id if consent else None, "version", consent.version if consent else None)
                pu = db.execute(__import__("sqlalchemy").select(ProposedUse).where(ProposedUse.project_id == project.id)).scalars().first() if project else None
                print("PROPOSED USE:", pu.id if pu else None, pu.status if pu else None, pu.outcome if hasattr(pu, 'outcome') else '')
                review = db.execute(__import__("sqlalchemy").select(Review).where(Review.proposed_use_id == pu.id)).scalars().first() if pu else None
                print("REVIEW:", review.id if review else None, review.review_status if review else None, review.human_decision if review else None)
            return 0 if result.get("status") == "clearance_analyzed" else 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())