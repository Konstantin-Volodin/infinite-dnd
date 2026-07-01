from src.agents.quest_reviewer.tools import Modify


def test_update_quest_status():
    m = Modify(action="update_quest", target_id="q1", status="completed")
    assert m.kind == "modify" and m.action == "update_quest"


def test_update_quest_step():
    m_step = Modify(action="update_quest", target_id="q1", step="found the map")
    assert m_step.step == "found the map" and m_step.status is None


def test_roundtrip_serialization():
    m = Modify(action="update_quest", target_id="q1", status="completed")
    m_step = Modify(action="update_quest", target_id="q1", step="found the map")
    for tool in (m, m_step):
        clone = Modify.model_validate_json(tool.model_dump_json())
        assert clone == tool
