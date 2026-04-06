# src/tools/character/tools.py
"""Character tools."""

from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, ConfigDict

class ActParams(BaseModel):
    model_config = ConfigDict(extra="forbid")
    description: str
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
        "name": "perform_action",
        "description": "describe what you want to do and how you want to do it. can target person, item, or feature. be specific and detailed.",
        "strict": True,
        "parameters": ActParams.model_json_schema(),
    },
    {
        "type": "function",
        "name": "speak",
        "description": "say something. can be targeted (dialogue) or thinking out loud.",
        "parameters": SpeakParams.model_json_schema(),
        "strict": True,
    },
    {
        "type": "function",
        "name": "travel",
        "description": "travel to a connected location.",
        "parameters": MoveParams.model_json_schema(),
        "strict": True,
    },
]