import pytest

from src.engine.state.loader import StateManager
from src.engine.state.models import Character, Location, Quest, WorldState
from src.world import list_scenarios


@pytest.mark.parametrize("scenario", list_scenarios())
def test_init_state_for_scenario(scenario):
    manager = StateManager(scenario=scenario)
    state = manager.init_state()

    assert manager.scenario == scenario
    assert manager.manifest["pc"] in state.characters, f"manifest pc '{manager.manifest['pc']}' not in characters for {scenario}"
    assert isinstance(state, WorldState)

    for char_id, char in state.characters.items():
        assert isinstance(char, Character)
        assert char.id == char_id
        assert char.location in state.locations, f"{char_id} placed at unknown location {char.location}"

    for loc_id, loc in state.locations.items():
        assert isinstance(loc, Location)
        assert loc.id == loc_id
        # Dangling connections are allowed: the DM agent materializes them
        # when events reference the named place.

    for quest_id, quest in state.quests.items():
        assert isinstance(quest, Quest)
        assert quest.id == quest_id
        if quest.owner:
            assert quest.owner in state.characters, f"quest {quest_id} owned by unknown character {quest.owner}"


def test_save_load_round_trip():
    # round-trip save/load on the default (random) scenario
    manager = StateManager()
    state = manager.load_state()
    state.time += 1
    manager.save_state(state)
    loaded = manager.load_state(world_state_file=f"world_state_{state.time}.json")
    assert loaded == state


def test_latest_snapshot_name_uses_numeric_order(tmp_path):
    manager = StateManager(scenario="smuggler-cove", state_dir=str(tmp_path))
    assert manager.latest_snapshot_name() is None
    for tick in (2, 10, 3):
        (manager.state_dir / f"world_state_{tick}.json").write_text("{}", encoding="utf-8")
    (manager.state_dir / "world_state_bad.json").write_text("{}", encoding="utf-8")
    assert manager.latest_snapshot_name() == "world_state_10.json"
