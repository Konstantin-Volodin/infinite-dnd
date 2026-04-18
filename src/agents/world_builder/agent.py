"""World builder agent: extracts new named entities from recent events as Create tools."""

from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel
from pydantic_ai import Agent, RunContext, ToolOutput

from src.engine.state import WorldState
from src.agents.utils import create_model
from .context import world_builder_context, world_builder_system
from .tools import Create


@dataclass
class WorldBuilderDeps:
    state: WorldState


class NewEntity(BaseModel):
    type: Literal["location", "npc", "item", "quest"]
    name: str
    description: str = ""
    location: str | None = None
    role: str | None = None
    goal: str | None = None
    owner: str | None = None


def enrich_output(
    _: RunContext[WorldBuilderDeps],
    entities: list[NewEntity],
) -> list[Create]:
    """register entities revealed by the recent events. empty list = nothing new."""
    return [
        Create(
            type=e.type,
            name=e.name,
            description=e.description,
            location=e.location,
            role=e.role,
            goal=e.goal,
            owner=e.owner,
        )
        for e in entities
        if e.name.strip()
    ]


agent: Agent[WorldBuilderDeps, list[Create]] = Agent(
    model=create_model(),
    deps_type=WorldBuilderDeps,
    output_type=ToolOutput(enrich_output, name="enrich"),
    instructions="You extract newly-revealed named entities from recent events.",
)


@agent.system_prompt
def _identity(_: RunContext[WorldBuilderDeps]) -> str:
    return world_builder_system()


@agent.instructions
def _context(ctx: RunContext[WorldBuilderDeps]) -> str:
    return world_builder_context(ctx.deps.state)


if __name__ == "__main__":
    import logging

    logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")

    entities = [
        NewEntity(type="npc", name="Dockmaster Alan", description="a shady port official", location="docks", role="dockmaster"),
        NewEntity(type="location", name="The Docks", description="busy port district", location="market-square"),
        NewEntity(type="item", name="", description="nameless item — should be filtered"),
        NewEntity(type="quest", name="Find the Vault", description="locate the cold-hearth vault", owner="alice"),
    ]
    tools = enrich_output(None, entities)  # type: ignore[arg-type]
    assert len(tools) == 3  # empty-name filtered
    assert all(isinstance(t, Create) for t in tools)
    assert tools[0].type == "npc" and tools[0].role == "dockmaster"
    assert tools[1].type == "location" and tools[1].location == "market-square"
    assert tools[2].type == "quest" and tools[2].owner == "alice"

    assert enrich_output(None, []) == []  # type: ignore[arg-type]

    logging.info(f"{__file__} tests completed successfully.")
