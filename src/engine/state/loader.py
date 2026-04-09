"""State Manager - load/save world state from JSON files."""

import json
from pathlib import Path

from src.engine.state.models import (
    WorldState,
    Character,
    Location,
    CharacterStats,
    Quest,
)

class StateLoader:
    """Handles the world state."""

    def __init__(self, setup_dir: str = "src/world", state_dir: str = "world-state"):
        """Initialize the state loader."""
        self.ROOT_DIR = Path(__file__).resolve().parents[3]
        self.setup_dir = self.ROOT_DIR / Path(setup_dir)
        self.state_dir = self.ROOT_DIR / Path(state_dir)
        self.state_dir.mkdir(exist_ok=True)

    def read_json(self, path: str | Path):
        with open(path, "r", encoding="utf-8") as json_file:
            return json.load(json_file)

    def init_state(self) -> WorldState:
        """Load fresh world from setup files."""

        locations = {}
        locations_json = self.read_json(self.setup_dir / "locations.json")
        for loc in locations_json:
            locations[loc["id"]] = Location(
                id=loc["id"],
                description=loc.get("description", ""),
                connections=loc.get("connections", []),
                features=loc.get("features", []),
                items=loc.get("items", []),
            )

        characters = {}
        characters_json = self.read_json(self.setup_dir / "characters.json")
        for char in characters_json:
            characters[char["id"]] = Character(
                id=char["id"],
                location=char["location"],
                role=char.get("role", ""),
                stats=CharacterStats(**char.get("stats", {})),
                backstory=char.get("backstory", ""),
                personality=char.get("personality", ""),
                goal=char.get("goal", ""),
                inventory=char.get("inventory", []),
                knowledge=char.get("knowledge", []),
                relationships=char.get("relationships", {}),
            )

        quests = {}
        quests_json = self.read_json(self.setup_dir / "quests.json")
        for quest in quests_json:
            quests[quest["id"]] = Quest(
                id=quest["id"],
                title=quest.get("title", ""),
                description=quest.get("description", ""),
                status=quest.get("status", "active"),
                owner=quest.get("owner", ""),
                steps=quest.get("steps", []),
            )

        word_state = WorldState(
            locations=locations, 
            characters=characters, 
            quests=quests
        )
        return word_state

    def load_state(self, world_state_file: str = None) -> WorldState:
        """Load saved state, or create fresh from setup if none exists."""

        if world_state_file:
            state_path = self.state_dir / world_state_file
            if not state_path.exists():
                raise FileNotFoundError(f"Specified world state file {state_path} does not exist.")
            return WorldState(**self.read_json(state_path))
        
        else:
            state = self.init_state()
            self.save_state(state)
            return state

    def save_state(self, state: WorldState):
        """Save current world state to JSON."""
        state_file = self.state_dir / f"world_state_{state.time}.json"
        with state_file.open("w", encoding="utf-8") as state_file:
            state_file.write(state.model_dump_json(indent=2))


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")

    manager = StateLoader()
    state = manager.load_state()

    # check dirs
    logging.info(f"Initial world state loaded.")
    logging.info(f"root_dir: {manager.ROOT_DIR}")
    logging.info(f"setup_dir: {manager.setup_dir}")
    logging.info(f"state_dir: {manager.state_dir}")

    # tests
    assert isinstance(state, WorldState)
    assert isinstance(state.characters, dict)
    assert isinstance(state.locations, dict)
    assert isinstance(state.quests, dict)
    logging.info("WorldState structure test passed.")

    # check characters
    for char_id, char in state.characters.items():
        assert isinstance(char, Character)
        assert char.id == char_id
        logging.info(f"Character {char_id} loaded.")
        logging.info(f"{char}")
    logging.info("All characters loaded successfully.")

    # check locations
    for loc_id, loc in state.locations.items():
        assert isinstance(loc, Location)
        assert loc.id == loc_id
        logging.info(f"Location {loc_id} loaded.")
        logging.info(f"{loc}")
    logging.info("All locations loaded successfully.")

    # check quests
    for quest_id, quest in state.quests.items():
        assert isinstance(quest, Quest)
        assert quest.id == quest_id
        logging.info(f"Quest {quest_id} loaded.")
        logging.info(f"{quest}")
    logging.info("All quests loaded successfully.")

    logging.info(f"{__file__} tests completed successfully.")

    # test saving state
    state.time += 1  # increment time to avoid overwriting initial state
    manager.save_state(state)
    logging.info(f"World state saved successfully at time {state.time}.")

    # test loading saved state
    loaded_state = manager.load_state(world_state_file=f"world_state_{state.time}.json")
    assert loaded_state == state
    logging.info("Saved world state loaded successfully and matches current state.")