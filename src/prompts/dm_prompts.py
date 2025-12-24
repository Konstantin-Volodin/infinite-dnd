"""DM Prompts - System prompt and context for the Dungeon Master."""

DM_SYSTEM = """
You are the Engineer of an AI-driven story.

I ask you to breath life into this world as the story unfolds.

Here are your responsibilities:
1. Create the world and its elements.
2. The created elements must fit within the world and story context.
3. Advance the story by creating quest-relevant NPCs and events.

Thank you Engineer, and good luck <3

TOOLS:
- spawn_npc: Create a NEW character (enemy, ally, mysterious stranger) with their own goals.
- create_location: Reveal a new area connected to the current one.
- create_item: Place a significant item in the world.

QUEST ADVANCEMENT - CRITICAL:
- When characters reach quest-relevant locations, SPAWN the NPCs or items they're looking for
- Example: If a character is searching for their brother and reaches the rescue location, SPAWN the brother or rescue crew
- Don't just narrate "you don't find them" - CREATE them so the quest can progress
- Failed skill checks should create COMPLICATIONS, not dead-ends (e.g., "caught by guard who might talk")

Guidelines:
- be sparing with NPCs, create only when the director demands them for story progression OR when advancing active quests
- If you narrate about an object/landmark players might interact with
- Use new_features in dm_action for: doors, altars, runes, mysterious objects
- Replace spawn_event with features when possible - let players discover, not just observe
- Example: Instead of spawn_event("A glowing rune appears"), use new_features=["glowing rune"]
"""


def build_dm_system_prompt() -> str:
    return DM_SYSTEM


def build_dm_context(state) -> str:
    """Build context for the DM's turn."""
    # Use getattr defaults in case test harness provides a simplified state object
    lines = [f"Turn {getattr(state, 'time', 0)}"]
    
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
        lines.append("\n=== ACTIVE QUESTS ===")
        for q in state.quests.values():
            if q.status == "active":
                lines.append(f"  📜 {q.title}: {q.description}")
                if hasattr(q, 'objectives'):
                    lines.append(f"     Objectives: {q.objectives}")
        
        # QUEST ADVANCEMENT OPPORTUNITIES
        lines.append("\n🎯 QUEST ADVANCEMENT OPPORTUNITIES:")
        quest_opportunities = []
        for char in state.characters.values():
            for q in state.quests.values():
                if q.status == "active":
                    # Check if character's goal or location relates to quest
                    char_loc = state.locations.get(char.location_id)
                    loc_name = char_loc.name.lower() if char_loc else ""
                    quest_keywords = q.title.lower().split() + q.description.lower().split()
                    
                    # If character is at a location mentioned in quest or their goal matches quest
                    if any(keyword in loc_name for keyword in quest_keywords if len(keyword) > 4):
                        quest_opportunities.append(
                            f"  ⚡ {char.name} is at {char_loc.name} - relevant to '{q.title}'. "
                            f"Consider spawning quest-critical NPCs or items here!"
                        )
                    elif char.goal and any(keyword in char.goal.lower() for keyword in quest_keywords if len(keyword) > 4):
                        quest_opportunities.append(
                            f"  ⚡ {char.name}'s goal ('{char.goal}') relates to '{q.title}'. "
                            f"Create NPCs or events to advance this quest!"
                        )
        
        if quest_opportunities:
            lines.extend(quest_opportunities)
        else:
            lines.append("  (No immediate quest advancement opportunities detected)")
    
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
