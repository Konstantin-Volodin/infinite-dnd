from src.agents.dm.agent import NewEntity, QuestUpdate, DMResult, dm_output
from src.agents.dm.tools import Create, Modify


def test_dm_output_entities_filtered():
    entities = [
        NewEntity(type="npc", name="Dockmaster Alan", description="a shady port official", location="docks", role="dockmaster"),
        NewEntity(type="location", name="The Docks", description="busy port district", location="market-square"),
        NewEntity(type="item", name="", description="nameless item — should be filtered"),
        NewEntity(type="quest", name="Find the Vault", description="locate the cold-hearth vault", owner="alice"),
    ]
    result = dm_output(None, entities, [], [])  # type: ignore[arg-type]
    assert isinstance(result, DMResult)
    assert len(result.creates) == 3  # empty-name filtered
    assert all(isinstance(t, Create) for t in result.creates)
    assert result.creates[0].type == "npc" and result.creates[0].role == "dockmaster"
    assert result.creates[1].type == "location" and result.creates[1].location == "market-square"
    assert result.creates[2].type == "quest" and result.creates[2].owner == "alice"


def test_dm_output_quest_updates_filtered():
    updates = [
        QuestUpdate(quest_id="find-brother", new_status="completed"),
        QuestUpdate(quest_id="find-alan", step="discovered he works at the docks"),
        QuestUpdate(quest_id="noise"),  # empty — should be dropped
    ]
    result = dm_output(None, [], updates, [])  # type: ignore[arg-type]
    assert len(result.modifies) == 2  # empty update filtered out
    assert all(isinstance(t, Modify) for t in result.modifies)
    assert result.modifies[0].target_id == "find-brother" and result.modifies[0].status == "completed" and result.modifies[0].step is None
    assert result.modifies[1].target_id == "find-alan" and result.modifies[1].status is None and result.modifies[1].step == "discovered he works at the docks"


def test_dm_output_minutes_clamped():
    result = dm_output(None, [], [], [0, 1, 30, 9999, -5])  # type: ignore[arg-type]
    assert result.minutes == [0, 1, 30, 1440, 0]


def test_dm_output_all_empty():
    result = dm_output(None, [], [], [])  # type: ignore[arg-type]
    assert result == DMResult(creates=[], modifies=[], minutes=[])
