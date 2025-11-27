"""Action execution for the game engine."""
import random
from typing import Any, Dict, Optional
from ..core.models import WorldState, Location, Character, CharacterType, CharacterStats
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
        
        # Check for repetition
        last_msg = f'{char.name}: "{dialogue}"'
        if target:
            last_msg = f'{char.name} says to {target}: "{dialogue}"'
            
        if self.state.history and self.state.history[-1] == last_msg:
             return {"status": "error", "message": "You just said that. Say something else or do something."}

        # Validate target presence if a target is provided
        if target:
            # find a character by the target name in same location
            possible = [c for c in self.state.characters.values() if c.location_id == char.location_id and target.lower() in c.name.lower()]
            if not possible:
                allowed = [c.name for c in self.state.characters.values() if c.location_id == char.location_id and c.id != char.id]
                return {"status": "error", "code": "invalid_target", "message": f"Target not present: {target}", "allowed_targets": allowed}
        msg = last_msg
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
        loc = self._get_loc(char.location_id)
        # Validate target exists as a feature or item in this location
        present_features = [f.lower() for f in (loc.features or [])]
        present_items = [i.lower() for i in (loc.items or [])]
        inventory_items = [i.lower() for i in (char.inventory or [])]
        if target.lower() not in present_features and target.lower() not in present_items and target.lower() not in inventory_items:
            return {"status": "error", "code": "invalid_target", "message": f"Nothing named '{target}' here to examine.", "present_features": loc.features, "present_items": loc.items, "inventory_items": char.inventory}
        if loc and loc.feature_traits:
            # Match target against trait keys (case-insensitive)
            trait = None
            t_lower = target.lower()
            for k, v in loc.feature_traits.items():
                if t_lower == k.lower() or t_lower in k.lower() or k.lower() in t_lower:
                    trait = v
                    trait_name = k
                    break
            if trait and isinstance(trait, dict) and trait.get("skill"):
                skill = trait.get("skill")
                difficulty = trait.get("difficulty", 10)
                # Offer a skill_required code for run_game to handle
                return {
                    "status": "success",
                    "code": "skill_required",
                    "skill": skill,
                    "difficulty": difficulty,
                    "action_description": trait.get("description", f"Search {target} carefully."),
                    "location_id": loc.id,
                    "examine_target": target,
                    "feature_key": trait_name
                }
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
            # Return list of items present to help the agent
            return {"status": "error", "code": "item_missing", "item_name": item_name, "allowed_items": loc.items}
        
        loc.items.remove(found)
        char.inventory.append(found)
        self._save()
        self._emit("✋", f"{char.name} picked up {found}")
        return {"status": "success"}

    def use(self, character_id: str, item_name: str, target: str, spell_name: str = None) -> Dict:
        """Use an item."""
        char = self._get_char(character_id)
        if not char:
            return {"status": "error", "message": "Character not found"}
        found = next((i for i in char.inventory if i.lower() == item_name.lower()), None)
        if not found:
            return {"status": "error", "message": f"Don't have {item_name}"}
        # Include spell_name if provided to make the narration clearer
        if spell_name:
            self._emit("✨", f"{char.name} uses {found} ({spell_name}) on {target}")
            # Healing spell recognition (basic): heal if spell_name contains 'heal' or 'cure' or item contains 'potion'
            if "heal" in spell_name.lower() or "cure" in spell_name.lower() or "potion" in item_name.lower():
                # Target either self or named target at same location
                if target:
                    tchar = self._find_target(char, target)
                    if not tchar and target.lower() in [c.id for c in self.state.characters.values()]:
                        tchar = self.state.characters.get(target)
                else:
                    tchar = char
                if tchar:
                    heal = 6  # Simple flat heal; can be replaced by dice roll
                    before = tchar.stats.hp
                    tchar.stats.hp = min(tchar.stats.max_hp, tchar.stats.hp + heal)
                    self._save()
                    self._emit("💖", f"{char.name} heals {tchar.name} for {tchar.stats.hp - before} (now {tchar.stats.hp}/{tchar.stats.max_hp})")
        else:
            self._emit("🔧", f"{char.name} used {found} on {target}")
            # Basic item healing for potions
            if "potion" in item_name.lower() or "healing" in item_name.lower():
                # heal self or target
                if target:
                    tchar = self._find_target(char, target)
                    if not tchar and target.lower() in [c.id for c in self.state.characters.values()]:
                        tchar = self.state.characters.get(target)
                else:
                    tchar = char
                if tchar:
                    heal = 8
                    before = tchar.stats.hp
                    tchar.stats.hp = min(tchar.stats.max_hp, tchar.stats.hp + heal)
                    self._save()
                    self._emit("💖", f"{char.name} drinks {found} and heals {tchar.name} for {tchar.stats.hp - before} (now {tchar.stats.hp}/{tchar.stats.max_hp})")
        return {"status": "success"}

    def attack(self, character_id: str, target: str, weapon: str = "unarmed", style: str = None) -> Dict:
        """Attack a target."""
        char = self._get_char(character_id)
        if not char:
            return {"status": "error", "message": "Character not found"}
        target_char = self._find_target(char, target)
        if not target_char:
            # Suggest allowed targets present at location
            allowed = [c.name for c in self.state.characters.values() if c.location_id == char.location_id and c.id != char.id]
            return {"status": "error", "code": "invalid_target", "message": f"Can't find {target}", "allowed_targets": allowed}
        
    # Roll attack
        roll = random.randint(1, 20) + char.stats.level
        hit = roll >= target_char.stats.ac
        
        if hit:
            damage = random.randint(1, 6) + char.stats.level
            before_status = get_health_status(target_char)
            target_char.stats.hp -= damage
            if target_char.stats.hp <= 0:
                target_char.stats.hp = 0
                if style:
                    self._emit("⚔️", f"{char.name} delivers a {style} with {weapon}, defeating {target_char.name}!")
                else:
                    self._emit("⚔️", f"{char.name} defeats {target_char.name}!")
                if target_char.type == CharacterType.NPC:
                    del self.state.characters[target_char.id]
            else:
                if style:
                    self._emit("⚔️", f"{char.name} {style} {target_char.name} for {damage} ({target_char.stats.hp} HP)")
                else:
                    self._emit("⚔️", f"{char.name} hits {target_char.name} for {damage} ({target_char.stats.hp} HP)")
            # Check for status change
            after_status = get_health_status(target_char)
            if after_status != before_status:
                # Emit a status change message
                self._emit("⚠️", f"{target_char.name} is now {after_status} ({target_char.stats.hp}/{target_char.stats.max_hp})")
        else:
            if style:
                self._emit("⚔️", f"{char.name} attempts a {style} but misses {target_char.name}")
            else:
                self._emit("⚔️", f"{char.name} misses {target_char.name}")
        
        self._save()
        return {"status": "success", "hit": hit}

    def attempt_skill(self, character_id: str, skill: str, action_description: str, difficulty: int = None) -> Dict:
        """Attempt a skill check."""
        char = self._get_char(character_id)
        if not char:
            return {"status": "error", "message": "Character not found"}
        
        modifier = get_skill_modifier(char, skill)
        roll = random.randint(1, 20)
        total = roll + modifier
        
        msg = f"🎲 {char.name} {skill.title()}: {total} (d20={roll}, mod={modifier})"
        self._emit("🎲", msg, f"[SYSTEM] {msg}")
        result = {"status": "success", "roll": total, "modifier": modifier}
        if difficulty is not None:
            result["difficulty"] = difficulty
            result["success"] = total >= difficulty
        return result

    def wait(self, character_id: str, reason: str = None) -> Dict:
        """Character waits."""
        char = self._get_char(character_id)
        if not char:
            return {"status": "error", "message": "Character not found"}
        self._emit("⏳", f"{char.name} waits" + (f" ({reason})" if reason else ""))
        return {"status": "success"}
