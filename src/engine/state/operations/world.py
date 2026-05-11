"""
World-scoped operations: quests, characters (spawn/delete), items (world-level), locations, time.
"""

from src.engine.state.models import Character, Location, Quest
from src.engine.state.operations._base import _OpsBase


class WorldOps(_OpsBase):
    # ============ QUESTS ============
    def advance_quest(self, quest_id: str, new_status: str | None = None, step: str | None = None) -> str:
        quest = self.state.quests.get(quest_id)
        if not quest: return f"Cannot advance quest — '{quest_id}' not found."

        if new_status: quest.status = new_status
        if step: quest.steps.append(step)

        # XP award to owner — step=10, completion=50. Silent if owner isn't a known character.
        award_suffix = ""
        if quest.owner and quest.owner in self.state.characters:
            if step:
                self.award_xp(quest.owner, 10, reason=f"quest '{quest_id}' progress")
                award_suffix = f" (+10 XP to {quest.owner})"
            if new_status == "completed":
                self.award_xp(quest.owner, 50, reason=f"quest '{quest_id}' completed")
                award_suffix = f" (+50 XP to {quest.owner})"
        return f"Quest '{quest_id}' updated.{award_suffix}"

    def add_quest(self, quest_id: str, title: str, description: str = "", owner: str | None = None) -> str:
        if quest_id in self.state.quests: return f"Quest '{quest_id}' already exists."

        owner_id = owner or ""
        self.state.quests[quest_id] = Quest(id=quest_id, title=title, description=description, owner=owner_id)
        owner_loc = self.state.characters[owner_id].location if owner_id in self.state.characters else ""
        self._log(f"New quest: '{title}'" + (f" (owner: {owner_id})" if owner_id else ""), owner_loc, [owner_id] if owner_id else None)
        return f"Quest '{quest_id}' added."

    # ============ CHARACTERS ============
    def spawn_npc(self, npc_id: str, role: str, location_id: str, backstory: str = "", goal: str = "") -> str:
        if npc_id in self.state.characters: return f"Cannot spawn '{npc_id}' — character already exists."
        if location_id not in self.state.locations: return f"Cannot spawn '{npc_id}' — location '{location_id}' not found."

        self.state.characters[npc_id] = Character(id=npc_id, role=role, location=location_id, backstory=backstory, goal=goal)
        result = f"{npc_id} appears at '{location_id}'."
        self._log(result, location_id, [npc_id])
        return result

    def delete_npc(self, npc_id: str, reason: str = "") -> str:
        char = self.state.characters.get(npc_id)
        if not char: return f"Cannot delete '{npc_id}' — character not found."

        location = char.location
        del self.state.characters[npc_id]
        result = f"{npc_id} is gone. {reason}".strip()
        self._log(result, location)
        return result

    # ============ ITEMS ============
    def create_item(self, item: str, location_id: str) -> str:
        loc = self.state.locations.get(location_id)
        if not loc: return f"Cannot create item — location '{location_id}' not found."
        if item in loc.items: return f"'{item}' already exists at '{location_id}'."

        loc.items.append(item)
        result = f"'{item}' appears at '{location_id}'."
        self._log(result, location_id)
        return result

    # ============ LOCATIONS ============
    def add_location(self, location_id: str, description: str = "", connections: list[str] | None = None) -> str:
        if location_id in self.state.locations: return f"Location '{location_id}' already exists."

        validated = [c for c in (connections or []) if c in self.state.locations]
        self.state.locations[location_id] = Location(id=location_id, description=description, connections=validated)

        for c in validated:
            if location_id not in self.state.locations[c].connections:
                self.state.locations[c].connections.append(location_id)

        return f"Location '{location_id}' added."

    def modify_location(self, location_id: str, description: str | None = None, add_feature: str | None = None, remove_feature: str | None = None) -> str:
        loc = self.state.locations.get(location_id)
        if not loc: return f"Cannot modify — location '{location_id}' not found."

        if description: loc.description = description
        if add_feature and add_feature not in loc.features: loc.features.append(add_feature)
        if remove_feature and remove_feature in loc.features: loc.features.remove(remove_feature)
        return f"Location '{location_id}' updated."

    def connect_locations(self, location_a: str, location_b: str) -> str:
        if location_a not in self.state.locations: return f"Cannot connect — location '{location_a}' not found."
        if location_b not in self.state.locations: return f"Cannot connect — location '{location_b}' not found."

        loc_a, loc_b = self.state.locations[location_a], self.state.locations[location_b]
        if location_b in loc_a.connections: return f"'{location_a}' and '{location_b}' are already connected."

        loc_a.connections.append(location_b)
        loc_b.connections.append(location_a)
        return f"'{location_a}' and '{location_b}' connected."

    def disconnect_locations(self, location_a: str, location_b: str) -> str:
        if location_a not in self.state.locations: return f"Cannot disconnect — location '{location_a}' not found."
        if location_b not in self.state.locations: return f"Cannot disconnect — location '{location_b}' not found."

        loc_a, loc_b = self.state.locations[location_a], self.state.locations[location_b]
        if location_b not in loc_a.connections: return f"'{location_a}' and '{location_b}' are not connected."

        loc_a.connections.remove(location_b)
        loc_b.connections.remove(location_a)
        return f"'{location_a}' and '{location_b}' disconnected."

    def remove_location(self, location_id: str) -> str:
        if location_id not in self.state.locations: return f"Cannot remove — location '{location_id}' not found."

        for loc in self.state.locations.values():
            if location_id in loc.connections:
                loc.connections.remove(location_id)

        del self.state.locations[location_id]
        return f"Location '{location_id}' removed."

    # ============ TIME ============
    def tick_time(self, event_text: str, location: str, characters: list[str] | None = None) -> str:
        self.state.time += 1
        self._log(event_text, location, characters)
        return f"Time advanced to {self.state.time}. Event logged: {event_text}"


if __name__ == "__main__":

    import logging
    from src.engine.state.models import WorldState, Location, Quest, Character
    from src.engine.state.operations import WorldOperations

    logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")

    state = WorldState(
        locations={
            "tavern": Location(id="tavern", connections=["forest"]),
            "forest": Location(id="forest", connections=["tavern"]),
        },
        characters={
            "hero": Character(id="hero", role="warrior", location="tavern"),
        },
        quests={
            "q1": Quest(id="q1", title="Clear the Cave", description="Defeat the creatures", owner="hero"),
            "q2": Quest(id="q2", title="Ownerless Task", description="no owner", owner=""),
        },
    )
    ops = WorldOperations(state)

    # quests — step/completion award XP to owner; return string reflects award
    msg = ops.advance_quest("q1", step="Entered the cave")
    assert "Entered the cave" in state.quests["q1"].steps
    assert state.characters["hero"].stats.xp == 10
    assert "+10 XP to hero" in msg
    msg = ops.advance_quest("q1", new_status="completed")
    assert state.quests["q1"].status == "completed"
    assert state.characters["hero"].stats.xp == 60
    assert "+50 XP to hero" in msg
    # ownerless quest: no XP, no suffix
    msg = ops.advance_quest("q2", new_status="completed")
    assert state.quests["q2"].status == "completed"
    assert msg == "Quest 'q2' updated."

    # add_quest — anchored to owner's location when known
    history_before_add = len(state.history)
    msg = ops.add_quest("q3", title="Find the Map", description="locate the buried chart", owner="hero")
    assert msg == "Quest 'q3' added."
    assert "q3" in state.quests and state.quests["q3"].owner == "hero"
    assert state.history[-1].location == "tavern"
    assert "owner: hero" in state.history[-1].text
    # idempotent
    assert "already exists" in ops.add_quest("q3", title="Find the Map")
    assert len(state.history) == history_before_add + 1
    # ownerless quest: empty location, no character tag
    ops.add_quest("q4", title="Mystery", description="someone, somewhere")
    assert state.quests["q4"].owner == ""
    logging.info("Quest tests passed.")

    # spawn / delete NPC
    ops.spawn_npc("guard", "warrior", "tavern")
    assert "guard" in state.characters
    assert state.characters["guard"].location == "tavern"
    ops.delete_npc("guard", "Left the town.")
    assert "guard" not in state.characters
    assert "Cannot spawn" in ops.spawn_npc("guard", "warrior", "nowhere")  # bad location
    logging.info("Spawn/delete NPC tests passed.")

    # create item
    ops.create_item("torch", "forest")
    assert "torch" in state.locations["forest"].items
    assert "already exists" in ops.create_item("torch", "forest")
    logging.info("Create item tests passed.")

    # locations
    ops.add_location("cave", description="damp cave", connections=["forest"])
    assert "cave" in state.locations
    assert "cave" in state.locations["forest"].connections
    ops.modify_location("cave", description="very dark cave", add_feature="stalactites")
    assert state.locations["cave"].description == "very dark cave"
    assert "stalactites" in state.locations["cave"].features
    ops.remove_location("cave")
    assert "cave" not in state.locations
    assert "cave" not in state.locations["forest"].connections
    logging.info("Location tests passed.")

    # connect / disconnect
    ops.connect_locations("tavern", "forest")  # already connected via add_location above? no — cave was removed, tavern/forest still exist
    # reset: disconnect first if already connected
    if "forest" in state.locations["tavern"].connections:
        ops.disconnect_locations("tavern", "forest")
    assert "forest" not in state.locations["tavern"].connections
    assert "tavern" not in state.locations["forest"].connections
    ops.connect_locations("tavern", "forest")
    assert "forest" in state.locations["tavern"].connections
    assert "tavern" in state.locations["forest"].connections
    assert "already connected" in ops.connect_locations("tavern", "forest")
    ops.disconnect_locations("tavern", "forest")
    assert "forest" not in state.locations["tavern"].connections
    assert "not connected" in ops.disconnect_locations("tavern", "forest")
    logging.info("Connect/disconnect location tests passed.")

    # tick time
    ops.tick_time("The sun sets.", location="tavern")
    assert state.time == 1
    assert state.history[-1].text == "The sun sets."
    logging.info("Tick time test passed.")

    logging.info(f"{__file__} tests completed successfully.")
