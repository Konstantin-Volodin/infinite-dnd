"""
Cross-entity Operations - higher-level game actions that span multiple models.
    - move_character: move a character to a connected location.
    - take_item / drop_item: pick up or drop items at current location.
    - give_item: give an item to a living character.
    - loot_item: take an item from a dead character.
    - damage / heal: modify character HP with clamping.
    - level_up: increment character level and max_hp.
    - update_relationship: set or remove a relationship between two characters.
    - add_knowledge: append knowledge to a character.
    - advance_quest: update quest status or add a step.
    - spawn_npc / delete_npc: add or remove characters from the world.
    - create_item: add an item to a location.
    - add_location / modify_location / remove_location: manage locations.
    - tick_time: advance world time and log a history event.

All operations return a string describing the outcome (success or failure reason).
"""

from src.engine.state.models import WorldState, HistoryEvent, Character, Location


class WorldOperations:
    """Cross-entity operations that coordinate changes across multiple models."""

    def __init__(self, state: WorldState):
        self.state = state

    def _log(self, text: str, location: str, characters: list[str] | None = None) -> None:
        self.state.history.append(HistoryEvent(text=text, location=location, characters=characters or []))

    # ============ MOVEMENT ============
    def move_character(self, character_id: str, destination_id: str) -> str:
        """Move a character to a connected location."""
        char = self.state.characters.get(character_id)
        if not char: return f"Cannot move — character '{character_id}' not found."

        current = self.state.locations.get(char.location)
        if destination_id not in self.state.locations: return f"Cannot move to '{destination_id}' — location not found."
        if current and destination_id not in current.connections: return f"Cannot reach '{destination_id}' from '{char.location}' — connected locations: {current.connections}."

        char.location = destination_id
        result = f"{character_id} moved to '{destination_id}'."
        self._log(result, destination_id, [character_id])
        return result

    # ============ DIALOGUE ============
    def speak(self, character_id: str, message: str, target_id: str | None = None) -> str:
        """Character says something, optionally directed at another character."""
        char = self.state.characters.get(character_id)
        if not char: return f"Cannot speak — character '{character_id}' not found."
        if target_id and target_id not in self.state.characters: return f"Cannot speak to '{target_id}' — character not found."

        result = f"{character_id} says to {target_id}: \"{message}\"" if target_id else f"{character_id} says: \"{message}\""
        characters = [character_id, target_id] if target_id else [character_id]
        self._log(result, char.location, characters)
        return result

    # ============ ITEMS ============
    def take_item(self, character_id: str, item: str) -> str:
        """Character picks up an item from their current location."""
        char = self.state.characters.get(character_id)
        if not char: return f"Cannot take item — character '{character_id}' not found."

        loc = self.state.locations.get(char.location)
        if not loc: return f"Cannot take item — location '{char.location}' not found."
        if item not in loc.items: return f"Cannot take '{item}' — it's not at '{char.location}'."

        loc.items.remove(item)
        char.inventory.append(item)
        result = f"{character_id} picks up '{item}'."
        self._log(result, char.location, [character_id])
        return result

    def drop_item(self, character_id: str, item: str) -> str:
        """Character drops an item at their current location."""
        char = self.state.characters.get(character_id)
        if not char: return f"Cannot drop item — character '{character_id}' not found."
        if item not in char.inventory: return f"Cannot drop '{item}' — {character_id} doesn't have it."

        loc = self.state.locations.get(char.location)
        if not loc: return f"Cannot drop item — location '{char.location}' not found."

        char.inventory.remove(item)
        loc.items.append(item)
        result = f"{character_id} drops '{item}' at '{char.location}'."
        self._log(result, char.location, [character_id])
        return result

    def give_item(self, from_character_id: str, to_character_id: str, item: str) -> str:
        """Character gives an item to another living character in the same location."""
        giver = self.state.characters.get(from_character_id)
        if not giver: return f"Cannot give item — character '{from_character_id}' not found."

        receiver = self.state.characters.get(to_character_id)
        if not receiver: return f"Cannot give item — character '{to_character_id}' not found."
        if giver.location != receiver.location: return f"Cannot give item — '{from_character_id}' and '{to_character_id}' are not in the same location."
        if receiver.stats.hp <= 0: return f"Cannot give item — '{to_character_id}' is dead."
        if item not in giver.inventory: return f"Cannot give '{item}' — {from_character_id} doesn't have it."

        giver.inventory.remove(item)
        receiver.inventory.append(item)
        result = f"{from_character_id} gives '{item}' to {to_character_id}."
        self._log(result, giver.location, [from_character_id, to_character_id])
        return result

    def loot_item(self, character_id: str, target_id: str, item: str) -> str:
        """Character takes an item from a dead character in the same location."""
        char = self.state.characters.get(character_id)
        if not char: return f"Cannot loot — character '{character_id}' not found."

        target = self.state.characters.get(target_id)
        if not target: return f"Cannot loot — character '{target_id}' not found."
        if char.location != target.location: return f"Cannot loot — '{character_id}' and '{target_id}' are not in the same location."
        if target.stats.hp > 0: return f"Cannot loot '{target_id}' — they are still alive."
        if item not in target.inventory: return f"Cannot loot '{item}' — {target_id} doesn't have it."

        target.inventory.remove(item)
        char.inventory.append(item)
        result = f"{character_id} loots '{item}' from {target_id}."
        self._log(result, char.location, [character_id, target_id])
        return result

    # ============ STATS ============
    def damage(self, character_id: str, amount: int) -> str:
        """Deal damage to a character."""
        char = self.state.characters.get(character_id)
        if not char: return f"Cannot damage — character '{character_id}' not found."

        char.stats.hp = max(0, char.stats.hp - amount)
        result = f"{character_id} takes {amount} damage. HP: {char.stats.hp}/{char.stats.max_hp}."
        self._log(result, char.location, [character_id])
        return result

    def heal(self, character_id: str, amount: int) -> str:
        """Heal a character."""
        char = self.state.characters.get(character_id)
        if not char: return f"Cannot heal — character '{character_id}' not found."

        char.stats.hp = min(char.stats.max_hp, char.stats.hp + amount)
        result = f"{character_id} heals {amount} HP. HP: {char.stats.hp}/{char.stats.max_hp}."
        self._log(result, char.location, [character_id])
        return result

    def level_up(self, character_id: str, hp_increase: int = 5) -> str:
        """Level up a character, increasing level and max_hp."""
        char = self.state.characters.get(character_id)
        if not char: return f"Cannot level up — character '{character_id}' not found."

        char.stats.level += 1
        char.stats.max_hp += hp_increase
        char.stats.hp = char.stats.max_hp
        result = f"{character_id} leveled up to level {char.stats.level}. Max HP increased to {char.stats.max_hp}."
        self._log(result, char.location, [character_id])
        return result

    # ============ RELATIONSHIPS ============
    def update_relationship(self, character_id: str, target_id: str, relation: str) -> str:
        """Set a relationship from one character to another."""
        char = self.state.characters.get(character_id)
        if not char: return f"Cannot update relationship — character '{character_id}' not found."
        if target_id not in self.state.characters: return f"Cannot update relationship — character '{target_id}' not found."

        char.relationships[target_id] = relation
        return f"{character_id}'s relationship with {target_id} is now '{relation}'."

    def remove_relationship(self, character_id: str, target_id: str) -> str:
        """Remove a relationship between two characters."""
        char = self.state.characters.get(character_id)
        if not char: return f"Cannot remove relationship — character '{character_id}' not found."
        if target_id not in char.relationships: return f"{character_id} has no relationship with '{target_id}'."

        del char.relationships[target_id]
        return f"{character_id}'s relationship with {target_id} removed."

    # ============ KNOWLEDGE ============
    def add_knowledge(self, character_id: str, fact: str) -> str:
        """Add a piece of knowledge to a character (no duplicates)."""
        char = self.state.characters.get(character_id)
        if not char: return f"Cannot add knowledge — character '{character_id}' not found."
        if fact in char.knowledge: return f"{character_id} already knows that."

        char.knowledge.append(fact)
        return f"{character_id} learns: {fact}"

    # ============ QUESTS ============
    def advance_quest(self, quest_id: str, new_status: str | None = None, step: str | None = None) -> str:
        """Update a quest's status and/or add a step."""
        quest = self.state.quests.get(quest_id)
        if not quest: return f"Cannot advance quest — '{quest_id}' not found."

        if new_status: quest.status = new_status
        if step: quest.steps.append(step)
        return f"Quest '{quest_id}' updated."

    # ============ CHARACTERS ============
    def spawn_npc(self, npc_id: str, role: str, location_id: str, backstory: str = "", goal: str = "") -> str:
        """Spawn a new NPC at a location."""
        if npc_id in self.state.characters: return f"Cannot spawn '{npc_id}' — character already exists."
        if location_id not in self.state.locations: return f"Cannot spawn '{npc_id}' — location '{location_id}' not found."

        self.state.characters[npc_id] = Character(id=npc_id, role=role, location=location_id, backstory=backstory, goal=goal)
        result = f"{npc_id} appears at '{location_id}'."
        self._log(result, location_id, [npc_id])
        return result

    def delete_npc(self, npc_id: str, reason: str = "") -> str:
        """Remove an NPC from the world."""
        char = self.state.characters.get(npc_id)
        if not char: return f"Cannot delete '{npc_id}' — character not found."

        location = char.location
        del self.state.characters[npc_id]
        result = f"{npc_id} is gone. {reason}".strip()
        self._log(result, location)
        return result

    # ============ ITEMS ============
    def create_item(self, item: str, location_id: str) -> str:
        """Create a new item at a location."""
        loc = self.state.locations.get(location_id)
        if not loc: return f"Cannot create item — location '{location_id}' not found."
        if item in loc.items: return f"'{item}' already exists at '{location_id}'."

        loc.items.append(item)
        result = f"'{item}' appears at '{location_id}'."
        self._log(result, location_id)
        return result

    # ============ LOCATIONS ============
    def add_location(self, location_id: str, description: str = "", connections: list[str] | None = None) -> str:
        """Add a new location, optionally connected to existing ones."""
        if location_id in self.state.locations: return f"Location '{location_id}' already exists."

        validated_connections = [c for c in (connections or []) if c in self.state.locations]
        self.state.locations[location_id] = Location(id=location_id, description=description, connections=validated_connections)

        for c in validated_connections:
            if location_id not in self.state.locations[c].connections:
                self.state.locations[c].connections.append(location_id)

        return f"Location '{location_id}' added."

    def modify_location(self, location_id: str, description: str | None = None, add_feature: str | None = None, remove_feature: str | None = None) -> str:
        """Update a location's description or features."""
        loc = self.state.locations.get(location_id)
        if not loc: return f"Cannot modify — location '{location_id}' not found."

        if description: loc.description = description
        if add_feature and add_feature not in loc.features: loc.features.append(add_feature)
        if remove_feature and remove_feature in loc.features: loc.features.remove(remove_feature)
        return f"Location '{location_id}' updated."

    def remove_location(self, location_id: str) -> str:
        """Remove a location and clean up connections."""
        if location_id not in self.state.locations: return f"Cannot remove — location '{location_id}' not found."

        for loc in self.state.locations.values():
            if location_id in loc.connections:
                loc.connections.remove(location_id)

        del self.state.locations[location_id]
        return f"Location '{location_id}' removed."

    # ============ TIME ============
    def tick_time(self, event_text: str, location: str, characters: list[str] | None = None) -> str:
        """Advance world time by 1 and log a history event."""
        self.state.time += 1
        self._log(event_text, location, characters)
        return f"Time advanced to {self.state.time}. Event logged: {event_text}"


if __name__ == "__main__":

    import logging
    from src.engine.state.models import WorldState, Location, Character, CharacterStats, Quest

    logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")

    # setup test world
    state = WorldState(
        locations={
            "tavern": Location(id="tavern", description="a cozy tavern", connections=["forest"], items=["ale"]),
            "forest": Location(id="forest", description="a dark forest", connections=["tavern", "cave"]),
            "cave": Location(id="cave", description="a damp cave", connections=["forest"]),
        },
        characters={
            "hero": Character(id="hero", role="warrior", location="tavern", inventory=["sword"], stats=CharacterStats(hp=20, max_hp=20, level=1)),
            "merchant": Character(id="merchant", role="shopkeeper", location="tavern", inventory=["potion", "shield"]),
        },
        quests={
            "q1": Quest(id="q1", title="Clear the Cave", description="Defeat the creatures in the cave", owner="hero"),
        },
    )
    ops = WorldOperations(state)

    # movement
    ops.move_character("hero", "forest")
    assert state.characters["hero"].location == "forest"
    ops.move_character("hero", "cave")
    assert state.characters["hero"].location == "cave"
    logging.info("Movement tests passed.")

    # movement validation
    try:
        ops.move_character("hero", "tavern")  # cave only connects to forest
        assert False, "Should have raised ValueError"
    except ValueError:
        pass
    logging.info("Movement validation test passed.")

    # take item from location
    ops.move_character("hero", "forest")
    ops.move_character("hero", "tavern")
    ops.take_item("hero", "ale")
    assert "ale" in state.characters["hero"].inventory
    assert "ale" not in state.locations["tavern"].items
    logging.info("Take item test passed.")

    # drop item at location
    ops.drop_item("hero", "ale")
    assert "ale" not in state.characters["hero"].inventory
    assert "ale" in state.locations["tavern"].items
    logging.info("Drop item test passed.")

    # give item to living character (both in tavern)
    ops.give_item("merchant", "hero", "potion")
    assert "potion" in state.characters["hero"].inventory
    assert "potion" not in state.characters["merchant"].inventory
    logging.info("Give item test passed.")

    # loot item from dead character
    ops.damage("merchant", 100)
    assert state.characters["merchant"].stats.hp == 0
    ops.loot_item("hero", "merchant", "shield")
    assert "shield" in state.characters["hero"].inventory
    assert "shield" not in state.characters["merchant"].inventory
    logging.info("Loot item test passed.")

    # cannot give to dead character
    try:
        ops.give_item("hero", "merchant", "potion")
        assert False, "Should have raised ValueError"
    except ValueError:
        pass
    logging.info("Give to dead validation test passed.")

    # cannot loot from living character
    ops.heal("merchant", 100)
    try:
        ops.loot_item("hero", "merchant", "shield")
        assert False, "Should have raised ValueError"
    except ValueError:
        pass
    logging.info("Loot from living validation test passed.")

    # damage and heal
    ops.damage("hero", 8)
    assert state.characters["hero"].stats.hp == 12
    ops.heal("hero", 3)
    assert state.characters["hero"].stats.hp == 15
    ops.damage("hero", 100)
    assert state.characters["hero"].stats.hp == 0  # clamped
    ops.heal("hero", 100)
    assert state.characters["hero"].stats.hp == 20  # clamped to max
    logging.info("Damage/heal tests passed.")

    # level up
    ops.level_up("hero")
    assert state.characters["hero"].stats.level == 2
    assert state.characters["hero"].stats.max_hp == 25
    assert state.characters["hero"].stats.hp == 25  # healed to new max
    logging.info("Level up test passed.")

    # relationships
    ops.update_relationship("hero", "merchant", "friendly")
    assert state.characters["hero"].relationships["merchant"] == "friendly"
    ops.remove_relationship("hero", "merchant")
    assert "merchant" not in state.characters["hero"].relationships
    logging.info("Relationship tests passed.")

    # knowledge
    ops.add_knowledge("hero", "The cave has a hidden passage")
    assert "The cave has a hidden passage" in state.characters["hero"].knowledge
    ops.add_knowledge("hero", "The cave has a hidden passage")  # no duplicate
    assert state.characters["hero"].knowledge.count("The cave has a hidden passage") == 1
    logging.info("Knowledge tests passed.")

    # quest advancement
    ops.advance_quest("q1", step="Entered the cave")
    assert "Entered the cave" in state.quests["q1"].steps
    ops.advance_quest("q1", new_status="completed")
    assert state.quests["q1"].status == "completed"
    logging.info("Quest advancement tests passed.")

    # tick time
    new_time = ops.tick_time("Hero cleared the cave", location="cave", characters=["hero"])
    assert state.time == 1
    assert len(state.history) == 1
    assert state.history[0].text == "Hero cleared the cave"
    logging.info("Tick time test passed.")

    logging.info(f"{__file__} tests completed successfully.")
