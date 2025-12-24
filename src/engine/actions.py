"""Action execution for the game engine."""
import random
from typing import Any, Dict, Optional
from ..core.models import WorldState, Location, Character, CharacterType, CharacterStats, Memory
from ..core.rules import get_skill_modifier, get_health_status


class ActionExecutor:
    """Executes game actions and updates state."""
    
    def __init__(self, state: WorldState, save_callback, log_callback, history_callback):
        self.state = state
        self._save = save_callback
        self._log = log_callback
        self._history = history_callback

    def _emit(self, icon: str, msg: str, history_msg: str = None):
        """Log and record an event."""
        # Import sys to check module globals without circular dependency
        import sys
        
        # Get output_level from run_game module if it exists
        run_game_module = sys.modules.get('__main__')
        if run_game_module and hasattr(run_game_module, 'OutputLevel'):
            OutputLevel = run_game_module.OutputLevel
            current_output_level = getattr(run_game_module, 'output_level', 1)  # Default to DEFAULT
        else:
            # Fallback if module not found (e.g., during testing)
            current_output_level = 1  # DEFAULT
            class OutputLevel:
                QUIET = 0
                DEFAULT = 1
                VERBOSE = 2
                DEBUG = 3
        
        # Filter thinking and system messages based on output level
        is_thinking = "<thinking>" in msg or "</thinking>" in msg
        is_system = msg.startswith("[SYSTEM]")
        
        # In QUIET mode, suppress most emissions (they're redundant with turn summaries)
        # In DEFAULT mode, show normal gameplay but hide thinking/system
        # In VERBOSE mode, show everything including thinking/system
        # In DEBUG mode, show absolutely everything

        # Map message types to output levels
        if is_thinking or is_system:
            required_level = OutputLevel.VERBOSE
        else:
            required_level = OutputLevel.DEFAULT

        # Quiet mode suppresses these messages (turn summaries are handled elsewhere)
        if current_output_level >= required_level:
            # Use the run_game output function if present so global output settings are consistent
            run_game_output = None
            try:
                run_game_output = getattr(sys.modules.get('__main__'), 'output')
            except Exception:
                run_game_output = None
            formatted = f"  {icon} {msg}"
            if run_game_output:
                try:
                    # Call output with the appropriate required level
                    run_game_module = sys.modules.get('__main__')
                    run_game_module.output(formatted, level=required_level)
                except Exception:
                    print(formatted)
            else:
                print(formatted)
        
        self._log(msg)
        self._history(history_msg or msg)

    def _get_char(self, char_id: str) -> Optional[Character]:
        return self.state.characters.get(char_id)

    def _get_loc(self, loc_id: str) -> Optional[Location]:
        return self.state.locations.get(loc_id)

    def _find_target(self, char: Character, target_name: str) -> Optional[Character]:
        """Find a character by name at the same location (fuzzy match)."""
        target_lower = target_name.lower()
        for c in self.state.characters.values():
            if c.location_id == char.location_id and c.id != char.id:
                c_name_lower = c.name.lower()
                # Exact match or substring match
                if target_lower == c_name_lower or target_lower in c_name_lower or c_name_lower in target_lower:
                    return c
        return None

    # === DM Actions ===
    
    def dm_action(self, location_id: str, response: Dict) -> Dict:
        """Handle structured DM response with narration and world updates."""
        narration = response.get("narration", "")
        loc = self._get_loc(location_id)
        
        if loc:
            for f in response.get("new_location_features", []):
                if f not in loc.features:
                    loc.features.append(f)
            for i in response.get("new_items", []):
                if i not in loc.items:
                    loc.items.append(i)
            self._save()
        
        if narration:
            self._emit("📖", f"DM: {narration}")
        return {"status": "success", "narration": narration}

    def narrate(self, text: str) -> Dict:
        """Simple narration."""
        if text:
            self._emit("📖", f"DM: {text}")
        return {"status": "success"}

    def spawn_event(self, location_id: str, description: str) -> Dict:
        """Spawn an event at a location."""
        loc = self._get_loc(location_id)
        if not loc:
            return {"status": "error", "message": "Location not found"}
        self._emit("⚡", f"EVENT at {loc.name}: {description}")
        return {"status": "success"}

    def _sanitize_id(self, id_str: str) -> str:
        """Sanitize ID to be lowercase, no spaces, no special chars."""
        import re
        # Replace spaces/special chars with hyphens, remove non-alphanumeric
        clean = re.sub(r'[^a-z0-9\-]', '', id_str.lower().replace(' ', '-'))
        # Remove duplicate hyphens
        clean = re.sub(r'-+', '-', clean)
        return clean.strip('-')

    def create_location(self, location_id: str, name: str, description: str, connected_to: list = None) -> Dict:
        """Create a new location."""
        # Sanitize ID
        location_id = self._sanitize_id(location_id)
        
        if location_id in self.state.locations:
            return {"status": "error", "message": "Location exists"}
        
        self.state.locations[location_id] = Location(
            id=location_id, name=name, description=description,
            connections=connected_to or []
        )
        for conn_id in (connected_to or []):
            if conn_id in self.state.locations:
                self.state.locations[conn_id].connections.append(location_id)
        self._save()
        self._emit("🗺️", f"New location: {name}")
        return {"status": "success"}

    def create_item(self, item_name: str, location_id: str) -> Dict:
        """Add an item to a location."""
        loc = self._get_loc(location_id)
        if not loc:
            return {"status": "error", "message": "Location not found"}
        if item_name not in loc.items:
            loc.items.append(item_name)
            self._save()
        return {"status": "success"}

    def spawn_npc(self, npc_id: str, name: str, role: str, location_id: str, description: str = "", goal: str = "") -> Dict:
        """Create a new NPC."""
        # Sanitize ID
        npc_id = self._sanitize_id(npc_id)
        
        if npc_id in self.state.characters:
            return {"status": "error", "message": "NPC exists"}
        loc = self._get_loc(location_id)
        if not loc:
            return {"status": "error", "message": "Location not found"}
        
        self.state.characters[npc_id] = Character(
            id=npc_id, name=name, type=CharacterType.NPC, race="Human",
            class_name=role, backstory=description, goal=goal,
            stats=CharacterStats(hp=15, max_hp=15, ac=10), location_id=location_id
        )
        self._save()
        self._emit("👤", f"{name} ({role}) appears at {loc.name}")
        return {"status": "success"}

    def remove_npc(self, npc_id: str, reason: str = "left") -> Dict:
        """Remove an NPC."""
        char = self._get_char(npc_id)
        if not char or char.type == CharacterType.PC:
            return {"status": "error", "message": "Cannot remove"}
        name = char.name
        del self.state.characters[npc_id]
        self._save()
        self._emit("👋", f"{name} {reason}")
        return {"status": "success"}



    def skill_check(self, character_id: str, skill: str, description: str, item_name: Optional[str] = None) -> Dict:
        """Describe what you will do next to advance the story. This can be an action (eg, pick a lock, climb a wall, attempt a persuasion, knowledge check, etc.). Use this when the outcome is uncertain."""
        char = self._get_char(character_id)
        if not char:
            return {"status": "error", "message": "Character not found"}
        
        msg = f"{char.name} attempts a {skill} check: {description}"
        if item_name:
            msg += f" (using {item_name})"
        self._emit("🎲", msg)
        
        # Build rich DM guidance including quest context
        dm_guidance = f"Determine the outcome of {char.name}'s {skill} check: '{description}'."
        
        # Add character's goal for context
        if char.goal:
            dm_guidance += f"\n\nCharacter's Goal: {char.goal}"
            dm_guidance += f"\n\nIMPORTANT: Even if the check fails, create a COMPLICATION that advances their goal, not a dead-end."
            dm_guidance += f"\nExample: If caught, maybe the guard knows something useful. If lock fails, maybe there's another way in."
        
        dm_guidance += f"\n\nNarrate the result (success or failure) and any consequences."
        
        return {
            "status": "success",
            "requires_dm_response": True,
            "dm_guidance": dm_guidance
        }

    def combat(self, character_id: str, target: str, description: str, dmg: Optional[str] = None, heal: Optional[str] = None) -> Dict:
        """Start combat or help a character in combat. Describe the action and its impact."""
        char = self._get_char(character_id)
        if not char:
            return {"status": "error", "message": "Character not found"}
        
        target_char = self._find_target(char, target)
        if not target_char:
            return {"status": "error", "message": f"Target '{target}' not found at {char.location_id}"}
        
        msg = f"{char.name} attacks {target_char.name}: {description}"
        if dmg:
            msg += f" (deals {dmg} damage)"
        if heal:
            msg += f" (heals {heal})"
        self._emit("⚔️", msg)
        return {"status": "success"}

    def move(self, character_id: str, location_id: str) -> Dict:
        """Move to a different location. ONLY ALLOWED TO USE WHEN NO OTHER TOOLS ARE USED"""
        char = self._get_char(character_id)
        if not char:
            return {"status": "error", "message": "Character not found"}
        
        new_loc = self._get_loc(location_id)
        if not new_loc:
            return {"status": "error", "message": "Location not found"}
        
        current_loc = self._get_loc(char.location_id)
        if not current_loc or location_id not in current_loc.connections:
            return {"status": "error", "message": f"Cannot move to {new_loc.name} from {current_loc.name if current_loc else 'unknown location'}. It's not a connected location."}
        
        char.location_id = location_id
        self._save()
        self._emit("🚶", f"{char.name} moves to {new_loc.name}")
        return {"status": "success"}

    def update(self, character_id: str, goals: Optional[str] = None, emotions: Optional[str] = None, knowledge: Optional[str] = None) -> Dict:
        """Update character state (goals, emotions, knowledge)."""
        char = self._get_char(character_id)
        if not char:
            return {"status": "error", "message": "Character not found"}
        
        updates = []
        if goals:
            char.goal = goals
            updates.append(f"goals: {goals}")
        if emotions:
            # Assuming there's a field for emotions or we just log it/store in memory?
            # The Character model might not have 'emotions' field. Let's check.
            # If not, maybe just log it or append to memory/scratchpad.
            # For now, let's assume we just log it as an internal state update.
            updates.append(f"emotions: {emotions}")
        if knowledge:
            if knowledge not in char.knowledge:
                char.knowledge.append(knowledge)
                updates.append(f"learned: {knowledge}")
        
        if updates:
            self._save()
            self._emit("🧠", f"{char.name} updates state: {', '.join(updates)}")
        
        return {"status": "success"}

    def request(self, character_id: str, request: str) -> Dict:
        """Request something from the DM."""
        char = self._get_char(character_id)
        if not char:
            return {"status": "error", "message": "Character not found"}
        
        self._emit("✋", f"{char.name} requests: {request}")
        return {"status": "success", "message": "Request sent to DM"}



    # === Character Actions ===
    def dialogue(self, character_id: str, message: str) -> Dict:
        """Character expresses thoughts, feelings, or observations."""
        char = self._get_char(character_id)
        if not char or not message:
            return {"status": "error", "message": "Invalid"}
        self._emit("💭", f"{char.name}: {message}")
        return {"status": "success"}


