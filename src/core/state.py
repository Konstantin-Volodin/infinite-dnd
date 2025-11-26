"""State Manager - Load/save world state from JSON files."""
import json
import os
from .models import WorldState, Character, Location, CharacterType, CharacterStats


class StateManager:
    """Handles loading initial setup and persisting world state."""
    
    def __init__(self, setup_dir: str = "world-setup", state_dir: str = "world-state"):
        self.setup_dir = setup_dir
        self.state_dir = state_dir
        self.state_file = os.path.join(state_dir, "world_state.json")
        os.makedirs(self.state_dir, exist_ok=True)

    def load_initial_setup(self) -> WorldState:
        """Load fresh world from setup files."""
        locations = {}
        with open(os.path.join(self.setup_dir, "locations.json")) as f:
            for loc in json.load(f):
                locations[loc["id"]] = Location(
                    id=loc["id"], name=loc["name"], description=loc["description"],
                    connections=loc.get("connections", []),
                    features=loc.get("features", []), items=loc.get("items", [])
                )

        characters = {}
        with open(os.path.join(self.setup_dir, "characters.json")) as f:
            for char in json.load(f):
                char_type = CharacterType.PC if char.get("type") == "pc" else CharacterType.NPC
                characters[char["id"]] = Character(
                    id=char["id"], name=char["name"], type=char_type,
                    class_name=char.get("role", "Commoner"),
                    backstory=char.get("description", ""), goal=char.get("goal", ""),
                    knowledge=char.get("knowledge", []),
                    stats=CharacterStats(hp=20, max_hp=20, ac=10),
                    location_id="market-square", inventory=char.get("inventory", [])
                )

        return WorldState(locations=locations, characters=characters)

    def load_state(self) -> WorldState:
        """Load saved state, or create fresh from setup if none exists."""
        if not os.path.exists(self.state_file):
            # print("🔄 initializing world state...")
            state = self.load_initial_setup()
            self.save_state(state)
            return state
        with open(self.state_file, "r", encoding="utf-8") as f:
            return WorldState(**json.load(f))

    def save_state(self, state: WorldState):
        """Save current world state to JSON."""
        with open(self.state_file, "w", encoding="utf-8") as f:
            # print("saving world state...")
            f.write(state.model_dump_json(indent=2))
