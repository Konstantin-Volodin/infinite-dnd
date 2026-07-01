from src.agents.character.tools import Action, Speak, Travel, Wait


def test_speak():
    s = Speak(actor="alice", message="hi", target="bob")
    assert s.kind == "speak" and s.actor == "alice" and s.target == "bob"


def test_travel():
    t = Travel(actor="alice", destination="forest")
    assert t.kind == "travel" and t.destination == "forest"


def test_wait():
    w = Wait(actor="alice")
    assert w.kind == "wait"


def test_action():
    a = Action(actor="alice", description="pick the lock")
    assert a.kind == "action" and a.target is None


def test_roundtrip_serialization():
    s = Speak(actor="alice", message="hi", target="bob")
    t = Travel(actor="alice", destination="forest")
    w = Wait(actor="alice")
    a = Action(actor="alice", description="pick the lock")
    for tool in (s, t, w, a):
        clone = type(tool).model_validate_json(tool.model_dump_json())
        assert clone == tool
