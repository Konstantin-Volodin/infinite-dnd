"""Data Models - Pydantic models for game state."""
from typing import List, Dict, Optional
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
    hp: int = 10
    max_hp: int = 10
    ac: int = 10
    level: int = 1
    attributes: Attributes = Field(default_factory=Attributes)


class Location(BaseModel):
    id: str
    name: str
    description: str = ""
    connections: List[str] = []
    items: List[str] = []
    features: List[str] = []
    environmental_effects: List[str] = []


class Character(BaseModel):
    id: str
    name: str
    type: CharacterType = CharacterType.NPC
    race: str = "Human"
    class_name: str = ""
    backstory: str = ""
    goal: str = ""
    knowledge: List[str] = []
    stats: CharacterStats = Field(default_factory=CharacterStats)
    location_id: str = ""
    inventory: List[str] = []


class NarrativeState(BaseModel):
    scene_type: str = "exploration"  # exploration, social, combat
    tension: str = "low"             # low, rising, high
    stall_counter: int = 0


class WorldState(BaseModel):
    time: int = 0
    narrative: NarrativeState = Field(default_factory=NarrativeState)
    locations: Dict[str, Location] = {}
    characters: Dict[str, Character] = {}
    history: List[str] = []
