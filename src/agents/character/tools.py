"""Typed tool-call schemas for the character agent.

Each class is the structured payload of one tool the character can call.
The agent emits one per turn; the resolver consumes them and is the only writer.
"""

from typing import Literal, Union

from pydantic import BaseModel


class CharacterToolBase(BaseModel):
    """Shared optional fields every character tool carries — applied deterministically by the resolver."""
    remember: str | None = None  # one concrete fact to store in my own knowledge
    new_goal: str | None = None  # replacement for my own goal, when something changed it


class Speak(CharacterToolBase):
    kind: Literal["speak"] = "speak"
    actor: str
    message: str
    target: str | None = None


class Travel(CharacterToolBase):
    kind: Literal["travel"] = "travel"
    actor: str
    destination: str


class Wait(CharacterToolBase):
    kind: Literal["wait"] = "wait"
    actor: str


class Action(CharacterToolBase):
    kind: Literal["action"] = "action"
    actor: str
    description: str
    target: str | None = None


class Attack(CharacterToolBase):
    kind: Literal["attack"] = "attack"
    actor: str
    target: str


CharacterTool = Union[Speak, Travel, Wait, Action, Attack]
