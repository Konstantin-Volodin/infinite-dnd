from src.engine.state.models import (
    Character,
    CharacterStats,
    HistoryEvent,
    Location,
    Quest,
    WorldState,
)


def test_character_stats():
    stats = CharacterStats(hp=20, max_hp=20, level=3)
    assert stats.hp == 20
    assert stats.max_hp == 20
    assert stats.level == 3


def test_location():
    loc = Location(id="forest-1", description="dark forest", connections=["village-1"], features=["cabin in the woods"], items=["sword"])
    assert loc.id == "forest-1"
    assert loc.connections == ["village-1"]
    assert loc.features == ["cabin in the woods"]
    assert loc.items == ["sword"]


def test_character():
    stats = CharacterStats(hp=20, max_hp=20, level=3)
    char = Character(id="hero-1", role="warrior", inventory=["sword", "shield"], goal="slay the dragon", stats=stats)
    assert char.id == "hero-1"
    assert char.role == "warrior"
    assert char.stats.hp == 20
    assert char.inventory == ["sword", "shield"]
    assert char.goal == "slay the dragon"


def test_quest():
    char = Character(id="hero-1", role="warrior")
    quest = Quest(id="q1", title="Slay Dragon", description="defeat the dragon", owner=char.id)
    assert quest.status == "active"
    assert quest.owner == "hero-1"
    assert quest.description == "defeat the dragon"
    # back-compat defaults — old snapshots/scenarios without plan still construct fine
    assert quest.plan == []
    assert quest.current_step == 0
    assert quest.steps == []


def test_quest_with_plan():
    quest = Quest(id="q2", title="Slay Dragon", description="defeat the dragon", plan=["find the lair", "slay the dragon"])
    assert quest.plan == ["find the lair", "slay the dragon"]
    assert quest.current_step == 0


def test_world_state():
    loc = Location(id="forest-1", description="dark forest", connections=["village-1"], features=["cabin in the woods"], items=["sword"])
    stats = CharacterStats(hp=20, max_hp=20, level=3)
    char = Character(id="hero-1", role="warrior", inventory=["sword", "shield"], goal="slay the dragon", stats=stats)
    quest = Quest(id="q1", title="Slay Dragon", description="defeat the dragon", owner=char.id)

    world = WorldState(
        time=0,
        locations={"forest-1": loc},
        characters={"hero-1": char},
        quests={"q1": quest},
        history=[HistoryEvent(text="Hero enters the forest", location="forest-1", characters=["hero-1"])]
    )
    assert world.time == 0
    assert world.locations == {"forest-1": loc}
    assert world.characters == {"hero-1": char}
    assert world.quests == {"q1": quest}
    assert world.history == [HistoryEvent(text="Hero enters the forest", location="forest-1", characters=["hero-1"])]
