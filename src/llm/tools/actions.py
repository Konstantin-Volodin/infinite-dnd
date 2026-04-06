"""Action execution — what happens when a tool is called.

Character: act, speak, move, think, wait
DM: narrate, create, modify (and their sub-actions)
"""

import random
from typing import Dict, Optional
from ...core.models import WorldState, Location, Character, CharacterStats
from ...core.rules import get_skill_modifier
from ...core.utils import slugify


class ActionExecutor:
    """Executes game actions and updates state."""

    def __init__(self, state: WorldState, save_state, save_history):
        self.state = state
        self.save_state = save_state
        self.save_history = save_history

    def log_action(self, icon: str, msg: str):
        print(f"  {icon} {msg}")

    def _get_char(self, char_id: str) -> Optional[Character]:
        return self.state.characters.get(char_id)

    def _get_loc(self, loc_id: str) -> Optional[Location]:
        return self.state.locations.get(loc_id)

    def _find_target(self, char: Character, target_name: str) -> Optional[Character]:
        """Find a character by name at the same location (fuzzy match)."""
        target_lower = target_name.lower()
        for c in self.state.characters.values():
            if c.location == char.location and c.id != char.id:
                c_name_lower = c.id.lower()
                if (
                    target_lower == c_name_lower
                    or target_lower in c_name_lower
                    or c_name_lower in target_lower
                ):
                    return c
        return None

    def _default_anchor_location(self) -> Optional[str]:
        first_char = next(iter(self.state.characters.values()), None)
        if first_char and first_char.location in self.state.locations:
            return first_char.location
        return next(iter(self.state.locations.keys()), None)

    # =========================================================================
    # CHARACTER ACTIONS
    # =========================================================================

    def act(
        self,
        character_id: str,
        description: str,
        skill: Optional[str] = None,
        target: Optional[str] = None,
    ) -> Dict:
        char = self._get_char(character_id)
        if not char:
            return {"status": "error", "message": "Character not found"}

        loc = self._get_loc(char.location)

        roll_info = None
        if skill:
            roll = random.randint(1, 20)
            modifier = get_skill_modifier(char, skill)
            total = roll + modifier
            roll_info = f"[{skill}: {roll}+{modifier}={total}]"

        intent = f"{char.id} {description}"
        if roll_info:
            intent += f" {roll_info}"

        self.log_action("⚔️", intent)
        self.save_history(intent, char.location)

        return {
            "status": "success",
            "character": char.id,
            "action": description,
            "skill": skill,
            "target": target,
            "location": loc.id if loc else "unknown",
            "roll_info": roll_info,
            "action_type": "act",
            "intent": intent,
            "dm_guidance": f"Narrate {char.id}'s action: '{description}'" + (f" (Roll: {roll_info})" if roll_info else ""),
        }

    def speak(self, character_id: str, message: str, target: str = None) -> Dict:
        char = self._get_char(character_id)
        if not char:
            return {"status": "error", "message": "Character not found"}
        if not message:
            return {"status": "error", "message": "Message is required"}

        if target:
            target_char = self._find_target(char, target)
            target_name = target_char.id if target_char else target
            intent = f'{char.id} says to {target_name}: "{message}"'
        else:
            intent = f'{char.id} says: "{message}"'

        self.log_action("💬", intent)
        self.save_history(intent, char.location)

        return {
            "status": "success",
            "character": char.id,
            "action_type": "speak",
            "intent": intent,
            "message": message,
            "target": target,
            "dm_guidance": f"Narrate {char.id}'s dialogue with prose: \"{message}\"",
        }

    def move(self, character_id: str, location: str) -> Dict:
        char = self._get_char(character_id)
        if not char:
            return {"status": "error", "message": "Character not found"}

        current_loc = self._get_loc(char.location)
        new_loc = self._get_loc(location)
        if not new_loc:
            if current_loc and location in (current_loc.connections or []):
                return {
                    "status": "error",
                    "code": "location_missing",
                    "target_name": location,
                    "origin_id": current_loc.id,
                    "message": "Location not found",
                }
            return {"status": "error", "message": "Location not found"}

        if not current_loc or location not in current_loc.connections:
            return {"status": "error", "message": f"Cannot reach {new_loc.id} from here"}

        origin_id = current_loc.id
        self.save_history(f"{char.id} left towards {new_loc.id}", origin_id)
        char.location = location
        self.save_state()
        self.save_history(f"{char.id} arrived from {origin_id}", new_loc.id)
        self.log_action("🚶", f"{char.id} moves to {new_loc.id}")
        return {"status": "success"}

    def think(
        self,
        character_id: str,
        goals: Optional[str] = None,
        emotions: Optional[str] = None,
        knowledge: Optional[str] = None,
    ) -> Dict:
        char = self._get_char(character_id)
        if not char:
            return {"status": "error", "message": "Character not found"}

        updates = []
        if goals:
            char.goal = goals
            updates.append(f"goals: {goals}")
        if emotions:
            updates.append(f"emotions: {emotions}")
        if knowledge and knowledge not in char.knowledge:
            char.knowledge.append(knowledge)
            updates.append(f"learned: {knowledge}")

        if updates:
            self.save_state()
            self.log_action("🧠", f"{char.id} updates state: {', '.join(updates)}")

        return {"status": "success"}

    def wait(self, character_id: str = None, reason: str = None, content: str = None) -> Dict:
        char = self._get_char(character_id) if character_id else None

        if content and char:
            self.log_action("💭", f"{char.id} reflects: {content[:200]}...")
            return {"status": "success", "introspection": content}

        if char:
            msg = f"{char.id} waits"
            if reason:
                msg += f" ({reason})"
            self.log_action("⏳", msg)

        return {"status": "success"}

    # =========================================================================
    # DM ACTIONS
    # =========================================================================

    def narrate(self, content: str = None, text: str = None, location: str = "") -> Dict:
        narration = content or text or ""
        if narration:
            self.log_action("📖", f"DM: {narration}")
            self.save_history(narration, location)
        return {"status": "success"}

    def create_location(
        self,
        location: str,
        name: str,
        description: str,
        connected_to: list = None,
        anchor_location: Optional[str] = None,
    ) -> Dict:
        location = slugify(location)

        if location in self.state.locations:
            return {"status": "error", "message": "Location already exists"}

        connected_to = [c for c in (connected_to or []) if c]

        if not connected_to:
            anchor = anchor_location or self._default_anchor_location()
            if anchor and anchor != location and anchor in self.state.locations:
                connected_to = [anchor]

        unique_connections = list(dict.fromkeys(connected_to))

        self.state.locations[location] = Location(
            id=location,
            name=name,
            description=description,
            connections=unique_connections,
        )

        for conn_id in unique_connections:
            other = self.state.locations.get(conn_id)
            if other and location not in (other.connections or []):
                other.connections.append(location)

        self.save_state()
        self.log_action("🗺️", f"New location: {name}")
        return {"status": "success"}

    def create_item(self, item_name: str, location: str) -> Dict:
        loc = self._get_loc(location)
        if not loc:
            return {"status": "error", "message": "Location not found"}
        if item_name not in loc.items:
            loc.items.append(item_name)
            self.save_state()
        return {"status": "success"}

    def spawn_npc(
        self,
        npc_id: str,
        name: str,
        role: str,
        location: str,
        description: str = "",
        goal: str = "",
    ) -> Dict:
        npc_id = slugify(npc_id)

        if npc_id in self.state.characters:
            return {"status": "error", "message": "NPC already exists"}

        loc = self._get_loc(location)
        if not loc:
            return {"status": "error", "message": "Location not found"}

        self.state.characters[npc_id] = Character(
            id=npc_id,
            role=role,
            backstory=description,
            goal=goal,
            stats=CharacterStats(hp=15, max_hp=15),
            location=location,
        )
        self.save_state()
        self.log_action("👤", f"{name} ({role}) appears at {loc.id}")
        return {"status": "success"}

    def remove_npc(self, npc_id: str, reason: str = "left") -> Dict:
        char = self._get_char(npc_id)
        if not char:
            return {"status": "error", "message": "Cannot remove"}

        name = char.id
        del self.state.characters[npc_id]
        self.save_state()
        self.log_action("👋", f"{name} {reason}")
        return {"status": "success"}

    def update_quest(self, quest_id: str, status: str, **_) -> Dict:
        if not quest_id or not status:
            return {"status": "error", "message": "quest_id and status required"}

        quest = self.state.quests.get(quest_id)
        if not quest:
            q_slug = slugify(quest_id)
            for q in self.state.quests.values():
                if slugify(q.id) == q_slug or slugify(q.title) == q_slug:
                    quest = q
                    break

        if not quest:
            return {"status": "error", "message": f"Quest '{quest_id}' not found"}

        old = quest.status
        quest.status = status
        self.save_state()
        self.log_action("📜", f"Quest '{quest.title}': {old} → {status}")
        return {"status": "success"}

    def create(
        self,
        type: str,
        name: str,
        description: str,
        id: str = None,
        location: str = None,
        role: str = None,
        goal: str = None,
        **_,
    ) -> Dict:
        if type == "location":
            location = slugify(id or name)
            return self.create_location(location=location, name=name, description=description)
        elif type == "item":
            if not location:
                location = self._default_anchor_location()
                if not location:
                    return {"status": "error", "message": "No location for item"}
            return self.create_item(item_name=name, location=location)
        elif type == "npc":
            if not location:
                location = self._default_anchor_location()
                if not location:
                    return {"status": "error", "message": "No location for NPC"}
            return self.spawn_npc(
                npc_id=slugify(id or name),
                name=name,
                role=role or "commoner",
                location=location,
                description=description,
                goal=goal or "",
            )
        else:
            return {"status": "error", "message": f"Unknown type: {type}"}

    def modify(
        self,
        action: str,
        target_id: str,
        status: str = None,
        reason: str = None,
        **_,
    ) -> Dict:
        if action == "update_quest":
            if not status:
                return {"status": "error", "message": "status required for quest update"}
            return self.update_quest(quest_id=target_id, status=status)
        elif action == "remove_npc":
            return self.remove_npc(npc_id=target_id, reason=reason or "left")
        elif action == "update_location":
            loc = self._get_loc(target_id)
            if not loc:
                return {"status": "error", "message": "Location not found"}
            if reason:
                self.log_action("🗺️", f"{loc.id}: {reason}")
            return {"status": "success"}
        else:
            return {"status": "error", "message": f"Unknown action: {action}"}
