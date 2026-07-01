from src.agents.world_builder.agent import NewEntity, enrich_output
from src.agents.world_builder.tools import Create


def test_enrich_output():
    entities = [
        NewEntity(type="npc", name="Dockmaster Alan", description="a shady port official", location="docks", role="dockmaster"),
        NewEntity(type="location", name="The Docks", description="busy port district", location="market-square"),
        NewEntity(type="item", name="", description="nameless item — should be filtered"),
        NewEntity(type="quest", name="Find the Vault", description="locate the cold-hearth vault", owner="alice"),
    ]
    tools = enrich_output(None, entities)  # type: ignore[arg-type]
    assert len(tools) == 3  # empty-name filtered
    assert all(isinstance(t, Create) for t in tools)
    assert tools[0].type == "npc" and tools[0].role == "dockmaster"
    assert tools[1].type == "location" and tools[1].location == "market-square"
    assert tools[2].type == "quest" and tools[2].owner == "alice"

    assert enrich_output(None, []) == []  # type: ignore[arg-type]
