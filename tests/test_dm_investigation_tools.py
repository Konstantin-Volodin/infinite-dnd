from src.tools import get_dm_tools
from src.agents.dm import DMAgent
from src.core.models import WorldState
from types import SimpleNamespace


def test_get_dm_tools_investigation_subset():
    tool_names = [t['function']['name'] for t in get_dm_tools('investigation')]
    assert 'spawn_npc' not in tool_names
    assert 'narrate' in tool_names


def test_dm_enforces_tool_restrictions_for_investigation(monkeypatch):
    # Build a fake state with investigation scene
    state = SimpleNamespace()
    state.narrative = SimpleNamespace(scene_type='investigation')

    # Create a DMAgent and patch _decide to return a forbidden tool
    dm = DMAgent()

    def fake_decide(system_prompt, context, tools, fallback_tool='narrate', fallback_args=None):
        # Return a forbidden tool call to spawn an NPC
        return {
            'tool': 'spawn_npc',
            'npc_id': 'bad_guy',
            'name': 'Bad Guy',
            'role': 'raider',
            'location_id': 'market-square',
            'description': 'A hostile raider',
        }

    monkeypatch.setattr(dm, '_decide', fake_decide)
    # Call decide_action and ensure the enforcement returns a narrate fallback
    res = dm.decide_action(state, guidance='Describe investigation')
    assert res['tool'] == 'narrate'
