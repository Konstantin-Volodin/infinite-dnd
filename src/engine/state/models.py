"""
Data Models - Pydantic models for game state.
    - CharacterStats: HP, level, etc.
    - Location: id, description, connections, features, items.
    - Character: id, role, backstory, personality, goal, location, relationships, inventory, knowledge, stats.
    - HistoryEvent: text, location, characters involved.
    - Quest: id, title, description, status, owner, plan, current_step, steps.
    - WorldState: time, locations, characters, quests, history.

See tests/engine/state/test_models.py for coverage.
"""

from typing import Dict, List

from pydantic import BaseModel, Field, model_validator


class CharacterStats(BaseModel):
    hp: int = Field(default=5, ge=0)
    max_hp: int = Field(default=5, ge=0)
    level: int = Field(default=1, ge=1)
    xp: int = Field(default=0, ge=0)
    gold: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def hp_does_not_exceed_maximum(self) -> "CharacterStats":
        if self.hp > self.max_hp:
            raise ValueError("hp cannot exceed max_hp")
        return self


class Location(BaseModel):
    id: str
    description: str = ""
    connections: List[str] = Field(default_factory=list)
    features: List[str] = Field(default_factory=list)
    items: List[str] = Field(default_factory=list)


class Character(BaseModel):
    id: str
    role: str = "" 
    backstory: str = ""
    personality: str = "" 
    goal: str = ""
    location: str = ""
    relationships: Dict[str, str] = Field(default_factory=dict)
    inventory: List[str] = Field(default_factory=list)
    knowledge: List[str] = Field(default_factory=list)
    stats: CharacterStats = Field(default_factory=CharacterStats)


class HistoryEvent(BaseModel):
    text: str
    location: str
    characters: List[str] = Field(default_factory=list)
    minutes_elapsed: int = Field(default=0, ge=0)


class Quest(BaseModel):
    id: str
    title: str
    description: str
    status: str = "active"
    owner: str = ""
    plan: List[str] = Field(default_factory=list)  # ordered, concrete objectives set at creation
    current_step: int = Field(default=0, ge=0)  # index into plan of the current objective
    steps: List[str] = Field(default_factory=list)  # progress log — accomplished objectives + notes


class WorldState(BaseModel):
    time: int = Field(default=0, ge=0)
    minutes_elapsed: int = Field(default=0, ge=0)
    last_quest_advance_time: int = Field(default=0, ge=0)  # tick of the most recent quest advancement — stall detection
    director_interventions: Dict[str, int] = Field(default_factory=dict)  # quest id (or "world") → director beat count
    locations: Dict[str, Location] = Field(default_factory=dict)
    characters: Dict[str, Character] = Field(default_factory=dict)
    quests: Dict[str, Quest] = Field(default_factory=dict)
    history: List[HistoryEvent] = Field(default_factory=list)
