from src.agents.quest_reviewer.agent import QuestUpdate, review_output
from src.agents.quest_reviewer.tools import Modify


def test_review_output():
    # The review_output conversion is pure; exercise it without hitting the LLM.
    updates = [
        QuestUpdate(quest_id="find-brother", new_status="completed"),
        QuestUpdate(quest_id="find-alan", step="discovered he works at the docks"),
        QuestUpdate(quest_id="noise"),  # empty — should be dropped
    ]
    tools = review_output(None, updates)  # type: ignore[arg-type]
    assert len(tools) == 2  # empty update filtered out
    assert all(isinstance(t, Modify) for t in tools)
    assert tools[0].target_id == "find-brother" and tools[0].status == "completed" and tools[0].step is None
    assert tools[1].target_id == "find-alan" and tools[1].status is None and tools[1].step == "discovered he works at the docks"

    assert review_output(None, []) == []  # type: ignore[arg-type]
