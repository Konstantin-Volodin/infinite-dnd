"""Time keeper agent: returns minutes elapsed per event."""

from dataclasses import dataclass

from pydantic_ai import Agent, RunContext, ToolOutput

from src.agents.utils import create_model
from .context import time_keeper_context, time_keeper_system


@dataclass
class TimeKeeperDeps:
    events: list[str]


def estimate_output(
    _: RunContext[TimeKeeperDeps],
    minutes: list[int],
) -> list[int]:
    """accept one integer per event, in order. returns them clamped to [0, 1440]."""
    return [max(0, min(int(m), 1440)) for m in minutes]


agent: Agent[TimeKeeperDeps, list[int]] = Agent(
    model=create_model(),
    deps_type=TimeKeeperDeps,
    output_type=ToolOutput(estimate_output, name="estimate"),
    instructions="You estimate the minutes elapsed for each event based on heuristics.",
)


@agent.system_prompt
def _identity(_: RunContext[TimeKeeperDeps]) -> str:
    return time_keeper_system()


@agent.instructions
def _context(ctx: RunContext[TimeKeeperDeps]) -> str:
    return time_keeper_context(ctx.deps.events)


if __name__ == "__main__":
    import logging

    logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")

    # Conversion is pure; clamping matters.
    assert estimate_output(None, [0, 1, 30, 9999, -5]) == [0, 1, 30, 1440, 0]  # type: ignore[arg-type]
    assert estimate_output(None, []) == []  # type: ignore[arg-type]

    logging.info(f"{__file__} tests completed successfully.")
