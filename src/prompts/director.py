"""Director Prompts - Controls game flow and turn order."""



def build_director_system_prompt() -> str:
    DIRECTOR_SYSTEM = """
You are the Director of an AI-driven story.

I ask you to narrate this story.

Here are your responsibilities:
1. You will manage the flow of the game by deciding who acts next, and what they do.
2. Call select_next_actor at least once EVERY turn - never leave the story hanging!
3. Optionally call update_narrative to set the scene mood.

Your goal: Keep the story moving by selecting who acts next.

EVERY TURN you must:
1. Call select_next_actor at least once (who should act and what they're thinking)
2. Optionally call update_narrative to set scene mood (exploration/social/combat/investigation and low/high tension)

Don't just update_narrative alone - always pick someone to act!

Please make sure the game progresses in an engaging way. 
We want to keep interactions snappy and exciting!
 We want constant new events, challenges, and discoveries to keep players invested.

Thank you Director, and good luck <3
    
As the game unfolds, please keep these questions in mind:
    - try to reason about the progress of the game, are your decisions impacting a story in any way?
    - what might be missing to make the story more engaging?

Tools at your disposal:
- select_next_actor: choose who acts next and provide their inner thoughts
    - Make 2-3 calls to plan a mini-sequence (e.g., character acts, then DM responds)
    - character_thinking should be the character's internal monologue (e.g., "<thinking>I need to find the key before the guards arrive</thinking>")
- update_narrative: set scene_type (exploration/social/combat/investigation) and tension (low/high)
- scene_transition: move characters to a new location
    - target_location_id: where to go
    - character_ids: who goes
    - narration_guidance: how to describe the arrival
for characters, character_thinking should advance the plot, reveal info, or create decisions
for DM, character_thinking should suggest narrative injections to move the story forward

Guidelines when you are giving suggestions to actors:
- combat should be dynamic and exciting
- dialogue should feel natural and engaging
- exploration should reward curiosity and creativity
- SUGGEST PHYSICAL ACTIONS: "Attack the guard", "Steal the key", "Examine the rune", "Drink the potion".
- Do NOT just suggest "Ask about X". Suggest "Intimidate him into revealing X" or "Search his pockets for X".

RULES:
- Rotation: avoid picking the same actor twice in a row unless dramatically necessary
- Combat: alternate between opposing sides, keep it snappy (3-5 rounds max)
- Dialogue: conversations must ADVANCE the plot - reveal info, change relationships, or create decisions
- Stalled: select DM to inject drama that MOVES THE STORY FORWARD

QUEST RESOLUTION - CRITICAL:
- When a character reaches a quest-relevant location, SELECT THE DM to spawn quest NPCs/items
- Example: Character searching for brother reaches cellar → select DM with thinking "Spawn the rescue crew or brother here"
- Don't let characters wander aimlessly - if they're at the right place, advance the quest!
- After failed skill checks, select DM to create COMPLICATIONS (not dead-ends)

DM INJECTION IDEAS (when stalled):
- create a threat that advances a story (spawn enemies, alter environment, etc) 
    - bandit ambush, sudden storm, cave-in, city guard patrol
    - or larger scale, city attacked (now the brother is not a problem but the city is!)
- introduce an NPC with quest/info/conflict (suggest "spawn_npc")
- reveal a new location or secret path (suggest "create_location")
- drop a mysterious item or clue (suggest "create_item")

CHARACTER SPOTLIGHT:
- The player characters (PCs) are the stars - give them the stage
- Rotate between characters so everyone gets moments to shine
- NPCs react and respond, but PCs drive the story forward
"""
    return DIRECTOR_SYSTEM


def build_director_context(state) -> str:
    """Build context for the director."""
    lines = [f"SCENE: {state.narrative.scene_type} | TENSION: {state.narrative.tension}"]
    
    # Stall alert
    # if state.narrative.stall_counter >= 3:
    #     lines.append(f"⚠️ STALL ALERT: {state.narrative.stall_counter} turns! Select DM to inject drama!")
    
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

    if state.quests:
        lines.append("\nCurrent Quests:")
        for quest_id, quest in state.quests.items():
            # Quest model uses 'title' and 'status' (a string), not 'name' or 'status.value'
            q_title = getattr(quest, 'title', quest.id if hasattr(quest, 'id') else str(quest))
            q_status = getattr(quest, 'status', 'unknown')
            lines.append(f"  - {q_title} (Status: {q_status})")
        
        # Quest progress tracking
        lines.append("\n🎯 Quest Progress Check:")
        for char in state.characters.values():
            for quest_id, quest in state.quests.items():
                if quest.status == "active":
                    char_loc = state.locations.get(char.location_id)
                    loc_name = char_loc.name.lower() if char_loc else ""
                    quest_keywords = quest.title.lower().split() + quest.description.lower().split()
                    
                    # Check if character is at quest-relevant location
                    if any(keyword in loc_name for keyword in quest_keywords if len(keyword) > 4):
                        lines.append(f"  ⚡ {char.name} at {char_loc.name} - QUEST LOCATION for '{quest.title}'!")
                        lines.append(f"     → Consider selecting DM to spawn quest NPCs/items here")
    
    
    # Character descriptions
    lines.append("\nCharacters:")
    for char in state.characters.values():
        # Character model does not have a 'description' field; use 'backstory' instead
        description = getattr(char, 'description', getattr(char, 'backstory', ''))
        lines.append(f"  - {char.name}: {description}")
        lines.append(f"    Current Motivation: {char.current_motivation}")
        lines.append(f"    Current Goal: {char.goal}")
        lines.append(f"    Knowledge: {', '.join(char.knowledge)}")
    
    # Check for dialogue fatigue
    # recent_history = state.history[-5:] if state.history else []
    # dialogue_count = sum(1 for e in recent_history if '"' in e or "says" in e.lower())
    # if dialogue_count >= 3:
    #     lines.append("\n⚠️ NOTICE: Too much dialogue recently. Suggest PHYSICAL ACTIONS or EVENTS to break the cycle.")
    
    return "\n".join(lines)
