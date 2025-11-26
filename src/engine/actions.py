"""Action execution for the game engine."""
import random
from typing import Any, Dict, Optional
from ..core.models import WorldState, Location, Character, CharacterType, CharacterStats
from ..core.rules import get_skill_modifier


class ActionExecutor:
    """Executes game actions and updates state."""
    
    def __init__(self, state: WorldState, save_callback, log_callback, history_callback):
        self.state = state
        self._save = save_callback
        self._log = log_callback
        self._history = history_callback

    def _emit(self, icon: str, msg: str, history_msg: str = None):
        """Log and record an event."""
        print(f"  {icon} {msg}")
        self._log(msg)
        self._history(history_msg or msg)

    def _get_char(self, char_id: str) -> Optional[Character]:
        return self.state.characters.get(char_id)

    def _get_loc(self, loc_id: str) -> Optional[Location]:
        return self.state.locations.get(loc_id)

    def _find_target(self, char: Character, target_name: str) -> Optional[Character]:
        """Find a character by name at the same location."""
        for c in self.state.characters.values():
            if c.location_id == char.location_id and c.id != char.id:
                if target_name.lower() in c.name.lower():
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

    def create_location(self, location_id: str, name: str, description: str, connected_to: list = None) -> Dict:
        """Create a new location."""
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

    # === Character Actions ===

    def say(self, character_id: str, dialogue: str, target: str = None) -> Dict:
        """Character speaks."""
        char = self._get_char(character_id)
        if not char or not dialogue:
            return {"status": "error", "message": "Invalid"}
        msg = f'{char.name} says to {target}: "{dialogue}"' if target else f'{char.name}: "{dialogue}"'
        self._emit("💬", msg)
        return {"status": "success"}

    def move(self, character_id: str, destination: str) -> Dict:
        """Move character to a location."""
        char = self._get_char(character_id)
        if not char:
            return {"status": "error", "message": "Character not found"}
        
        # Find destination by ID or name
        dest_id = None
        for lid, loc in self.state.locations.items():
            if destination.lower() in lid.lower() or destination.lower() in loc.name.lower():
                dest_id = lid
                break
        
        if not dest_id:
            return {"status": "error", "message": f"Unknown location: {destination}"}
        if char.location_id == dest_id:
            return {"status": "success", "message": "Already there"}
        
        old_name = self._get_loc(char.location_id).name if char.location_id else "nowhere"
        char.location_id = dest_id
        self._save()
        self._emit("🚶", f"{char.name} moved from {old_name} to {self._get_loc(dest_id).name}")
        return {"status": "success"}

    def examine(self, character_id: str, target: str) -> Dict:
        """Character examines something."""
        char = self._get_char(character_id)
        if not char:
            return {"status": "error", "message": "Character not found"}
        self._emit("🔍", f"{char.name} examines {target}")
        return {"status": "success", "requires_dm_response": True, "examine_target": target}

    def pickup(self, character_id: str, item_name: str) -> Dict:
        """Pick up an item."""
        char = self._get_char(character_id)
        if not char:
            return {"status": "error", "message": "Character not found"}
        loc = self._get_loc(char.location_id)
        if not loc:
            return {"status": "error", "message": "Location not found"}
        
        # Find item (case-insensitive)
        found = next((i for i in loc.items if i.lower() == item_name.lower()), None)
        if not found:
            return {"status": "error", "code": "item_missing", "item_name": item_name}
        
        loc.items.remove(found)
        char.inventory.append(found)
        self._save()
        self._emit("✋", f"{char.name} picked up {found}")
        return {"status": "success"}

    def use(self, character_id: str, item_name: str, target: str) -> Dict:
        """Use an item."""
        char = self._get_char(character_id)
        if not char:
            return {"status": "error", "message": "Character not found"}
        found = next((i for i in char.inventory if i.lower() == item_name.lower()), None)
        if not found:
            return {"status": "error", "message": f"Don't have {item_name}"}
        self._emit("🔧", f"{char.name} used {found} on {target}")
        return {"status": "success"}

    def attack(self, character_id: str, target: str, weapon: str = "unarmed") -> Dict:
        """Attack a target."""
        char = self._get_char(character_id)
        if not char:
            return {"status": "error", "message": "Character not found"}
        target_char = self._find_target(char, target)
        if not target_char:
            return {"status": "error", "message": f"Can't find {target}"}
        
        # Roll attack
        roll = random.randint(1, 20) + char.stats.level
        hit = roll >= target_char.stats.ac
        
        if hit:
            damage = random.randint(1, 6) + char.stats.level
            target_char.stats.hp -= damage
            if target_char.stats.hp <= 0:
                target_char.stats.hp = 0
                self._emit("⚔️", f"{char.name} defeats {target_char.name}!")
                if target_char.type == CharacterType.NPC:
                    del self.state.characters[target_char.id]
            else:
                self._emit("⚔️", f"{char.name} hits {target_char.name} for {damage} ({target_char.stats.hp} HP)")
        else:
            self._emit("⚔️", f"{char.name} misses {target_char.name}")
        
        self._save()
        return {"status": "success", "hit": hit}

    def attempt_skill(self, character_id: str, skill: str, action_description: str) -> Dict:
        """Attempt a skill check."""
        char = self._get_char(character_id)
        if not char:
            return {"status": "error", "message": "Character not found"}
        
        modifier = get_skill_modifier(char, skill)
        roll = random.randint(1, 20)
        total = roll + modifier
        
        msg = f"🎲 {char.name} {skill.title()}: {total} (d20={roll}, mod={modifier})"
        self._emit("🎲", msg, f"[SYSTEM] {msg}")
        return {"status": "success", "roll": total, "modifier": modifier}

    def wait(self, character_id: str, reason: str = None) -> Dict:
        """Character waits."""
        char = self._get_char(character_id)
        if not char:
            return {"status": "error", "message": "Character not found"}
        self._emit("⏳", f"{char.name} waits" + (f" ({reason})" if reason else ""))
        return {"status": "success"}
