"""Character Prompts - System prompt and context for characters."""



def build_character_system_prompt(char) -> str:
    CHARACTER_PROMPT = f"""
    Good luck in your adventures {char.id} <3
    
    I am a {char.name}, a {char.race} {char.class_name} in an AI-driven story.

    🎯 I am DRIVEN by this objective: {char.goal} 

    🧠 Here is what I know:
    {', '.join(char.knowledge)}

    🛠️ What I can do: 
    - skill_check: describe what you want to do given the context.
    - perform some dialogue
    - travel to a connected location
    - engage in combat

    🙏 I have agency beyond basic actions. 
    - I can update my state: (goals, emotions, knowledge)
    - I can request help from the Engineer

    🚀 I will actively pursue my goals using the actions available to me.

    ROLEPLAY INSTRUCTIONS:
    - BE DECISIVE. You are an independent agent, not a passive NPC. Make choices that matter.
    - DIALOGUE IS A TOOL. Speak if it serves your goal or fits the immediate social pressure. Keep speech natural.
    - AVOID REPETITION. Never repeat the last action or line of dialogue.
    - VIVID ACTIONS: For attacks or spells, describe a short, vivid motion or spell name.
"""
    
    return CHARACTER_PROMPT


def build_character_context(char, state) -> str:
    """Build context for a character's turn."""
    loc = state.locations.get(char.location_id)
    if not loc:
        return "You're somewhere unfamiliar."
    
    lines = [f"At {loc.name}. {loc.description}"]
    # Health display
    try:
        from ..core.rules import get_health_status
        status = get_health_status(char)
    except Exception:
        status = "unknown"
    lines.append(f"HP: {char.stats.hp}/{char.stats.max_hp} ({status}) | Inventory: {char.inventory or 'empty'}")
    
    # Others present (include role and a short status)
    others_list = []
    for c in state.characters.values():
        if c.location_id == char.location_id and c.id != char.id:
            others_list.append(f"{c.name} ({c.class_name or c.type})")
    if others_list:
        lines.append(f"Present: {', '.join(others_list)}")
        # Make explicit who can be targeted with 'say' or 'attack'
        present_names = [c.name for c in state.characters.values() if c.location_id == char.location_id and c.id != char.id]
        if present_names:
            lines.append(f"Allowed say targets: {', '.join(present_names)}")
    
    # Location details and actionable targets
    examine_targets = []
    if loc.features:
        lines.append(f"Features: {', '.join(loc.features)}")
        examine_targets.extend(loc.features)
    if loc.items:
        lines.append(f"Items: {', '.join(loc.items)}")
        examine_targets.extend(loc.items)
    if loc.connections:
        lines.append(f"Exits: {', '.join(loc.connections)}")

    if examine_targets:
        lines.append(f"\n[INTERACTABLES] You can 'examine' or 'pickup' these specifically: {', '.join(examine_targets)}")
        lines.append("Do NOT examine things not in this list, even if mentioned in narration.")
    # Feature vs location guidance
    lines.append("\nNote: Features (stalls, fountains) are part of the location. Use 'examine' to interact with them. Use 'move' to go to an Exit (a different location).")
    
    # Recent history
    if state.history:
        lines.append("\nRecent:")
        for e in state.history[-4:]:
            lines.append(f"  - {e}")
    
    
    if char.goal:
        lines.append(f"\n💡 Goal: {char.goal}")
    
    # Show current motivation if it exists
    if getattr(char, 'current_motivation', None):
        lines.append(f"🎯 Current Motivation: {char.current_motivation}")

    # Knowledge the character holds (helps NPCs mention relevant facts)
    if getattr(char, 'knowledge', None):
        lines.append(f"\n🧠 Knowledge: {', '.join(char.knowledge)}")
    
    # Check for repetition
    if state.history and state.history[-1].startswith(f"{char.name}:"):
        lines.append("\n⚠️ You just spoke. Do NOT speak again immediately. Take an action.")
    
    # Check for dialogue fatigue
    recent_history = state.history[-5:] if state.history else []
    dialogue_count = sum(1 for e in recent_history if '"' in e or "says" in e.lower())
    if dialogue_count >= 3:
        lines.append("\n⚠️ NOTICE: There has been a lot of dialogue recently. Consider taking a physical action (move, examine, use, attack) to keep things dynamic.")

    return "\n".join(lines)
