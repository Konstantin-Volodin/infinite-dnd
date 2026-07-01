"""Quest reviewer agent: emits Modify(update_quest) tools based on recent events."""

from dataclasses import dataclass

from pydantic import BaseModel
from pydantic_ai import Agent, RunContext, ToolOutput

from src.engine.state import WorldState
from src.agents.utils import create_model
from .context import quest_reviewer_context, quest_reviewer_system
from .tools import Modify


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
) -> list[Modify]:
    """report quest progress justified by recent events. empty list = nothing changed."""
    return [
        Modify(action="update_quest", target_id=u.quest_id, status=u.new_status, step=u.step)
        for u in updates
        if u.new_status or u.step
    ]


agent: Agent[QuestReviewerDeps, list[Modify]] = Agent(
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
