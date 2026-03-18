"""State Manager - Load/save world state from JSON files."""

import json
import os
from .models import (
    WorldState,
    Character,
    Location,
    CharacterType,
    CharacterStats,
    Quest,
)
class StateManager:
    """Handles the world state."""

    def __init__(self, setup_dir: str = "world-setup", state_dir: str = "world-state"):
        """Initialize the state manager."""
        self.setup_dir = setup_dir
        self.state_dir = state_dir
        self.state_file = os.path.join(state_dir, "world_state.json")
        os.makedirs(self.state_dir, exist_ok=True)

    def read_json(self, path: str):
        """Load a JSON file."""
        try:
            with open(path, "r", encoding="utf-8") as json_file:
                return json.load(json_file)
        except Exception as e:
            raise ValueError(f"Failed to read JSON file {path}: {e}") from e

    def generate_initial_setup(self) -> WorldState:
        """Load fresh world from setup files."""

        # Load locations
        locations = {}
        locations_json = self.read_json(os.path.join(self.setup_dir, "locations.json"))
        for loc in locations_json:
            locations[loc["id"]] = Location(
                id=loc["id"],
                name=loc.get("name") or loc["id"].replace("-", " ").title(),
                description=loc["description"],
                connections=loc.get("connections", []),
                features=loc.get("features", []),
                items=loc.get("items", []),
            )

        # Load characters
        characters = {}
        characters_json = self.read_json(os.path.join(self.setup_dir, "characters.json"))
        for char in characters_json:
            c_type = CharacterType(char["type"]) if "type" in char else CharacterType.NPC
            # Simple heuristic for name: convert slug to Title Case
            c_name = char.get("name") or char["id"].replace("-", " ").title()

            characters[char["id"]] = Character(
                id=char["id"],
                name=c_name,
                type=char.get("type", c_type),
                location=char.get("location", "market-square"),
                role=char.get("role", ""),
                stats=CharacterStats(**char.get("stats", {})),
                backstory=char.get("backstory", ""),
                personality=char.get("personality", ""),
                goal=char.get("goal", ""),
                inventory=char.get("inventory", []),
                knowledge=char.get("knowledge", []),
                relationships=char.get("relationships", {}),
            )

        # Load Quests
        quests = {}
        quests_json = self.read_json(os.path.join(self.setup_dir, "quests.json"))
        for quest in quests_json:
            quests[quest["id"]] = Quest(
                id=quest["id"],
                title=quest["title"],
                description=quest["description"],
                status=quest.get("status", "active"),
                owner=quest.get("owner", ""),
                steps=quest.get("steps", []),
            )

        # Initial world state
        world_state = WorldState(locations=locations, characters=characters, quests=quests)
        return world_state

    def generate_state(self) -> WorldState:
        """Load saved state, or create fresh from setup if none exists."""
        
        # initial state
        if not os.path.exists(self.state_file):
            print("🔄 initializing world state...")
            state = self.generate_initial_setup()
            self.save_state(state)
            return state

        # load saved state
        world_state_json = self.read_json(self.state_file)



        return WorldState(**world_state_json)

    def save_state(self, state: WorldState):
        """Save current world state to JSON."""
        with open(self.state_file, "w", encoding="utf-8") as f:
            f.write(state.model_dump_json(indent=2))
