"""Agent registry + orchestration order (consent → story → advocate → ethics → coordinator)."""
from app.agents.consent_analyst import ConsentAnalystAgent
from app.agents.ethics_reviewer import EthicsReviewerAgent
from app.agents.participant_advocate import ParticipantAdvocateAgent
from app.agents.production_coordinator import ProductionCoordinatorAgent
from app.agents.story_change_analyst import StoryChangeAnalystAgent

AGENT_CLASSES = {
    "consent_analyst": ConsentAnalystAgent,
    "story_change_analyst": StoryChangeAnalystAgent,
    "participant_advocate": ParticipantAdvocateAgent,
    "ethics_reviewer": EthicsReviewerAgent,
    "production_coordinator": ProductionCoordinatorAgent,
}

PIPELINE_ORDER = ["consent_analyst", "story_change_analyst", "participant_advocate", "ethics_reviewer", "production_coordinator"]


def agent_for(name: str):
    cls = AGENT_CLASSES.get(name)
    if cls is None:
        raise KeyError(f"Unknown agent: {name}")
    return cls()
