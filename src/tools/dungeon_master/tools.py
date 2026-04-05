# src/tools/dungeon_master/tools.py
"""Dungeon Master tools."""

from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, ConfigDict

class NarrateParams(BaseModel):
    model_config = ConfigDict(extra="forbid")
    content: str
    prompts_character: Optional[str] = None

class CreateParams(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: str  # "location" | "item" | "npc"
    name: str
    description: str
    id: Optional[str] = None
    location: Optional[str] = None
    role: Optional[str] = None
    goal: Optional[str] = None

class ModifyParams(BaseModel):
    model_config = ConfigDict(extra="forbid")
    action: str  # "update_quest" | "remove_npc" | "update_location"
    target_id: str
    status: Optional[str] = None
    reason: Optional[str] = None

DM_TOOLS = [
    {
        "type": "function",
        "name": "narrate",
        "description": "Describe what happens in the world. Never write dialogue or thoughts for characters — they speak for themselves.",
        "parameters": NarrateParams.model_json_schema(),
        "strict": True,
    },
    {
        "type": "function",
        "name": "create",
        "description": "Add a location, item, or NPC to the world.",
        "parameters": CreateParams.model_json_schema(),
        "strict": True,
    },
    {
        "type": "function",
        "name": "modify",
        "description": "Change or remove something: update a quest, remove an NPC, update a location.",
        "parameters": ModifyParams.model_json_schema(),
        "strict": True,
    },
]