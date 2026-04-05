# src/tools/character/tools.py
"""Character tools."""

from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, ConfigDict

class ActParams(BaseModel):
    model_config = ConfigDict(extra="forbid")
    description: str
    skill: Optional[str] = None
    target: Optional[str] = None

class SpeakParams(BaseModel):
    model_config = ConfigDict(extra="forbid")
    message: str
    target: Optional[str] = None

class MoveParams(BaseModel):
    model_config = ConfigDict(extra="forbid")
    location: str

CHARACTER_TOOLS = [
    {
        "type": "function",
        "name": "act",
        "description": "Do something physical: attack, examine, pick up, use an item, cast a spell, sneak, climb — anything that isn't talking or traveling.",
        "parameters": ActParams.model_json_schema(),
        "strict": True,
    },
    {
        "type": "function",
        "name": "speak",
        "description": "Say something out loud. Include emotion and body language in your message.",
        "parameters": SpeakParams.model_json_schema(),
        "strict": True,
    },
    {
        "type": "function",
        "name": "move",
        "description": "Travel to a connected location. Must be a valid exit from your current location.",
        "parameters": MoveParams.model_json_schema(),
        "strict": True,
    },
]