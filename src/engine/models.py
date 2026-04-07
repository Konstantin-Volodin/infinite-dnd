# src/core/models.py
"""Data Models - Pydantic models for game state."""

from typing import List, Dict
from pydantic import BaseModel, Field


class CharacterStats(BaseModel):
    hp: int = 5
    max_hp: int = 5
    level: int = 1


class Location(BaseModel):
    id: str
    name: str = ""
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


class Quest(BaseModel):
    id: str
    title: str
    description: str
    status: str = "active"  # active, completed, failed
    owner: str = ""  # Character who owns/is assigned this quest
    steps: List[str] = [] # description for dm to track progress


class WorldState(BaseModel):
    time: int = 0
    locations: Dict[str, Location] = {}
    characters: Dict[str, Character] = {}
    quests: Dict[str, Quest] = {}
    history: List[HistoryEvent] = []
