
from src.engine.state.models import WorldState, Character, Location, CharacterStats, Quest

class StateManager:
    """CRUD operations for D&D world state management."""

    def __init__(self, state: WorldState):
        self.state = state

    # ============ LOCATIONS ============
    def add_location(self, location: Location) -> None:
        self.state.locations[location.id] = location

    def get_location(self, id: str) -> Location | None:
        return self.state.locations.get(id)

    def modify_location(self, id: str, updated_location: Location) -> None:
        if id in self.state.locations:
            self.state.locations[id] = updated_location

    def remove_location(self, id: str) -> None:
        if id in self.state.locations:
            del self.state.locations[id]
    
    def get_all_location_ids(self) -> list[str]:
        return list(self.state.locations.keys())

    # ============ CHARACTERS ============
    def add_character(self, character: Character) -> None:
        self.state.characters[character.id] = character

    def get_character(self, id: str) -> Character | None:
        return self.state.characters.get(id)

    def modify_character(self, id: str, updated_character: Character) -> None:
        if id in self.state.characters:
            self.state.characters[id] = updated_character

    def remove_character(self, id: str) -> None:
        if id in self.state.characters:
            del self.state.characters[id]

    def get_all_character_ids(self) -> list[str]:
        return list(self.state.characters.keys())

    # ============ QUESTS ============
    def add_quest(self, quest: Quest) -> None:
        self.state.quests[quest.id] = quest

    def get_quest(self, id: str) -> Quest | None:
        return self.state.quests.get(id)

    def modify_quest(self, id: str, updated_quest: Quest) -> None:
        if id in self.state.quests:
            self.state.quests[id] = updated_quest

    def remove_quest(self, id: str) -> None:
        if id in self.state.quests:
            del self.state.quests[id]

    def get_all_quest_ids(self) -> list[str]:
        return list(self.state.quests.keys())

    # ============ HISTORY ============
    def append_history(self, event: str) -> None:
        self.state.history.append(event)

if __name__ == "__main__":
    import logging
    from src.engine.state import StateLoader

    manager = StateLoader()
    state = manager.load_state()
    sm = StateManager(state)
    logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")

    # location tests
    loc = Location(id="test_loc")
    sm.add_location(loc)
    assert sm.get_location("test_loc") == loc
    sm.modify_location("test_loc", Location(id="test_loc", description="added description"))
    assert sm.get_location("test_loc").description == "added description"
    sm.remove_location("test_loc")
    assert sm.get_location("test_loc") is None
    assert len(sm.get_all_location_ids()) == 3  # assuming initial state has 3 locations
    logging.info("Location CRUD works")

    # character tests
    char = Character(id="test_char", role="test character")
    sm.add_character(char)
    assert sm.get_character("test_char") == char
    sm.modify_character("test_char", Character(id="test_char", role="modified role"))
    assert sm.get_character("test_char").role == "modified role"
    sm.remove_character("test_char")
    assert sm.get_character("test_char") is None
    assert len(sm.get_all_character_ids()) == 2  # assuming initial state has 2 characters
    logging.info("Character CRUD works")

    # quest tests
    quest = Quest(id="test_quest", title="Test Quest", description="A quest for testing")
    sm.add_quest(quest)
    assert sm.get_quest("test_quest") == quest
    sm.modify_quest("test_quest", Quest(id="test_quest", title="Modified Quest", description="Modified description"))
    assert sm.get_quest("test_quest").title == "Modified Quest"
    assert sm.get_quest("test_quest").description == "Modified description"
    sm.remove_quest("test_quest")
    assert sm.get_quest("test_quest") is None
    assert len(sm.get_all_quest_ids()) == 1  # assuming initial state has 1 quest
    logging.info("Quest CRUD works")

    # history tests
    sm.append_history("Test event")
    assert len(sm.state.history) > 0
    assert sm.state.history[-1] == "Test event"
    logging.info("History works")

