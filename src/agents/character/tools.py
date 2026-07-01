"""Typed tool-call schemas for the character agent.

Each class is the structured payload of one tool the character can call.
The agent emits one per turn; the resolver consumes them and is the only writer.
"""

from typing import Literal, Union

from pydantic import BaseModel


class Speak(BaseModel):
    kind: Literal["speak"] = "speak"
    actor: str
    message: str
    target: str | None = None


class Travel(BaseModel):
    kind: Literal["travel"] = "travel"
    actor: str
    destination: str


class Wait(BaseModel):
    kind: Literal["wait"] = "wait"
    actor: str


class Action(BaseModel):
    kind: Literal["action"] = "action"
    actor: str
    description: str
    target: str | None = None


CharacterTool = Union[Speak, Travel, Wait, Action]
