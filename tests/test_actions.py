from src.core.models import WorldState
from src.engine.actions import ActionExecutor


def test_create_location_stores_name():
    state = WorldState()

    saved = {"called": False}

    def save_state():
        saved["called"] = True

    ae = ActionExecutor(state=state, save_state=save_state, save_history=lambda *_: None)

    res = ae.create_location(location="Valley Bridge", name="Valley Bridge", description="A nice bridge.")
    assert res["status"] == "success"
    loc = state.locations.get("valley-bridge")
    assert loc is not None
    assert loc.name == "Valley Bridge"
    assert saved["called"]
