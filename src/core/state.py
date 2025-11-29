"""State Manager - Load/save world state from JSON files."""
import json
import os
from .models import WorldState, Character, Location, CharacterType, CharacterStats, Quest


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
        def load_json_file(path: str):
            try:
                with open(path, "r", encoding="utf-8") as hf:
                    return json.load(hf)
            except json.JSONDecodeError as e:
                raise ValueError(f"Failed to parse JSON file {path}: {e}") from e
            except Exception as e:
                raise ValueError(f"Failed to read JSON file {path}: {e}") from e

        for loc in load_json_file(os.path.join(self.setup_dir, "locations.json")):
                locations[loc["id"]] = Location(
                    id=loc["id"], name=loc["name"], description=loc["description"],
                    connections=loc.get("connections", []),
                    features=loc.get("features", []), items=loc.get("items", [])
                )

        characters = {}
        for char in load_json_file(os.path.join(self.setup_dir, "characters.json")):
                char_type = CharacterType.PC if char.get("type") == "pc" else CharacterType.NPC
                characters[char["id"]] = Character(
                    id=char["id"], name=char["name"], type=char_type,
                    class_name=char.get("role", "Commoner"),
                    backstory=char.get("description", ""), goal=char.get("goal", ""),
                    knowledge=char.get("knowledge", []),
                    stats=CharacterStats(hp=20, max_hp=20, ac=10),
                    location_id="market-square", inventory=char.get("inventory", [])
                )

        quests = {}
        quests_path = os.path.join(self.setup_dir, "quests.json")
        if os.path.exists(quests_path):
            try:
                for q in load_json_file(quests_path):
                    quests[q["id"]] = Quest(**q)
            except Exception as e:
                # Use run_game output if available, otherwise print
                import sys
                run_game_module = sys.modules.get('__main__')
                if run_game_module and hasattr(run_game_module, 'output'):
                    try:
                        OutputLevel = getattr(run_game_module, 'OutputLevel')
                        run_game_module.output(f"⚠️ Failed to load quests: {e}", OutputLevel.DEBUG)
                    except Exception:
                        print(f"⚠️ Failed to load quests: {e}")
                else:
                    print(f"⚠️ Failed to load quests: {e}")

        return WorldState(locations=locations, characters=characters, quests=quests)

    def load_state(self) -> WorldState:
        """Load saved state, or create fresh from setup if none exists."""
        if not os.path.exists(self.state_file):
            # print("🔄 initializing world state...")
            state = self.load_initial_setup()
            self.save_state(state)
            return state
        try:
            with open(self.state_file, "r", encoding="utf-8") as f:
                return WorldState(**json.load(f))
        except json.JSONDecodeError as e:
            raise ValueError(f"Saved state file is invalid JSON: {self.state_file}: {e}") from e
        except Exception as e:
            raise ValueError(f"Failed to load saved state from {self.state_file}: {e}") from e

    def save_state(self, state: WorldState):
        """Save current world state to JSON."""
        with open(self.state_file, "w", encoding="utf-8") as f:
            # print("saving world state...")
            f.write(state.model_dump_json(indent=2))
