import asyncio

from src.engine.state.models import Character, Location, WorldState
from src.agents.action_resolver.agent import resolve
from src.agents.character.tools import Check, Speak, Wait
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


class _Rolls:
    def __init__(self, *values: int):
        self.values = iter(values)

    def randint(self, _low: int, _high: int) -> int:
        return next(self.values)


def test_check_resolution_records_concise_roll_history():
    state = _state()
    result = asyncio.run(resolve(
        Check(actor="hero", ability="dexterity", description="picks the cellar lock", difficulty=14, modifier=2),
        state,
        rng=_Rolls(12),
    ))
    assert result == "hero succeeds: picks the cellar lock [dexterity; 12+2=14 vs DC 14]."
    assert state.history[-1].text == result
    assert state.history[-1].characters == ["hero"]


def test_contested_check_records_both_characters():
    state = _state()
    result = asyncio.run(resolve(Check(
        actor="hero", ability="charisma", description="bluffs the merchant",
        opponent="merchant", modifier=1, opposing_modifier=2,
    ), state, rng=_Rolls(16, 10)))
    assert "16+1=17 vs merchant 10+2=12" in result
    assert state.history[-1].characters == ["hero", "merchant"]
