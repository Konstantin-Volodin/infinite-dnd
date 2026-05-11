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
from src.world import pick_scenario, read_manifest, scenario_dir

class StateManager:
    """Load, persist, and reset world state for a chosen scenario."""

    def __init__(self, scenario: str | None = None, state_dir: str = "world-state"):
        self.ROOT_DIR = Path(__file__).resolve().parents[3]
        self.scenario = scenario or pick_scenario()
        self.manifest = read_manifest(self.scenario)
        self.setup_dir = scenario_dir(self.scenario)
        self.state_dir = self.ROOT_DIR / Path(state_dir) / self.scenario
        self.state_dir.mkdir(parents=True, exist_ok=True)

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
    from src.world import list_scenarios
    logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")

    # exercise every scenario so a malformed JSON can't slip through
    for scenario in list_scenarios():
        logging.info(f"--- loading scenario: {scenario} ---")
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
            for conn in loc.connections:
                # Dangling connections are allowed: world_builder materializes them
                # when events reference the named place.
                if conn not in state.locations:
                    logging.info(f"  {scenario}: {loc_id} → {conn} (deferred to enrichment)")

        for quest_id, quest in state.quests.items():
            assert isinstance(quest, Quest)
            assert quest.id == quest_id
            if quest.owner:
                assert quest.owner in state.characters, f"quest {quest_id} owned by unknown character {quest.owner}"

        logging.info(f"{scenario}: {len(state.characters)} chars, {len(state.locations)} locs, {len(state.quests)} quests OK")

    # round-trip save/load on the default (random) scenario
    manager = StateManager()
    state = manager.load_state()
    state.time += 1
    manager.save_state(state)
    loaded = manager.load_state(world_state_file=f"world_state_{state.time}.json")
    assert loaded == state
    logging.info(f"save/load round-trip OK on '{manager.scenario}'")

    logging.info(f"{__file__} tests completed successfully.")
