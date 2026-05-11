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


if __name__ == "__main__":
    import logging

    logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")

    m = Modify(action="update_quest", target_id="q1", status="completed")
    assert m.kind == "modify" and m.action == "update_quest"

    m_step = Modify(action="update_quest", target_id="q1", step="found the map")
    assert m_step.step == "found the map" and m_step.status is None

    for tool in (m, m_step):
        clone = Modify.model_validate_json(tool.model_dump_json())
        assert clone == tool

    logging.info(f"{__file__} tests completed successfully.")
