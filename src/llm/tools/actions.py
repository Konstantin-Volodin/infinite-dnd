"""Action execution — DM tools: narrate, create, modify (and their sub-actions)."""

from typing import Dict, Optional
from ...core.models import WorldState, Location, Character, CharacterStats
from ...core.utils import slugify


class ActionExecutor:
    """Executes DM game actions and updates state."""

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

    def _default_anchor_location(self) -> Optional[str]:
        first_char = next(iter(self.state.characters.values()), None)
        if first_char and first_char.location in self.state.locations:
            return first_char.location
        return next(iter(self.state.locations.keys()), None)

    # =========================================================================
    # DM ACTIONS
    # =========================================================================

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
