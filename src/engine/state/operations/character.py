"""
Character-scoped operations: movement, dialogue, items, stats, relationships, knowledge.
"""

from src.engine.state.operations._base import _OpsBase

_XP_PER_LEVEL = 100


class CharacterOps(_OpsBase):
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

    def trade_item(self, buyer_id: str, seller_id: str, item: str, price: int) -> str:
        buyer = self.state.characters.get(buyer_id)
        if not buyer: return f"Cannot trade — character '{buyer_id}' not found."

        seller = self.state.characters.get(seller_id)
        if not seller: return f"Cannot trade — character '{seller_id}' not found."
        if buyer.location != seller.location: return f"Cannot trade — '{buyer_id}' and '{seller_id}' are not in the same location."
        if item not in seller.inventory: return f"Cannot trade — '{seller_id}' doesn't have '{item}'."
        price = max(0, price)
        if buyer.stats.gold < price: return f"Cannot trade — '{buyer_id}' doesn't have enough gold ({buyer.stats.gold} < {price})."

        seller.inventory.remove(item)
        buyer.inventory.append(item)
        buyer.stats.gold -= price
        seller.stats.gold += price
        result = f"{buyer_id} buys '{item}' from {seller_id} for {price} gold."
        self._log(result, buyer.location, [buyer_id, seller_id])
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

    def award_xp(self, character_id: str, amount: int, reason: str = "") -> str:
        char = self.state.characters.get(character_id)
        if not char: return f"Cannot award XP — character '{character_id}' not found."

        amount = max(0, amount)
        char.stats.xp += amount
        suffix = f" ({reason})" if reason else ""
        result = f"{character_id} earns {amount} XP{suffix}."
        self._log(result, char.location, [character_id])

        while char.stats.xp >= char.stats.level * _XP_PER_LEVEL:
            result += " " + self.level_up(character_id)
        return result

    def give_gold(self, from_character_id: str, to_character_id: str, amount: int) -> str:
        giver = self.state.characters.get(from_character_id)
        if not giver: return f"Cannot give gold — character '{from_character_id}' not found."

        receiver = self.state.characters.get(to_character_id)
        if not receiver: return f"Cannot give gold — character '{to_character_id}' not found."
        amount = max(0, amount)
        if giver.stats.gold < amount: return f"Cannot give gold — '{from_character_id}' only has {giver.stats.gold}."

        giver.stats.gold -= amount
        receiver.stats.gold += amount
        result = f"{from_character_id} gives {amount} gold to {to_character_id}."
        self._log(result, giver.location, [from_character_id, to_character_id])
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
        result = f"{character_id} learns: {fact}"
        self._log(result, char.location, [character_id])
        return result
