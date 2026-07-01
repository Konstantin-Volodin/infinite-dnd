"""Typed tool-call schema for the quest reviewer agent."""

from typing import Literal

from pydantic import BaseModel


class Modify(BaseModel):
    kind: Literal["modify"] = "modify"
    action: Literal["update_quest", "remove_npc", "update_location"]
    target_id: str
    status: str | None = None
    step: str | None = None
    reason: str | None = None
