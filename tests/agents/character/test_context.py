from src.engine.state.models import Character, Location, WorldState
from src.agents.character.context import character_context


def _state() -> WorldState:
    return WorldState(
        locations={"tavern": Location(id="tavern", connections=[])},
        characters={
            "hero": Character(id="hero", location="tavern", relationships={"merchant": "friendly — she patched me up"}),
            "merchant": Character(id="merchant", role="merchant", location="tavern", relationships={"hero": "wary — caught him stealing"}),
            "bystander": Character(id="bystander", location="tavern"),
        },
    )


def test_context_shows_my_own_relationships():
    state = _state()
    ctx = character_context(state.characters["hero"], state)
    assert "merchant: friendly — she patched me up" in ctx


def test_context_shows_how_present_characters_see_me():
    state = _state()
    ctx = character_context(state.characters["hero"], state)
    assert "thinks of me: wary — caught him stealing" in ctx


def test_context_omits_disposition_when_none_set():
    state = _state()
    ctx = character_context(state.characters["bystander"], state)
    assert "thinks of me" not in ctx
