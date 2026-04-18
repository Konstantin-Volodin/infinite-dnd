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


if __name__ == "__main__":
    import logging

    logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")

    c = Create(type="location", name="Hidden Cellar", description="dusty", location="tavern")
    assert c.kind == "create" and c.type == "location"

    cq = Create(type="quest", name="Find the Map", description="locate the buried chart", owner="alice")
    assert cq.type == "quest" and cq.owner == "alice"

    for tool in (c, cq):
        clone = Create.model_validate_json(tool.model_dump_json())
        assert clone == tool

    logging.info(f"{__file__} tests completed successfully.")
