"""Data Models - Pydantic models for game state."""
from typing import List, Dict, Optional, Union
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
    # Optional traits map for features to define mechanics without hardcoding
    feature_traits: Dict[str, Dict] = Field(default_factory=dict)
    environmental_effects: List[str] = []


class Memory(BaseModel):
    content: str
    importance: str = "medium"
    turn: int = 0


class Character(BaseModel):
    id: str
    name: str
    type: CharacterType = CharacterType.NPC
    race: str = "Human"
    class_name: str = ""
    backstory: str = ""
    goal: str = ""  # Primary/static goal
    current_motivation: str = ""  # Dynamic motivation that can change
    knowledge: List[str] = []
    memory: List[Memory] = []  # Structured memories with context
    examined_items: List[str] = []  # Track what has been examined to prevent loops
    short_term_goals: List[str] = []  # Temporary objectives
    stats: CharacterStats = Field(default_factory=CharacterStats)
    location_id: str = ""
    inventory: List[str] = []
    
    # Backwards compatibility alias for description
    @property
    def description(self) -> str:
        """Alias for 'backstory' to support existing prompts that use 'description'."""
        return self.backstory


class NarrativeState(BaseModel):
    scene_type: str = "exploration"  # exploration, social, combat
    tension: str = "low"             # low, rising, high
    stall_counter: int = 0
    combat_turn_order: List[str] = [] # List of character IDs in initiative order
    current_turn_index: int = 0       # Index in combat_turn_order


class Quest(BaseModel):
    id: str
    title: str
    description: str
    status: str = "active"  # active, completed, failed
    giver_id: str = ""
    steps: List[str] = []
    
    # Backwards compatibility aliases
    @property
    def name(self) -> str:
        """Alias for 'title' for backwards compatibility."""
        return self.title


class WorldState(BaseModel):
    time: int = 0
    narrative: NarrativeState = Field(default_factory=NarrativeState)
    locations: Dict[str, Location] = {}
    characters: Dict[str, Character] = {}
    quests: Dict[str, Quest] = {}
    history: List[str] = []
    inspected_features: List[str] = [] # Track inspected features globally (location_id:feature_key)
