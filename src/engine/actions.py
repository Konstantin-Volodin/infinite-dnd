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
        
        old_loc = self._get_loc(char.location_id)
        old_name = old_loc.name if old_loc else "unknown location"
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
        if not loc:
             return {"status": "error", "message": "You are in an unknown location."}
        
        # Validate target exists as a feature or item in this location (fuzzy match)
        present_features = [f for f in (loc.features or [])]
        present_items = [i for i in (loc.items or [])]
        inventory_items = [i for i in (char.inventory or [])]
        
        target_lower = target.lower()
        
        # Helper for fuzzy check
        def is_match(name):
            n_lower = name.lower()
            return target_lower == n_lower or target_lower in n_lower or n_lower in target_lower

        matched_feature = next((f for f in present_features if is_match(f)), None)
        matched_item = next((i for i in present_items if is_match(i)), None)
        matched_inv = next((i for i in inventory_items if is_match(i)), None)
        
        real_target = matched_feature or matched_item or matched_inv
        
        if not real_target:
            return {"status": "error", "code": "invalid_target", "message": f"Nothing named '{target}' here to examine.", "present_features": loc.features, "present_items": loc.items, "inventory_items": char.inventory}
            
        # Use the real name for history/checks
        target = real_target

        # Check if already examined
        if target.lower() in [e.lower() for e in char.examined_items]:
             return {"status": "success", "message": f"You have already examined {target}. It seems unchanged."}
        
        # Mark as examined
        char.examined_items.append(target)
        self._save()

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
        
        # Trigger combat state if not already in combat
        if self.state.narrative.scene_type != "combat":
            self.state.narrative.scene_type = "combat"
            self.state.narrative.tension = "high"
            self._emit("⚔️", f"COMBAT STARTED! {char.name} attacks {target_char.name}!")
        
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
                
                # Handle defeat
                if target_char.type == CharacterType.NPC:
                    # Don't delete immediately, mark as defeated/unconscious? 
                    # For now, let's just remove them to keep it simple, or maybe leave a body?
                    # Let's remove them from active characters but maybe leave a "body" item?
                    del self.state.characters[target_char.id]
                    loc = self._get_loc(char.location_id)
                    if loc:
                        loc.items.append(f"body of {target_char.name}")
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

    def flee(self, character_id: str, direction: str = None) -> Dict:
        """Attempt to flee from combat."""
        char = self._get_char(character_id)
        if not char:
            return {"status": "error", "message": "Character not found"}
        
        if self.state.narrative.scene_type != "combat":
            # Just move if not in combat
            if direction:
                return self.move(character_id, direction)
            return {"status": "error", "message": "Not in combat, just move."}

        # Flee check (Athletics/Acrobatics vs DC 12)
        modifier = max(get_skill_modifier(char, "athletics"), get_skill_modifier(char, "acrobatics"))
        roll = random.randint(1, 20)
        total = roll + modifier
        difficulty = 12
        
        self._emit("🏃", f"{char.name} attempts to flee...", f"[SYSTEM] 🎲 Flee Check: {total} (d20={roll}, mod={modifier}) vs DC {difficulty}")
        
        if total >= difficulty:
            self._emit("💨", f"{char.name} escapes the battle!")
            # If direction provided, move there, else just stay but out of combat? 
            # Actually, fleeing should probably move you to a random connection or the previous location.
            # For now, let's ask for a direction or pick the first connection.
            loc = self._get_loc(char.location_id)
            target_loc_id = None
            if direction:
                 # Try to find matching connection
                 for conn in loc.connections:
                     if direction.lower() in conn.lower():
                         target_loc_id = conn
                         break
            
            if not target_loc_id and loc.connections:
                target_loc_id = loc.connections[0]
            
            if target_loc_id:
                char.location_id = target_loc_id
                self._save()
                self._emit("🚶", f"{char.name} fled to {target_loc_id}")
                return {"status": "success", "message": "Escaped!"}
            else:
                return {"status": "success", "message": "Escaped combat but nowhere to run!"}
        else:
            self._emit("🚫", f"{char.name} failed to escape!")
            return {"status": "failure", "message": "Blocked by enemies"}

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

    # === Self-Modification Actions ===
    
    def update_knowledge(self, character_id: str, knowledge_item: str) -> Dict:
        """Add knowledge to character."""
        char = self._get_char(character_id)
        if not char or not knowledge_item:
            return {"status": "error", "message": "Invalid"}
        if knowledge_item not in char.knowledge:
            char.knowledge.append(knowledge_item)
            self._save()
            self._emit("🧠", f"{char.name} learned: {knowledge_item}")
        return {"status": "success"}
    
    def reflect(self, character_id: str, new_motivation: str, reason: str = "") -> Dict:
        """Update character motivation."""
        char = self._get_char(character_id)
        if not char:
            return {"status": "error", "message": "Invalid"}
        old_motivation = char.current_motivation
        char.current_motivation = new_motivation
        self._save()
        msg = f"{char.name}'s motivation shifts: {new_motivation}"
        if reason:
            msg += f" ({reason})"
        self._emit("💭", msg)
        return {"status": "success", "old_motivation": old_motivation}
    
    def add_memory(self, character_id: str, memory: str, importance: str = "medium") -> Dict:
        """Record a memory."""
        char = self._get_char(character_id)
        if not char:
            return {"status": "error", "message": "Invalid"}
        char.memory.append(Memory(
            content=memory,
            importance=importance,
            turn=self.state.time
        ))
        self._save()
        emoji = "⭐" if importance == "high" else "📝"
        self._emit(emoji, f"{char.name} remembers: {memory}")
        return {"status": "success"}

    # === World Modification Actions ===
    
    def create_small_item(self, character_id: str, item_name: str, description: str = "") -> Dict:
        """Create a small item (validated)."""
        char = self._get_char(character_id)
        loc = self._get_loc(char.location_id)
        if not char or not loc:
            return {"status": "error", "message": "Invalid"}
        
        # Validate: only small, mundane items
        forbidden = ["artifact", "magical", "weapon", "sword", "gold", "treasure", "coin"]
        if any(word in item_name.lower() or word in description.lower() for word in forbidden):
            return {"status": "error", "message": "Can only create small mundane items like notes, crude tools, etc."}
        
        loc.items.append(item_name)
        self._save()
        self._emit("🛠️", f"{char.name} creates: {item_name}")
        return {"status": "success"}
    
    def modify_feature(self, character_id: str, feature: str, modification: str) -> Dict:
        """Modify a location feature."""
        char = self._get_char(character_id)
        loc = self._get_loc(char.location_id)
        if not char or not loc:
            return {"status": "error", "message": "Invalid"}
        
        # Check if feature exists
        if not loc.features or feature not in loc.features:
            return {"status": "error", "message": f"Feature '{feature}' doesn't exist here", "available_features": loc.features or []}
        
        # Record the modification
        modified_feature = f"{feature} ({modification})"
        idx = loc.features.index(feature)
        loc.features[idx] = modified_feature
        self._save()
        self._emit("🔧", f"{char.name} modifies {feature}: {modification}")
        return {"status": "success"}
    
    def steal(self, character_id: str, item_name: str, target: str = "from the location") -> Dict:
        """Steal an item (requires stealth check)."""
        char = self._get_char(character_id)
        loc = self._get_loc(char.location_id)
        if not char or not loc:
            return {"status": "error", "message": "Invalid"}
        
        # Find the item
        if target != "from the location":
            target_char = self._find_target(char, target)
            if not target_char:
                return {"status": "error", "message": f"Target not found: {target}"}
            if item_name not in target_char.inventory:
                return {"status": "error", "message": f"{target} doesn't have {item_name}"}
            
            # Require stealth check to steal from person
            modifier = get_skill_modifier(char, "stealth")
            roll = random.randint(1, 20)
            total = roll + modifier
            difficulty = 15  # Hard check
            
            self._emit("🎲", f"🎲 {char.name} Stealth: {total} (d20={roll}, mod={modifier}) vs DC {difficulty}")
            
            if total >= difficulty:
                target_char.inventory.remove(item_name)
                char.inventory.append(item_name)
                self._save()
                self._emit("🥷", f"{char.name} stealthily steals {item_name} from {target_char.name}!")
                return {"status": "success", "stolen_from": target_char.name}
            else:
                self._emit("⚠️", f"{target_char.name} notices {char.name} trying to steal!")
                return {"status": "failure", "message": "Caught in the act!"}
        else:
            # Stealing from location is easier (just pickup)
            if item_name not in loc.items:
                return {"status": "error", "message": f"Item not here: {item_name}"}
            loc.items.remove(item_name)
            char.inventory.append(item_name)
            self._save()
            self._emit("🥷", f"{char.name} takes {item_name} quietly")
            return {"status": "success"}
    
    def hide_item(self, character_id: str, item_name: str, location: str) -> Dict:
        """Hide an item."""
        char = self._get_char(character_id)
        loc = self._get_loc(char.location_id)
        if not char or not loc:
            return {"status": "error", "message": "Invalid"}
        
        # Check if character has the item
        if item_name not in char.inventory:
            return {"status": "error", "message": f"Don't have {item_name}"}
        
        # Hide it (add to location with hidden prefix)
        char.inventory.remove(item_name)
        hidden_item = f"hidden: {item_name} ({location})"
        loc.items.append(hidden_item)
        self._save()
        self._emit("🫥", f"{char.name} hides {item_name} {location}")
        return {"status": "success"}

    # === Item Lifecycle Management ===
    
    def destroy_item(self, character_id: str, item_name: str, method: str = "") -> Dict:
        """Destroy an item permanently."""
        char = self._get_char(character_id)
        loc = self._get_loc(char.location_id)
        if not char:
            return {"status": "error", "message": "Invalid"}
        
        # Check inventory first, then location
        if item_name in char.inventory:
            char.inventory.remove(item_name)
            self._save()
            self._emit("🔥", f"{char.name} destroys {item_name}" + (f" ({method})" if method else ""))
            return {"status": "success", "location": "inventory"}
        elif loc and item_name in loc.items:
            loc.items.remove(item_name)
            self._save()
            self._emit("🔥", f"{char.name} destroys {item_name}" + (f" ({method})" if method else ""))
            return {"status": "success", "location": "ground"}
        else:
            return {"status": "error", "message": f"Don't have {item_name} to destroy"}
    
    def consume_item(self, character_id: str, item_name: str, effect: str = "") -> Dict:
        """Consume an item (removes it from game)."""
        char = self._get_char(character_id)
        if not char:
            return {"status": "error", "message": "Invalid"}
        
        found = next((i for i in char.inventory if i.lower() == item_name.lower()), None)
        if not found:
            return {"status": "error", "message": f"Don't have {item_name}"}
        
        char.inventory.remove(found)
        self._save()
        
        msg = f"{char.name} consumes {found}"
        if effect:
            msg += f" - {effect}"
        self._emit("🍴", msg)
        
        # Auto-heal if it's a potion
        if "potion" in item_name.lower() or "elixir" in item_name.lower():
            heal = 8
            before = char.stats.hp
            char.stats.hp = min(char.stats.max_hp, char.stats.hp + heal)
            self._save()
            self._emit("💖", f"{char.name} heals for {char.stats.hp - before} HP")
        
        return {"status": "success"}
    
    def drop_item(self, character_id: str, item_name: str) -> Dict:
        """Drop item from inventory to location."""
        char = self._get_char(character_id)
        loc = self._get_loc(char.location_id)
        if not char or not loc:
            return {"status": "error", "message": "Invalid"}
        
        found = next((i for i in char.inventory if i.lower() == item_name.lower()), None)
        if not found:
            return {"status": "error", "message": f"Don't have {item_name}"}
        
        char.inventory.remove(found)
        loc.items.append(found)
        self._save()
        self._emit("📦", f"{char.name} drops {found}")
        return {"status": "success"}
