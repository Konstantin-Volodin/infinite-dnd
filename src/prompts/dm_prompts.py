"""DM Prompts - System prompt and context for the Dungeon Master."""

DM_SYSTEM = """You are the Dungeon Master. Move the story forward and create memorable moments.

PRINCIPLES:
- Make things happen, don't just describe
- Use NPCs to create dynamics
- Force decisions with consequences
- If you see [SYSTEM] skill check, narrate outcome based on the roll

Keep narration brief (1-2 sentences). Present tense."""


def build_dm_system_prompt() -> str:
    return DM_SYSTEM


def build_dm_context(state) -> str:
    """Build context for the DM's turn."""
    lines = [f"Turn {state.time}"]
    
    lines.append("\nCharacters:")
    for char in state.characters.values():
        loc = state.locations.get(char.location_id)
        lines.append(f"  {char.name} at {loc.name if loc else 'unknown'}")
    
    lines.append("\nLocations: " + ", ".join(l.id for l in state.locations.values()))
    
    if state.history:
        lines.append("\nRecent:")
        for e in state.history[-6:]:
            lines.append(f"  - {e}")
    
    return "\n".join(lines)
