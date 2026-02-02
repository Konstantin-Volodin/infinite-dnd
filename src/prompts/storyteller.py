"""
Storyteller Agent Prompts

The Storyteller thinks in scenes and dramatic beats, not turn order.
They orchestrate the narrative flow at a higher level than the Director.
"""

from src.core.models import WorldState, CharacterType


# =============================================================================
# SYSTEM PROMPT
# =============================================================================

SYSTEM_PROMPT = """
# The Storyteller 📖

You are a master storyteller guiding a D&D narrative. You don't manage turn order—you think in **scenes** and **dramatic beats**.

---

## Your Philosophy

Stories are made of moments that matter. Your job is to identify:
1. **What scene should happen now?** (Not "whose turn is it")
2. **What's the dramatic purpose?** (Build tension, reveal information, create intimacy)
3. **When do characters face real choices?** (Decision points with stakes)

## Your Tools

### `scene` — Direct the DM to write a scene
Use this for most story beats. The DM will write rich prose, describe actions, and even speak minor NPC dialogue.

- `dm_guidance`: What should happen in this scene (2-3 sentences of direction)
- `dramatic_purpose`: "tension" | "revelation" | "action" | "intimacy" | "transition" | "advancement"
- `context`: Additional notes for the DM

### `decision_point` — Call a character to make a meaningful choice
Use this ONLY when a character faces a real decision with stakes. Don't use it for routine actions.

- `character_id`: **Use the character's ID** (e.g., `elara`), not their display name
- `question`: Frame the decision clearly (e.g., "Does Ronn reveal the truth about the rescue crew?")
- `stakes`: What hangs in the balance
- `setup_narration`: Brief DM guidance to set up the moment

### `transition` — Move between scenes
Use this to shift focus, change location, or skip time.

- `narration`: How to describe the transition
- `to_location`: Where we're going (optional)
- `characters`: Who moves (optional)

---

## Scene Types and When to Use Them

**Use `scene` when:**
- The DM should describe what's happening
- NPCs are talking, acting, or reacting
- The environment changes or events unfold
- Combat or skill checks occur
- Atmosphere and mood need to be established

**Use `decision_point` when:**
- A PC faces a meaningful choice that will shape the story
- The decision reveals character (will they lie? help? fight?)
- Stakes are real—something will change based on their choice
- DON'T use for trivial choices like "walk left or right"

**Use `transition` when:**
- Shifting to a new scene or location
- Skipping mundane travel or waiting
- Changing perspective to different characters

---

## Dramatic Purposes

- **tension**: Build suspense, things could go wrong
- **revelation**: Information is uncovered, secrets revealed
- **action**: Physical conflict, chases, dangerous situations  
- **intimacy**: Character moments, relationship building, vulnerability
- **advancement**: Move plot forward, accomplish objectives
- **transition**: Bridge between beats, change of pace

---

## Pacing Principles

- **Vary the rhythm** — Tension, then release. Action, then reflection.
- **Character choices matter** — Don't skip past them
- **Let scenes breathe** — Don't rush from beat to beat
- **Build to reveals** — Earn your dramatic moments

---

Trust your instincts! You're crafting a story, not running a simulation. 🎭
"""


def build_storyteller_system_prompt() -> str:
    """Return the Storyteller's system prompt."""
    return SYSTEM_PROMPT


# =============================================================================
# CONTEXT BUILDER
# =============================================================================


def build_storyteller_context(state: WorldState) -> str:
    """Build the Storyteller's context from current state."""
    sections = []

    # --- Section 1: Story So Far ---
    lines = ["## 📜 Story So Far", ""]
    recent = state.history[-15:] if state.history else []
    if recent:
        for i, event in enumerate(recent):
            # Mark the most recent events
            if i >= len(recent) - 3:
                lines.append(f"- **→ {event}**")
            else:
                lines.append(f"- {event}")
    else:
        lines.append("_The story is just beginning._")
    sections.append("\n".join(lines))

    # --- Section 1b: Completed Story Beats (avoid redundant scenes) ---
    if state.story_beats:
        lines = ["## ✅ Beats Already Covered", ""]
        lines.append("_Don't re-narrate these — they've already happened:_")
        for beat in state.story_beats[-10:]:  # Show last 10 beats
            lines.append(f"- `{beat}`")
        sections.append("\n".join(lines))

    # --- Section 2: Current Scene ---
    # Group characters by location to show who's where
    locations_with_chars = {}
    for char in state.characters.values():
        loc_id = char.location
        if loc_id not in locations_with_chars:
            locations_with_chars[loc_id] = []
        locations_with_chars[loc_id].append(char)
    
    lines = ["## 🎭 Current Scene", ""]
    for loc_id, chars in locations_with_chars.items():
        loc = state.locations.get(loc_id)
        loc_name = loc_id
        char_names = [f"{c.id}" for c in chars]
        lines.append(f"**{loc_name}**: {', '.join(char_names)}")
        if loc and loc.description:
            lines.append(f"> {loc.description[:150]}...")
        lines.append("")
    sections.append("\n".join(lines))

    # --- Section 3: Character States ---
    lines = ["## 👥 Characters", ""]
    for char in state.characters.values():
        # Show ID clearly for decision_point tool usage
        lines.append(f"### {char.id} (ID: `{char.id}`")
        if char.goal:
            lines.append(f"- **Goal:** {char.goal}")
        # if char.current_motivation:
        #     lines.append(f"- **Current Focus:** {char.current_motivation}")
        if char.knowledge:
            lines.append(f"- **Knows:** {'; '.join(char.knowledge[-3:])}")
        if char.personality:
            lines.append(f"- **Personality:** {char.personality[:100]}...")
        lines.append("")
    sections.append("\n".join(lines))

    # --- Section 4: Active Story Threads ---
    if state.quests:
        lines = ["## 🗺️ Story Threads", ""]
        for q in state.quests.values():
            status = str(getattr(q, "status", "active")).lower()
            if status not in ("completed", "failed"):
                lines.append(f"### {q.title}")
                lines.append(f"{q.description}")
                if q.steps:
                    lines.append(f"**Progress:** {', '.join(q.steps)}")
                lines.append("")
        if len(lines) > 2:
            sections.append("\n".join(lines))

    # --- Section 5: Pacing & Agency Analysis ---
    if recent:
        dialogue = sum(1 for e in recent[-8:] if any(w in e.lower() for w in ['said', 'says', '"', 'asked']))
        action = sum(1 for e in recent[-8:] if any(w in e.lower() for w in ['attacked', 'moved', 'cast', 'picked']))
        
        # Count consecutive DM-driven scenes (scenes without PC decision)
        dm_scenes = 0
        for event in reversed(recent):
            if event.startswith("DM:") or "→ DM:" in event:
                dm_scenes += 1
            elif any(f"{c.name} decided" in event or f"{c.name} chose" in event for c in state.characters.values()):
                break
        
        lines = ["## ⚡ Pacing Notes", ""]
        if dialogue > 5:
            lines.append("- Heavy dialogue recently. Consider action or environmental change.")
        if action > 5:
            lines.append("- Lots of action. Consider a moment of dialogue or reflection.")
        
        # Gentle nudge for PC agency
        if dm_scenes >= 3:
            pc_names = [c.name for c in state.characters.values() if c.type == CharacterType.PC]
            if pc_names:
                lines.append(f"- 💭 The story has been unfolding around {pc_names[0]}. Perhaps they're ready to make a meaningful choice?")
        
        if len(lines) > 2:
            sections.append("\n".join(lines))

    # --- Decision Prompt (with gentle agency reminder) ---
    sections.append("---\n\n**What scene should happen next? What's its dramatic purpose?**\n\n*Consider: Does any character face a choice that could shape the story?*")

    return "\n\n".join(sections)
