from src.agents.world_builder.tools import Create


def test_create_location():
    c = Create(type="location", name="Hidden Cellar", description="dusty", location="tavern")
    assert c.kind == "create" and c.type == "location"


def test_create_quest():
    cq = Create(type="quest", name="Find the Map", description="locate the buried chart", owner="alice")
    assert cq.type == "quest" and cq.owner == "alice"


def test_roundtrip_serialization():
    c = Create(type="location", name="Hidden Cellar", description="dusty", location="tavern")
    cq = Create(type="quest", name="Find the Map", description="locate the buried chart", owner="alice")
    for tool in (c, cq):
        clone = Create.model_validate_json(tool.model_dump_json())
        assert clone == tool
