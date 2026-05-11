"""
Data Models - Pydantic models for game state.
    - CharacterStats: HP, level, etc.
    - Location: id, description, connections, features, items.
    - Character: id, role, backstory, personality, goal, location, relationships, inventory, knowledge, stats.
    - HistoryEvent: text, location, characters involved.
    - Quest: id, title, description, status, owner, steps.
    - WorldState: time, locations, characters, quests, history.

Each model has in-file tests to ensure correct instantiation and behavior.
"""

from typing import List, Dict
from pydantic import BaseModel, Field


class CharacterStats(BaseModel):
    hp: int = 5
    max_hp: int = 5
    level: int = 1
    xp: int = 0


class Location(BaseModel):
    id: str
    description: str = ""
    connections: List[str] = []
    features: List[str] = []
    items: List[str] = []


class Character(BaseModel):
    id: str
    role: str = "" 
    backstory: str = ""
    personality: str = "" 
    goal: str = ""
    location: str = ""
    relationships: Dict[str, str] = {}
    inventory: List[str] = []
    knowledge: List[str] = []
    stats: CharacterStats = Field(default_factory=CharacterStats)


class HistoryEvent(BaseModel):
    text: str
    location: str
    characters: List[str] = []
    minutes_elapsed: int = 0


class Quest(BaseModel):
    id: str
    title: str
    description: str
    status: str = "active" 
    owner: str = "" 
    steps: List[str] = []


class WorldState(BaseModel):
    time: int = 0
    minutes_elapsed: int = 0
    locations: Dict[str, Location] = {}
    characters: Dict[str, Character] = {}
    quests: Dict[str, Quest] = {}
    history: List[HistoryEvent] = []


if __name__ == "__main__":

    import logging
    logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")

    stats = CharacterStats(hp=20, max_hp=20, level=3)
    assert stats.hp == 20
    assert stats.max_hp == 20
    assert stats.level == 3
    logging.info(f"CharacterStats test passed.")
    logging.info(f"CharacterStats: {stats}")

    loc = Location(id="forest-1", description="dark forest", connections=["village-1"], features=["cabin in the woods"], items=["sword"])
    assert loc.id == "forest-1"
    assert loc.connections == ["village-1"]
    assert loc.features == ["cabin in the woods"]
    assert loc.items == ["sword"]
    logging.info(f"Location test passed.")
    logging.info(f"Location: {loc}")
    
    char = Character(id="hero-1", role="warrior", inventory=["sword", "shield"], goal="slay the dragon", stats=stats)
    assert char.id == "hero-1"
    assert char.role == "warrior"
    assert char.stats.hp == 20
    assert char.inventory == ["sword", "shield"]
    assert char.goal == "slay the dragon"
    logging.info(f"Character test passed.")
    logging.info(f"Character: {char}")
    
    quest = Quest(id="q1", title="Slay Dragon", description="defeat the dragon", owner=char.id)
    assert quest.status == "active"
    assert quest.owner == "hero-1"
    assert quest.description == "defeat the dragon"
    logging.info(f"Quest test passed.")
    logging.info(f"Quest: {quest}")
    
    world = WorldState(
        time=0,
        locations={"forest-1": loc},
        characters={"hero-1": char},
        quests={"q1": quest},
        history=[HistoryEvent(text="Hero enters the forest", location="forest-1", characters=["hero-1"])]
    )
    assert world.time == 0
    assert world.locations == {"forest-1": loc}
    assert world.characters == {"hero-1": char}
    assert world.quests == {"q1": quest}
    assert world.history == [HistoryEvent(text="Hero enters the forest", location="forest-1", characters=["hero-1"])]
    logging.info("WorldState test passed.")
    logging.info(f"WorldState: {world}")
    
    logging.info(f"{__file__} tests completed successfully.")
