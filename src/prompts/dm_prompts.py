"""DM Prompts - System prompt and context for the Dungeon Master."""

DM_SYSTEM = """
You are the Dungeon Master of an AI-driven story.

I ask you to shape this world.

Here are your responsibilities:
1. Narrate the story vividly.
2. Shape the world by creating new interactive elements.
3. Drive the plot forward based on logical consequences, not just suggestions.

Thank you Dungeon Master, and good luck <3

As the game unfolds, please keep these questions in mind:
    - try to reason about the progress of the game, are your decisions impacting a story in any way?
    - what might be missing to make the story more engaging?

    # Narration tip: be specific. When you describe combat or magical actions, include distinct movements, attack styles, and spell names (short phrases) so the scene is vivid and impactful.

TOOLS:
- spawn_npc: Create a NEW character (enemy, ally, mysterious stranger) with their own goals.
- create_location: Reveal a new area connected to the current one.
- create_item: Place a significant item in the world.do 
"""


def build_dm_system_prompt() -> str:
    return DM_SYSTEM


def build_dm_context(state) -> str:
    """Build context for the DM's turn."""
    lines = [f"Turn {state.time}"]
    
    lines.append("\nCharacters:")
    for char in state.characters.values():
        loc = state.locations.get(char.location_id)
        # Include health status
        try:
            from ..core.rules import get_health_status
            hs = get_health_status(char)
        except Exception:
            hs = "unknown"
        lines.append(f"  {char.name} at {loc.name if loc else 'unknown'} | HP: {char.stats.hp}/{char.stats.max_hp} ({hs})")
    
    lines.append("\nLocations: " + ", ".join(l.id for l in state.locations.values()))
    # Provide details per location so DM has a sense of what's in each place
    for lid, loc in state.locations.items():
        lines.append(f"\nLocation '{loc.name}' ({lid}):")
        if loc.features:
            lines.append(f"  Features: {', '.join(loc.features)}")
        if loc.items:
            lines.append(f"  Items: {', '.join(loc.items)}")
        # Characters here
        present = [c.name for c in state.characters.values() if c.location_id == lid]
        if present:
            lines.append(f"  Present: {', '.join(present)}")
    
    if state.history:
        lines.append("\nRecent:")
        for e in state.history[-6:]:
            lines.append(f"  - {e}")
    
    return "\n".join(lines)
