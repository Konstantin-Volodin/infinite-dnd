"""Data Models - Pydantic models for game state."""

from typing import List, Dict
from enum import Enum
from pydantic import BaseModel, Field


class CharacterType(str, Enum):
    PC = "pc"
    NPC = "npc"


class Attributes(BaseModel):
    strength: int = 10
    dexterity: int = 10
    constitution: int = 10
    intelligence: int = 10
    wisdom: int = 10
    charisma: int = 10


class CharacterStats(BaseModel):
    hp: int = 5
    max_hp: int = 5
    level: int = 1
    # attributes: Attributes = Field(default_factory=Attributes)


class Location(BaseModel):
    id: str
    description: str = ""
    connections: List[str] = []
    features: List[str] = []
    items: List[str] = []



class Memory(BaseModel):
    content: str
    importance: str = "medium"
    turn: int = 0


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
    memory: List[Memory] = []  # memories for characters to recall



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
    story_beats: List[str] = []  # Completed narrative beats (e.g., "ronn_reveals_cellar")
    inspected_features: List[str] = []  # track inspected elemnts 
