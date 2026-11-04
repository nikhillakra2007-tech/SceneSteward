"""Proposed-use analysis workflow.

Order: verify relationships → load confirmed consent → normalise → compare →
persist analysis → create human review + tasks → run agents → notify Switch.
Agent results are recorded; they never change consent or decide the outcome.
Failures in Switch/AI do not roll back persisted records.
"""
from __future__ import annotations

import logging
import uuid
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.agents import PIPELINE_ORDER, agent_for
from app.core.exceptions import NotFoundError
from app.models import (
    IntegrationEvent,
    Participant,
    ParticipantCommunication,
    ProposedUse,
    ProposedUseAnalysis,
    Review,
    StoryElement,
    SwitchRoomLink,
)
from app.services import audit, consent_service, tasks
from app.services.agent_context import build_context
from app.services.consent_comparison import (
    ENGINE_VERSION,
    compare_with_confirmed_record,
    normalize_proposed_use,
)

logger = logging.getLogger("scenesteward.workflows.analysis")


def run_proposed_use_analysis(
    db: Session,
    *,
    proposed_use: ProposedUse,
    project_id: uuid.UUID,
    actor_user_id: uuid.UUID | None,
    correlation_id: uuid.UUID,
) -> dict[str, Any]:
    if proposed_use.project_id != project_id:
        raise NotFoundError("Proposed use not found")

    participant = db.get(Participant, proposed_use.participant_id)
    if participant is None or participant.project_id != project_id:
        raise NotFoundError("Participant not found")
    story_element = db.get(StoryElement, proposed_use.story_element_id) if proposed_use.story_element_id else None

    # 1–4. Confirmed consent + deterministic comparison
    latest = consent_service.get_latest_confirmed(db, participant.id)
    history = consent_service.get_confirmed_history(db, participant.id)
    normalized = normalize_proposed_use(proposed_use)
    result = compare_with_confirmed_record(latest, history, normalized)

    # 5. Persist the analysis (append-only)
    analysis = ProposedUseAnalysis(
        proposed_use_id=proposed_use.id,
        outcome=result.outcome,
        findings=result.findings,
        matched_consent_record_ids=result.matched_consent_record_ids,
        engine_version=ENGINE_VERSION,
        created_by_type="engine",
    )
    db.add(analysis)

    proposed_use.status = "analysis_complete"
    proposed_use.version += 1

    missing = sorted({f["category"] for f in result.findings if f.get("choice") is None and f.get("category")})
    declined = sorted({f["category"] for f in result.findings if f.get("choice") == "declined" and f.get("category")})
    evidence_refs = sorted({ref for f in result.findings for ref in f.get("source_references", [])})

    # 6. Human review (unassigned — any authorised decider can claim it)
    review = Review(
        project_id=project_id,
        proposed_use_id=proposed_use.id,
        reviewer_type="human",
        review_status="pending",
        findings=result.findings,
        evidence_references=[{"ref": r} for r in evidence_refs],
        uncertainty=None if result.outcome == "RECORDED_CHOICE_MATCH" else "Proposed use exceeds or outruns the confirmed record",
    )
    db.add(review)
    db.flush()

    # 7. Human-owned tasks
    created_tasks = []
    if missing:
        task = tasks.create_task(
            db, project_id=project_id, participant_id=participant.id,
            task_type="unresolved_permission",
            title=f"Discuss with participant before use: {', '.join(missing[:4])}",
            description="Confirmed consent does not cover this proposed use. Hold a discussion; record outcomes as a NEW consent version.",
            priority="high", source_type="proposed_use", source_id=proposed_use.id,
            created_by_actor_type="system",
        )
        created_tasks.append(task)
    if declined:
        task = tasks.create_task(
            db, project_id=project_id, participant_id=participant.id,
            task_type="unresolved_permission",
            title=f"BLOCKED — participant declined: {', '.join(declined[:4])}",
            description="Remove the refused categories from the plan. Do not attempt to re-secure consent for this version.",
            priority="urgent", source_type="proposed_use", source_id=proposed_use.id,
            created_by_actor_type="system",
        )
        created_tasks.append(task)
    review_task = tasks.create_task(
        db, project_id=project_id, participant_id=participant.id,
        task_type="review",
        title=f"Human review required — proposed use {result.outcome}",
        description="Review the analysis, talk with the participant if needed, then record a formal decision in SceneSteward.",
        priority="high" if result.outcome != "RECORDED_CHOICE_MATCH" else "normal",
        source_type="review", source_id=review.id,
        created_by_actor_type="system",
    )
    created_tasks.append(review_task)

    actor = ("user", str(actor_user_id)) if actor_user_id else ("system", "scenesteward")
    audit.record(
        db, project_id=project_id, participant_id=participant.id,
        actor_type=actor[0], actor_id=actor[1],
        action="proposed_use.analysed",
        entity_type="proposed_use", entity_id=proposed_use.id,
        new_value={"outcome": result.outcome, "analysis_id": str(analysis.id),
                   "missing_categories": missing, "declined_categories": declined},
        correlation_id=correlation_id,
    )
    from app.events import publish
    publish("proposed_use.analysed", correlation_id=correlation_id,
            project_id=str(project_id), proposed_use_id=str(proposed_use.id), outcome=result.outcome)

    # 8. Agents (independent; failures are recorded, never rolled back)
    agent_outputs = run_agents(
        db, proposed_use=proposed_use, project_id=project_id, participant=participant,
        story_element=story_element, latest=latest, history=history,
        analysis_findings=result.findings, analysis_outcome=result.outcome,
        actor_user_id=actor_user_id, correlation_id=correlation_id,
    )

    # 8b. Draft communication (NEVER sent; requires explicit human approval later)
    coordinator_output = next(
        (o.get("output") for o in agent_outputs
         if o["agent_name"] == "production_coordinator" and o.get("output")),
        None,
    )
    draft_created = False
    if coordinator_output:
        actions = coordinator_output.get("recommended_actions", [])
        draft = (
            "Draft for a participant conversation (NOT sent — human approval required before sending):\n\n"
            "Thank you for sharing your story with us. Before we can go ahead with the planned use, "
            "we want to check in with you. The production would like to discuss:\n\n"
            + "\n".join(f"  {i+1}. {a}" for i, a in enumerate(actions[:8]))
            + "\n\nYou may agree, decline, or ask for more information about any of these. "
              "Nothing will go ahead without your clear, recorded decision."
        )
        db.add(ParticipantCommunication(
            project_id=project_id,
            participant_id=participant.id,
            communication_type="email",
            subject="A conversation about how your story will be used",
            draft_content=draft,
            communication_status="draft",
            created_by=actor_user_id or proposed_use.proposed_by,
        ))
        draft_created = True

    # 9. Switch notification (best-effort; failures recorded, never fatal)
    switch_note = maybe_notify_switch(
        db, project_id=project_id, participant_id=participant.id,
        proposed_use=proposed_use, result=result, missing=missing, declined=declined,
        correlation_id=correlation_id,
    )

    return {
        "analysis_id": analysis.id,
        "outcome": result.outcome,
        "findings": result.findings,
        "matched_consent_record_ids": result.matched_consent_record_ids,
        "review_id": review.id,
        "task_ids": [t.id for t in created_tasks],
        "agent_run_ids": [r["run_id"] for r in agent_outputs],
        "draft_communication_created": draft_created,
        "switch": switch_note,
        "requires_human_review": True,
    }


def run_agents(db, *, proposed_use, project_id, participant, story_element,
               latest, history, analysis_findings, analysis_outcome,
               actor_user_id, correlation_id) -> list[dict]:
    outputs: dict[str, Any] = {}
    runs: list[dict] = []
    actor = ("user", str(actor_user_id)) if actor_user_id else ("system", "scenesteward")

    for name in PIPELINE_ORDER:
        document_text = None  # document-driven extraction runs via the documents pipeline
        context = build_context(
            agent_name=name,
            project_id=project_id,
            participant_id=participant.id,
            proposed_use=proposed_use,
            story_element=story_element,
            latest_confirmed=latest,
            confirmed_history=history,
            analysis_findings=analysis_findings,
            analysis_outcome=analysis_outcome,
            participant_private={
                "accessibility_requirements": participant.accessibility_requirements,
                "preferred_language": participant.preferred_language,
                "privacy_preferences": participant.privacy_preferences,
            },
            document_text=document_text,
            agent_outputs=outputs,
        )
        run = agent_for(name).execute(db, context=context, actor=actor, correlation_id=correlation_id)
        outputs[name] = run.output_data or {"execution_status": run.execution_status, "error_code": run.error_code}
        runs.append({"run_id": run.id, "agent_name": name, "status": run.execution_status,
                     "output": run.output_data})
    return runs


def maybe_notify_switch(db, *, project_id, participant_id, proposed_use, result,
                        missing, declined, correlation_id) -> dict[str, str]:
    link = (
        db.query(SwitchRoomLink)
        .filter(SwitchRoomLink.project_id == project_id,
                SwitchRoomLink.participant_id == participant_id,
                SwitchRoomLink.room_type == "participant_review")
        .first()
        or db.query(SwitchRoomLink).filter(SwitchRoomLink.project_id == project_id,
                                           SwitchRoomLink.room_type == "project").first()
    )
    if link is None:
        return {"status": "not_linked", "detail": "No Switch room linked for this scope; nothing sent."}

    from app.integrations.switch import get_switch_adapter, switch_status
    status = switch_status()
    if status.status != "configured_verified":
        return {"status": status.status, "detail": status.detail or "Switch not verified; nothing sent."}

    adapter = get_switch_adapter()
    summary = {
        "proposed_use_id": str(proposed_use.id),
        "outcome": result.outcome,
        "missing_categories": missing,
        "declined_categories": declined,
    }
    send = adapter.send_review_context(room_id=link.switch_room_id, summary=summary,
                                       correlation_id=str(correlation_id))
    evt = IntegrationEvent(
        integration_name="switch",
        event_type="review_context",
        external_event_id=send.event_id or f"send:{correlation_id}",
        correlation_id=correlation_id,
        payload_reference=f"proposed_use:{proposed_use.id}",
        payload_summary={"room_id": link.switch_room_id, "outcome": result.outcome},
        processing_status="processed" if send.ok else "failed",
        attempt_count=1,
        last_error=None if send.ok else (send.error_code or "send_failed"),
    )
    try:
        with db.begin_nested():
            db.add(evt)
            db.flush()
    except IntegrityError:
        logger.info("switch review-context notification already recorded for correlation %s", correlation_id)
    if not send.ok:
        from app.integrations.notifications import notify_integration_failure
        notify_integration_failure(
            db, project_id=project_id, participant_id=participant_id,
            title="Switch notification failed",
            detail=f"error_code={send.error_code}; correlation_id={correlation_id}",
            correlation_id=correlation_id,
        )
        from app.events import publish
        publish("switch.delivery_failed", correlation_id=correlation_id,
                proposed_use_id=str(proposed_use.id), error_code=send.error_code)
    else:
        from app.events import publish
        publish("switch.delivery_succeeded", correlation_id=correlation_id,
                proposed_use_id=str(proposed_use.id))
    return {"status": "sent" if send.ok else "failed", "detail": send.error_code or ""}
