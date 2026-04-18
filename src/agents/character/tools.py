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


if __name__ == "__main__":
    import logging

    logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")

    s = Speak(actor="alice", message="hi", target="bob")
    assert s.kind == "speak" and s.actor == "alice" and s.target == "bob"

    t = Travel(actor="alice", destination="forest")
    assert t.kind == "travel" and t.destination == "forest"

    w = Wait(actor="alice")
    assert w.kind == "wait"

    a = Action(actor="alice", description="pick the lock")
    assert a.kind == "action" and a.target is None

    for tool in (s, t, w, a):
        clone = type(tool).model_validate_json(tool.model_dump_json())
        assert clone == tool

    logging.info(f"{__file__} tests completed successfully.")
