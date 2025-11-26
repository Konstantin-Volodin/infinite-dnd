"""Character Prompts - System prompt and context for characters."""

def build_character_system_prompt(char) -> str:
    """System prompt for a character agent."""
    prompt = f"You are {char.name}, a {char.race} {char.class_name}. {char.backstory}"
    if char.goal:
        prompt += f"\n\n🎯 GOAL: {char.goal}\nPursue this goal proactively."
    if char.knowledge:
        prompt += f"\nYou know: {', '.join(char.knowledge)}"
    prompt += "\n\nACTIONS: say, examine, attempt_skill, move, attack, pickup, use"
    return prompt


def build_character_context(char, state) -> str:
    """Build context for a character's turn."""
    loc = state.locations.get(char.location_id)
    if not loc:
        return "You're somewhere unfamiliar."
    
    lines = [f"At {loc.name}. {loc.description}"]
    lines.append(f"HP: {char.stats.hp}/{char.stats.max_hp} | Inventory: {char.inventory or 'empty'}")
    
    # Others present
    others = [c.name for c in state.characters.values() 
              if c.location_id == char.location_id and c.id != char.id]
    if others:
        lines.append(f"Present: {', '.join(others)}")
    
    # Location details
    if loc.features:
        lines.append(f"Features: {', '.join(loc.features)}")
    if loc.items:
        lines.append(f"Items: {', '.join(loc.items)}")
    if loc.connections:
        lines.append(f"Exits: {', '.join(loc.connections)}")
    
    # Recent history
    if state.history:
        lines.append("\nRecent:")
        for e in state.history[-4:]:
            lines.append(f"  - {e}")
    
    if char.goal:
        lines.append(f"\n💡 Goal: {char.goal}")
    
    return "\n".join(lines)
