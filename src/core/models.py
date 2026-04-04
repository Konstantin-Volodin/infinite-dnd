"""Data Models - Pydantic models for game state."""

from typing import List, Dict
from enum import Enum
from pydantic import BaseModel, Field


class CharacterType(str, Enum):
    PC = "pc"
    NPC = "npc"


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
    name: str = ""
    type: CharacterType = CharacterType.NPC

    location: str = ""
    role: str = ""  # e.g., "merchant", "guard", "villager"
    stats: CharacterStats = Field(default_factory=CharacterStats)
    backstory: str = ""
    personality: str = ""  # personality traits
    goal: str = ""  # current goal
    inventory: List[str] = []
    knowledge: List[str] = []
    relationships: Dict[str, str] = {}  # ally, enemy, contact, etc.


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
    history: List[str] = []  # Recent events for context
