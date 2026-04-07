from src.engine.state import WorldState, Character, Location, CharacterStats, Quest


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

    # ============ HISTORY ============
    def append_history(self, event: str) -> None:
        self.state.history.append(event)

    def get_history(self) -> list[str]:
        return self.state.history

    def get_history_slice(self, start: int = 0, end: int | None = None) -> list[str]:
        return self.state.history[start:end]


if __name__ == "__main__":
    import logging
    from src.engine.state import StateLoader

    manager = StateLoader()
    state = manager.load_state()
    sm = StateManager(state)
    logging.basicConfig(level=logging.DEBUG, format="%(asctime)s [%(levelname)s] %(message)s")

    # location tests
    loc = Location(id="test_loc", name="Test Location")
    sm.add_location(loc)
    assert sm.get_location("test_loc") == loc
    print("✓ Location CRUD works")

    # character tests
    char = Character(id="test_char", name="Test Character", stats=CharacterStats())
    sm.add_character(char)
    assert sm.get_character("test_char") == char
    print("✓ Character CRUD works")

    # quest tests
    quest = Quest(id="test_quest", title="Test Quest")
    sm.add_quest(quest)
    assert sm.get_quest("test_quest") == quest
    print("✓ Quest CRUD works")

    # history tests
    sm.append_history("Test event")
    assert len(sm.get_history()) > 0
    assert sm.get_history()[-1] == "Test event"
    print("✓ History works")

