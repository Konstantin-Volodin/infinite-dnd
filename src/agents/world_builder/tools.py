"""Typed tool-call schema for the world builder agent."""

from typing import Literal

from pydantic import BaseModel


class Create(BaseModel):
    kind: Literal["create"] = "create"
    type: Literal["location", "item", "npc", "quest"]
    name: str
    description: str = ""
    location: str | None = None
    role: str | None = None
    goal: str | None = None
    owner: str | None = None
