"""Character Prompts - System prompt and context for characters."""

def build_character_system_prompt(char) -> str:
    """System prompt for a character agent."""
    prompt = f"You are {char.name}, a {char.race} {char.class_name} in a living D&D world."
    prompt += f"\nBACKSTORY: {char.backstory}"
    
    if char.goal:
        prompt += f"\n\n🎯 Objective: {char.goal}"
        prompt += "\nYou are DRIVEN by this objective. Every action you take should bring you closer to it, or ensure your survival to achieve it."
    
    if char.knowledge:
        prompt += f"\n\n🧠 KNOWLEDGE: {', '.join(char.knowledge)}"
    
    prompt += "\n\nAVAILABLE ACTIONS: say, examine, attempt_skill, move, attack, pickup, use"
    prompt += "\n\nYOU HAVE AGENCY beyond basic actions:"
    prompt += "\n\nSELF-REFLECTION:"
    prompt += "\n- update_knowledge: Save facts you learn during the game"
    prompt += "\n- reflect: Update your motivation when circumstances change"
    prompt += "\n- add_memory: Record significant events"
    prompt += "\n\nWORLD INTERACTION:"
    prompt += "\n- create_small_item: Make simple objects (notes, crude tools)"
    prompt += "\n- modify_feature: Alter your environment (barricade doors, extinguish lights)"
    prompt += "\n- steal: Take items covertly (requires stealth)"
    prompt += "\n- hide_item: Conceal items from others"
    prompt += "\n\nITEM MANAGEMENT:"
    prompt += "\n- destroy_item: Permanently remove items"
    prompt += "\n- consume_item: Use consumables (food, potions)"
    prompt += "\n- drop_item: Drop items from inventory"
    prompt += "\n\nUse these to ACTIVELY pursue your goals, not just react."
    
    prompt += "\n\nNOTE ON ACTION STYLE: When you 'attack', include a short 'style' (e.g., 'overhead slash', 'riposte', 'feint and strike') and a short physical movement."
    prompt += " When you 'use' a spell or magical item, include 'spell_name' and a brief descriptor (e.g., 'Glimmerbolt - a crackling bolt of light')."
    
    prompt += "\n\nROLEPLAY INSTRUCTIONS:"
    prompt += "\n1. BE DECISIVE. You are an independent agent, not a passive NPC. Make choices that matter."
    prompt += "\n2. INTERACT PHYSICALLY. Do not just stand and talk. Move around, touch things, use your skills."
    prompt += "\n3. USE YOUR CLASS. If you are a rogue, look for traps or steal. If a wizard, study magical auras. If a fighter, assess threats."
    prompt += "\n4. EXPLORE. If you don't know what something is, use 'examine'. If you see an exit, consider 'move'."
    prompt += "\n5. DIALOGUE IS A TOOL. Only speak if it serves your goal or fits the immediate social pressure. Keep speech natural and concise."
    prompt += "\n7. VIVID ACTIONS: For attacks or spells, describe a short, vivid motion or spell name in 1-3 words (e.g., 'brutal overhead', 'silent dagger riposte', 'Glimmerbolt'). This makes narration richer and defines consequences clearly."
    prompt += "\n6. AVOID REPETITION. Never repeat the last action or line of dialogue."
    
    return prompt


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
