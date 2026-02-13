import json
from pathlib import Path
from src.core.state import StateManager


def test_generate_initial_setup_sets_location_name(tmp_path):
    setup_dir = tmp_path / "world-setup"
    setup_dir.mkdir()

    # locations.json without explicit name
    locations = [
        {"id": "valley-bridge", "description": "An old stone bridge."}
    ]
    (setup_dir / "locations.json").write_text(json.dumps(locations))
    # minimal empty characters/quests
    (setup_dir / "characters.json").write_text(json.dumps([]))
    (setup_dir / "quests.json").write_text(json.dumps([]))

    sm = StateManager(setup_dir=str(setup_dir), state_dir=str(tmp_path / "world-state"))
    state = sm.generate_initial_setup()

    loc = state.locations.get("valley-bridge")
    assert loc is not None
    assert loc.name == "Valley Bridge"
