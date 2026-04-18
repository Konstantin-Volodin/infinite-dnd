"""Quest reviewer agent: emits ModifyIntent(update_quest) based on recent events."""

from dataclasses import dataclass

from pydantic import BaseModel
from pydantic_ai import Agent, RunContext, ToolOutput

from src.engine.state import WorldState
from src.agents.intents import ModifyIntent
from src.agents.utils import create_model
from .context import quest_reviewer_context, quest_reviewer_system


@dataclass
class QuestReviewerDeps:
    state: WorldState


class QuestUpdate(BaseModel):
    quest_id: str
    new_status: str | None = None
    step: str | None = None


def review_output(
    _: RunContext[QuestReviewerDeps],
    updates: list[QuestUpdate],
) -> list[ModifyIntent]:
    """report quest progress justified by recent events. empty list = nothing changed."""
    return [
        ModifyIntent(action="update_quest", target_id=u.quest_id, status=u.new_status, step=u.step)
        for u in updates
        if u.new_status or u.step
    ]


agent: Agent[QuestReviewerDeps, list[ModifyIntent]] = Agent(
    model=create_model(),
    deps_type=QuestReviewerDeps,
    output_type=ToolOutput(review_output, name="review"),
    instructions="You review quest progress against recent events and report status changes.",
)


@agent.system_prompt
def _identity(_: RunContext[QuestReviewerDeps]) -> str:
    return quest_reviewer_system()


@agent.instructions
def _context(ctx: RunContext[QuestReviewerDeps]) -> str:
    return quest_reviewer_context(ctx.deps.state)


if __name__ == "__main__":
    import logging

    logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")

    # The review_output conversion is pure; exercise it without hitting the LLM.
    updates = [
        QuestUpdate(quest_id="find-brother", new_status="completed"),
        QuestUpdate(quest_id="find-alan", step="discovered he works at the docks"),
        QuestUpdate(quest_id="noise"),  # empty — should be dropped
    ]
    intents = review_output(None, updates)  # type: ignore[arg-type]
    assert len(intents) == 2  # empty update filtered out
    assert all(isinstance(i, ModifyIntent) for i in intents)
    assert intents[0].target_id == "find-brother" and intents[0].status == "completed" and intents[0].step is None
    assert intents[1].target_id == "find-alan" and intents[1].status is None and intents[1].step == "discovered he works at the docks"

    assert review_output(None, []) == []  # type: ignore[arg-type]

    logging.info(f"{__file__} tests completed successfully.")
