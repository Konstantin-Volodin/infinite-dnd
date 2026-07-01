"""
Data Models - Pydantic models for game state.
    - CharacterStats: HP, level, etc.
    - Location: id, description, connections, features, items.
    - Character: id, role, backstory, personality, goal, location, relationships, inventory, knowledge, stats.
    - HistoryEvent: text, location, characters involved.
    - Quest: id, title, description, status, owner, steps.
    - WorldState: time, locations, characters, quests, history.

See tests/engine/state/test_models.py for coverage.
"""

from typing import List, Dict
from pydantic import BaseModel, Field


class CharacterStats(BaseModel):
    hp: int = 5
    max_hp: int = 5
    level: int = 1
    xp: int = 0
    gold: int = 0


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
