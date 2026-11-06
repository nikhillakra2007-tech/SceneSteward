"""Aggregate /api/v1 router."""
from fastapi import APIRouter

from app.api.v1.endpoints import (
    agents,
    analytics,
    auth,
    communications,
    consent,
    documents,
    integrations,
    metrics,
    participants,
    projects,
    proposed_uses,
    reviews,
    storage_local,
    story_elements,
    switch_rooms,
    tasks,
    timeline,
)

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(projects.router)
api_router.include_router(participants.router)
api_router.include_router(consent.router)
api_router.include_router(documents.router)
api_router.include_router(storage_local.router)
api_router.include_router(story_elements.router)
api_router.include_router(proposed_uses.router)
api_router.include_router(reviews.router)
api_router.include_router(agents.router)
api_router.include_router(timeline.router)
api_router.include_router(tasks.router)
api_router.include_router(integrations.router)
api_router.include_router(switch_rooms.router)
api_router.include_router(metrics.router)
api_router.include_router(communications.router)
api_router.include_router(analytics.router)
