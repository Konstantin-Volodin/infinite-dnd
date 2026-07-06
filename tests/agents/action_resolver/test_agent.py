import asyncio

from src.engine.state.models import Character, Location, WorldState
from src.agents.action_resolver.agent import resolve
from src.agents.character.tools import Speak, Wait
from src.agents.dm.tools import Modify


def _state() -> WorldState:
    return WorldState(
        locations={"tavern": Location(id="tavern", connections=[])},
        characters={
            "hero": Character(id="hero", role="warrior", location="tavern", goal="find the ale"),
            "merchant": Character(id="merchant", role="merchant", location="tavern"),
        },
    )


def test_remember_applied_deterministically():
    state = _state()
    tool = Wait(actor="hero", remember="the innkeeper is hiding something")
    asyncio.run(resolve(tool, state))
    assert "the innkeeper is hiding something" in state.characters["hero"].knowledge


def test_new_goal_applied_deterministically():
    state = _state()
    tool = Wait(actor="hero", new_goal="expose the innkeeper")
    asyncio.run(resolve(tool, state))
    assert state.characters["hero"].goal == "expose the innkeeper"
    # a private event should be logged, visible only to this character
    event = state.history[-1]
    assert "expose the innkeeper" in event.text
    assert event.characters == ["hero"]


def test_remember_and_new_goal_together_on_any_tool():
    state = _state()
    tool = Speak(actor="hero", message="I've had enough of this place.", remember="the barkeep flinched at the question", new_goal="leave town")
    asyncio.run(resolve(tool, state))
    hero = state.characters["hero"]
    assert "the barkeep flinched at the question" in hero.knowledge
    assert hero.goal == "leave town"


def test_no_self_updates_when_fields_absent():
    state = _state()
    history_before = len(state.history)
    tool = Wait(actor="hero")
    asyncio.run(resolve(tool, state))
    assert state.characters["hero"].goal == "find the ale"  # unchanged
    assert len(state.history) == history_before + 1  # only the wait event itself


def test_modify_update_relationship_applied():
    state = _state()
    tool = Modify(action="update_relationship", target_id="hero", other_id="merchant", reason="grateful — she healed me")
    result = asyncio.run(resolve(tool, state))
    assert state.characters["hero"].relationships["merchant"] == "grateful — she healed me"
    assert "grateful" in result


def test_modify_update_relationship_unknown_target():
    state = _state()
    tool = Modify(action="update_relationship", target_id="ghost", other_id="merchant", reason="hostile")
    result = asyncio.run(resolve(tool, state))
    assert "Cannot update relationship" in result
    assert "ghost" not in state.characters


def test_modify_update_relationship_missing_fields():
    state = _state()
    tool = Modify(action="update_relationship", target_id="hero", other_id=None, reason=None)
    result = asyncio.run(resolve(tool, state))
    assert "Cannot update relationship" in result
    assert state.characters["hero"].relationships == {}
