import pytest

from src.engine.state.models import WorldState, Character, CharacterStats
from src.engine.state.operations.character import CharacterOps


@pytest.fixture
def state(locations) -> WorldState:
    return WorldState(
        locations=locations,
        characters={
            "hero": Character(id="hero", role="warrior", location="tavern", inventory=["sword"], stats=CharacterStats(hp=20, max_hp=20, level=1)),
            "merchant": Character(id="merchant", role="shopkeeper", location="tavern", inventory=["potion", "shield"]),
        },
    )


@pytest.fixture
def ops(state) -> CharacterOps:
    return CharacterOps(state)


# ============ MOVEMENT ============

def test_move_character(state, ops):
    ops.move_character("hero", "forest")
    assert state.characters["hero"].location == "forest"
    ops.move_character("hero", "cave")
    assert state.characters["hero"].location == "cave"
    assert "Cannot reach" in ops.move_character("hero", "tavern")  # cave only connects to forest


# ============ ITEMS ============

def test_take_drop_item(state, ops):
    ops.take_item("hero", "ale")
    assert "ale" in state.characters["hero"].inventory
    assert "ale" not in state.locations["tavern"].items
    ops.drop_item("hero", "ale")
    assert "ale" not in state.characters["hero"].inventory
    assert "ale" in state.locations["tavern"].items


def test_give_loot_item(state, ops):
    ops.give_item("merchant", "hero", "potion")
    assert "potion" in state.characters["hero"].inventory
    ops.damage("merchant", 100)
    assert state.characters["merchant"].stats.hp == 0
    ops.loot_item("hero", "merchant", "shield")
    assert "shield" in state.characters["hero"].inventory
    assert "Cannot give" in ops.give_item("hero", "merchant", "potion")  # dead
    ops.heal("merchant", 100)
    assert "Cannot loot" in ops.loot_item("hero", "merchant", "shield")  # alive


# ============ STATS ============

def test_damage_heal(state, ops):
    ops.damage("hero", 8)
    assert state.characters["hero"].stats.hp == 12
    ops.heal("hero", 3)
    assert state.characters["hero"].stats.hp == 15
    ops.damage("hero", 100)
    assert state.characters["hero"].stats.hp == 0
    ops.heal("hero", 100)
    assert state.characters["hero"].stats.hp == 20


def test_level_up(state, ops):
    ops.level_up("hero")
    assert state.characters["hero"].stats.level == 2
    assert state.characters["hero"].stats.max_hp == 25
    assert state.characters["hero"].stats.hp == 25


def test_award_xp(state, ops):
    history_before = len(state.history)
    ops.award_xp("hero", 25, reason="slaying goblins")
    assert state.characters["hero"].stats.xp == 25
    assert state.history[-1].text == "hero earns 25 XP (slaying goblins)."
    ops.award_xp("hero", -10)  # clamped to 0, still logs
    assert state.characters["hero"].stats.xp == 25
    assert state.history[-1].text == "hero earns 0 XP."
    assert len(state.history) == history_before + 2
    assert "Cannot award XP" in ops.award_xp("ghost", 10)


def test_award_xp_auto_levels(state, ops):
    ops.level_up("hero")  # level 2, threshold becomes 200
    msg = ops.award_xp("hero", 200, reason="defeating the ogre")
    assert state.characters["hero"].stats.level == 3
    assert state.characters["hero"].stats.max_hp == 30
    assert "leveled up to level 3" in msg


def test_give_gold(state, ops):
    state.characters["hero"].stats.gold = 10
    ops.give_gold("hero", "merchant", 4)
    assert state.characters["hero"].stats.gold == 6
    assert state.characters["merchant"].stats.gold == 4
    assert "Cannot give gold" in ops.give_gold("hero", "merchant", 100)  # not enough gold
    assert state.characters["hero"].stats.gold == 6  # unchanged
    assert "Cannot give gold" in ops.give_gold("ghost", "merchant", 1)  # unknown giver
    assert "Cannot give gold" in ops.give_gold("hero", "ghost", 1)  # unknown receiver


# ============ TRADE ============

def test_trade_item(state, ops):
    state.characters["hero"].stats.gold = 10
    ops.trade_item("hero", "merchant", "potion", 4)
    assert "potion" in state.characters["hero"].inventory
    assert "potion" not in state.characters["merchant"].inventory
    assert state.characters["hero"].stats.gold == 6
    assert state.characters["merchant"].stats.gold == 4

    # reverse direction — merchant buys back from hero
    ops.trade_item("merchant", "hero", "potion", 4)
    assert "potion" in state.characters["merchant"].inventory
    assert "potion" not in state.characters["hero"].inventory
    assert state.characters["hero"].stats.gold == 10
    assert state.characters["merchant"].stats.gold == 0

    assert "Cannot trade" in ops.trade_item("hero", "merchant", "wand", 1)  # seller doesn't have item
    assert "Cannot trade" in ops.trade_item("hero", "merchant", "shield", 100)  # buyer can't afford

    ops.move_character("hero", "forest")
    assert "Cannot trade" in ops.trade_item("hero", "merchant", "shield", 1)  # different locations


# ============ CHARACTER UPDATE ============

def test_update_character(state, ops):
    ops.update_character("hero", goal="find the artifact", personality="brooding")
    assert state.characters["hero"].goal == "find the artifact"
    assert state.characters["hero"].personality == "brooding"
    assert "Cannot update" in ops.update_character("ghost", goal="haunt")


# ============ RELATIONSHIPS ============

def test_relationships(state, ops):
    ops.update_relationship("hero", "merchant", "friendly")
    assert state.characters["hero"].relationships["merchant"] == "friendly"
    ops.remove_relationship("hero", "merchant")
    assert "merchant" not in state.characters["hero"].relationships


# ============ KNOWLEDGE ============

def test_knowledge(state, ops):
    history_before = len(state.history)
    ops.add_knowledge("hero", "The cave has a hidden passage")
    assert "The cave has a hidden passage" in state.characters["hero"].knowledge
    assert state.history[-1].text == "hero learns: The cave has a hidden passage"
    assert len(state.history) == history_before + 1
    ops.add_knowledge("hero", "The cave has a hidden passage")  # idempotent — no new event
    assert state.characters["hero"].knowledge.count("The cave has a hidden passage") == 1
    assert len(state.history) == history_before + 1
