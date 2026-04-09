"""
Character-scoped operations: movement, dialogue, items, stats, relationships, knowledge.
"""

from src.engine.state.models import WorldState, HistoryEvent


class CharacterOps:
    def __init__(self, state: WorldState):
        self.state = state

    def _log(self, text: str, location: str, characters: list[str] | None = None) -> None:
        self.state.history.append(HistoryEvent(text=text, location=location, characters=characters or []))

    # ============ MOVEMENT ============
    def move_character(self, character_id: str, destination_id: str) -> str:
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
        char = self.state.characters.get(character_id)
        if not char: return f"Cannot speak — character '{character_id}' not found."
        if target_id and target_id not in self.state.characters: return f"Cannot speak to '{target_id}' — character not found."

        result = f"{character_id} says to {target_id}: \"{message}\"" if target_id else f"{character_id} says: \"{message}\""
        characters = [character_id, target_id] if target_id else [character_id]
        self._log(result, char.location, characters)
        return result

    # ============ ITEMS ============
    def take_item(self, character_id: str, item: str) -> str:
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
        char = self.state.characters.get(character_id)
        if not char: return f"Cannot damage — character '{character_id}' not found."

        char.stats.hp = max(0, char.stats.hp - amount)
        result = f"{character_id} takes {amount} damage. HP: {char.stats.hp}/{char.stats.max_hp}."
        self._log(result, char.location, [character_id])
        return result

    def heal(self, character_id: str, amount: int) -> str:
        char = self.state.characters.get(character_id)
        if not char: return f"Cannot heal — character '{character_id}' not found."

        char.stats.hp = min(char.stats.max_hp, char.stats.hp + amount)
        result = f"{character_id} heals {amount} HP. HP: {char.stats.hp}/{char.stats.max_hp}."
        self._log(result, char.location, [character_id])
        return result

    def level_up(self, character_id: str, hp_increase: int = 5) -> str:
        char = self.state.characters.get(character_id)
        if not char: return f"Cannot level up — character '{character_id}' not found."

        char.stats.level += 1
        char.stats.max_hp += hp_increase
        char.stats.hp = char.stats.max_hp
        result = f"{character_id} leveled up to level {char.stats.level}. Max HP increased to {char.stats.max_hp}."
        self._log(result, char.location, [character_id])
        return result

    # ============ CHARACTER UPDATE ============
    def update_character(self, character_id: str, backstory: str | None = None, personality: str | None = None, goal: str | None = None, role: str | None = None) -> str:
        char = self.state.characters.get(character_id)
        if not char: return f"Cannot update — character '{character_id}' not found."

        if backstory is not None: char.backstory = backstory
        if personality is not None: char.personality = personality
        if goal is not None: char.goal = goal
        if role is not None: char.role = role
        return f"{character_id} updated."

    # ============ RELATIONSHIPS ============
    def update_relationship(self, character_id: str, target_id: str, relation: str) -> str:
        char = self.state.characters.get(character_id)
        if not char: return f"Cannot update relationship — character '{character_id}' not found."
        if target_id not in self.state.characters: return f"Cannot update relationship — character '{target_id}' not found."

        char.relationships[target_id] = relation
        return f"{character_id}'s relationship with {target_id} is now '{relation}'."

    def remove_relationship(self, character_id: str, target_id: str) -> str:
        char = self.state.characters.get(character_id)
        if not char: return f"Cannot remove relationship — character '{character_id}' not found."
        if target_id not in char.relationships: return f"{character_id} has no relationship with '{target_id}'."

        del char.relationships[target_id]
        return f"{character_id}'s relationship with {target_id} removed."

    # ============ KNOWLEDGE ============
    def add_knowledge(self, character_id: str, fact: str) -> str:
        char = self.state.characters.get(character_id)
        if not char: return f"Cannot add knowledge — character '{character_id}' not found."
        if fact in char.knowledge: return f"{character_id} already knows that."

        char.knowledge.append(fact)
        return f"{character_id} learns: {fact}"


if __name__ == "__main__":

    import logging
    from src.engine.state.models import WorldState, Location, Character, CharacterStats

    logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")

    state = WorldState(
        locations={
            "tavern": Location(id="tavern", connections=["forest"], items=["ale"]),
            "forest": Location(id="forest", connections=["tavern", "cave"]),
            "cave": Location(id="cave", connections=["forest"]),
        },
        characters={
            "hero": Character(id="hero", role="warrior", location="tavern", inventory=["sword"], stats=CharacterStats(hp=20, max_hp=20, level=1)),
            "merchant": Character(id="merchant", role="shopkeeper", location="tavern", inventory=["potion", "shield"]),
        },
    )
    ops = CharacterOps(state)

    # movement
    ops.move_character("hero", "forest")
    assert state.characters["hero"].location == "forest"
    ops.move_character("hero", "cave")
    assert state.characters["hero"].location == "cave"
    assert "Cannot reach" in ops.move_character("hero", "tavern")  # cave only connects to forest
    logging.info("Movement tests passed.")

    # take / drop
    ops.move_character("hero", "forest")
    ops.move_character("hero", "tavern")
    ops.take_item("hero", "ale")
    assert "ale" in state.characters["hero"].inventory
    assert "ale" not in state.locations["tavern"].items
    ops.drop_item("hero", "ale")
    assert "ale" not in state.characters["hero"].inventory
    assert "ale" in state.locations["tavern"].items
    logging.info("Take/drop tests passed.")

    # give / loot
    ops.give_item("merchant", "hero", "potion")
    assert "potion" in state.characters["hero"].inventory
    ops.damage("merchant", 100)
    assert state.characters["merchant"].stats.hp == 0
    ops.loot_item("hero", "merchant", "shield")
    assert "shield" in state.characters["hero"].inventory
    assert "Cannot give" in ops.give_item("hero", "merchant", "potion")  # dead
    ops.heal("merchant", 100)
    assert "Cannot loot" in ops.loot_item("hero", "merchant", "shield")  # alive
    logging.info("Give/loot tests passed.")

    # damage / heal / level_up
    ops.damage("hero", 8)
    assert state.characters["hero"].stats.hp == 12
    ops.heal("hero", 3)
    assert state.characters["hero"].stats.hp == 15
    ops.damage("hero", 100)
    assert state.characters["hero"].stats.hp == 0
    ops.heal("hero", 100)
    assert state.characters["hero"].stats.hp == 20
    ops.level_up("hero")
    assert state.characters["hero"].stats.level == 2
    assert state.characters["hero"].stats.max_hp == 25
    assert state.characters["hero"].stats.hp == 25
    logging.info("Stats tests passed.")

    # update character
    ops.update_character("hero", goal="find the artifact", personality="brooding")
    assert state.characters["hero"].goal == "find the artifact"
    assert state.characters["hero"].personality == "brooding"
    assert "Cannot update" in ops.update_character("ghost", goal="haunt")
    logging.info("Update character tests passed.")

    # relationships
    ops.update_relationship("hero", "merchant", "friendly")
    assert state.characters["hero"].relationships["merchant"] == "friendly"
    ops.remove_relationship("hero", "merchant")
    assert "merchant" not in state.characters["hero"].relationships
    logging.info("Relationship tests passed.")

    # knowledge
    ops.add_knowledge("hero", "The cave has a hidden passage")
    assert "The cave has a hidden passage" in state.characters["hero"].knowledge
    ops.add_knowledge("hero", "The cave has a hidden passage")
    assert state.characters["hero"].knowledge.count("The cave has a hidden passage") == 1
    logging.info("Knowledge tests passed.")

    logging.info(f"{__file__} tests completed successfully.")
