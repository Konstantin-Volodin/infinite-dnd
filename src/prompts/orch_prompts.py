"""Orchestrator Prompts - Controls game flow and turn order."""

ORCHESTRATOR_SYSTEM = """You control the flow of a D&D session.

YOUR JOB:
1. Decide who acts next (character ID or "dm")
2. Detect scene changes (exploration → combat, etc.)
3. If stall_counter >= 3, select DM to inject a complication

TOOLS:
- select_next_actor: Pick who goes next
- update_narrative: Change scene_type or tension

RULES:
- Combat: alternate between opposing sides
- Dialogue: let conversations flow naturally
- Stalled: select DM to create drama
"""


def build_orchestrator_system_prompt() -> str:
    return ORCHESTRATOR_SYSTEM


def build_orchestrator_context(state) -> str:
    """Build context for the orchestrator."""
    lines = [f"SCENE: {state.narrative.scene_type} | TENSION: {state.narrative.tension}"]
    
    # Stall alert
    if state.narrative.stall_counter >= 3:
        lines.append(f"⚠️ STALL ALERT: {state.narrative.stall_counter} turns! Select DM to inject drama!")
    
    # Actors
    actors = ["dm"] + list(state.characters.keys())
    lines.append(f"Actors: {', '.join(actors)}")
    
    # Character locations
    for char in state.characters.values():
        loc = state.locations.get(char.location_id)
        loc_name = loc.name if loc else "unknown"
        lines.append(f"  {char.name} ({char.id}) at {loc_name}")
    
    # Recent history
    if state.history:
        lines.append("\nRecent:")
        for event in state.history[-5:]:
            lines.append(f"  - {event}")
    
    return "\n".join(lines)
