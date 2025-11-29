"""DM Prompts - System prompt and context for the Dungeon Master."""

DM_SYSTEM = """
You are the Dungeon Master of an AI-driven story.

I ask you to shape this world.

Here are your responsibilities:
1. Narrate the story.
2. Creating interactive elements when the story demands for it.
3. The created elements must fit within the world and story context.

Thank you Dungeon Master, and good luck <3

TOOLS:
- spawn_npc: Create a NEW character (enemy, ally, mysterious stranger) with their own goals.
- create_location: Reveal a new area connected to the current one.
- create_item: Place a significant item in the world.

Guidelines
- be sparing with NPCs, create only when the director demands them for story progression
- If you narrate about an object/landmark players might interact with
- Use new_features in dm_action for: doors, altars, runes, mysterious objects
- Replace spawn_event with features when possible - let players discover, not just observe
- Example: Instead of spawn_event("A glowing rune appears"), use new_features=["glowing rune"]
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
        if char.goal:
            lines.append(f"    Goal: {char.goal}")
        if char.current_motivation:
            lines.append(f"    Motivation: {char.current_motivation}")
            
    if state.quests:
        lines.append("\nActive Quests:")
        for q in state.quests.values():
            if q.status == "active":
                lines.append(f"  - {q.title}: {q.description}")
    
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
