"""
Director Agent Prompts

The Director controls narrative flow and pacing, deciding which agent acts next.
"""

from src.core.models import WorldState


# =============================================================================
# SYSTEM PROMPT
# =============================================================================

SYSTEM_PROMPT = """
# Welcome, Director! 🎬

You're the creative force guiding this D&D story. Your job is to keep the narrative flowing naturally while giving each character meaningful moments.

---

## Your Tool

**`direct`** — Select who acts next and provide guidance.
- `actor`: character_id or "dm"
- `guidance`: What they should focus on (frame as internal monologue for characters)
- `move_to` (optional): Location ID for scene transitions
- `move_characters` (optional): Which characters to move

Call `direct` multiple times to plan a sequence of actors.

## Pacing Guidelines

- **Vary the rhythm** — Mix action, dialogue, exploration, and quiet moments
- **Follow emotional beats** — After tension, allow release; after discovery, allow reflection
- **Character moments matter** — Give PCs time to react to events before moving on
- **Don't rush resolutions** — Let conversations and encounters breathe

## Selection Logic

**Select an NPC when:**
- A PC just spoke TO them — they should respond in their own voice
- They have information relevant to the current situation
- They want to initiate conversation or action
- NPCs are full characters with their own agency. They speak for themselves!

**Select the DM when:**
- The scene needs description or atmosphere
- Environmental events should occur (weather, sounds, arrivals)
- Action outcomes need narration
- Combat or skill checks need resolution
- Transitions between scenes

**Select a PC when:**
- They were just addressed or affected
- It's their turn in conversation
- Their skills are relevant
- They haven't acted in a while

---

Trust your storytelling instincts! 🎭
"""


def build_director_system_prompt() -> str:
    """Return the Director's system prompt."""
    return SYSTEM_PROMPT


# =============================================================================
# CONTEXT BUILDER
# =============================================================================


def build_director_context(state: WorldState) -> str:
    """Build the Director's context from current state."""
    sections = []

    # --- Section 1: Recent Events ---
    lines = ["## 📜 Recent Events", ""]
    recent = state.history[-10:] if state.history else []
    if recent:
        for i, event in enumerate(recent):
            marker = "🔴" if i >= len(recent) - 2 else "⚪"
            lines.append(f"- {marker} {event}")
    else:
        lines.append("_No events yet._")
    sections.append("\n".join(lines))

    # --- Section 2: Action Variety ---
    if recent:
        action_types = []
        for e in recent[-5:]:
            e_lower = e.lower()
            if "moved to" in e_lower:
                action_types.append("move")
            elif any(w in e_lower for w in ['said', 'says', 'asked', 'asks', '"']):
                action_types.append("speak")
            elif any(w in e_lower for w in ['examined', 'picked up', 'attacked', 'cast']):
                action_types.append("act")
            else:
                action_types.append("other")
        if action_types.count("speak") >= 4:
            sections.append("## ⚡ Pacing Note\n\n> **Lots of dialogue recently.** Consider guiding toward movement or physical action.")

    # --- Section 3: Characters (with goals & knowledge) ---
    lines = ["## 👥 Characters", ""]
    actors = ["dm"] + list(state.characters.keys())
    lines.append(f"**Available actors:** {', '.join(actors)}")
    lines.append("")
    for char in state.characters.values():
        loc = state.locations.get(char.location)
        loc_name = loc.id if loc else "unknown"
        others = [
            c.id
            for c in state.characters.values()
            if c.location == char.location and c.id != char.id
        ]
        others_str = f" (with {', '.join(others)})" if others else ""
        lines.append(f"### {char.id}")
        lines.append(f"- **Location:** {loc_name}{others_str}")
        if char.goal:
            lines.append(f"- **Goal:** {char.goal}")
        # if char.current_motivation:
        #     lines.append(f"- **Focus:** {char.current_motivation}")
        if char.knowledge:
            lines.append(f"- **Knows:** {'; '.join(char.knowledge[-3:])}")
        # Show available exits for movement guidance
        if loc and loc.connections:
            lines.append(f"- **Can travel to:** {', '.join(loc.connections)}")
        lines.append("")
    sections.append("\n".join(lines))

    # --- Section 4: Active Quests ---
    if state.quests:
        lines = ["## 🗺️ Active Quests", ""]
        for q in state.quests.values():
            if str(getattr(q, "status", "active")).lower() not in (
                "completed",
                "failed",
            ):
                lines.append(f"### {q.title}")
                lines.append(f"{q.description}")
                if q.steps:
                    lines.append(f"**Steps:** {', '.join(q.steps)}")
                # Find which characters know about this quest
                involved = []
                for char in state.characters.values():
                    if q.owner == char.id:
                        involved.append(f"{char.id} (owns)")
                    elif any(q.title.lower() in k.lower() or q.id in k.lower() for k in char.knowledge):
                        involved.append(f"{char.id} (knows leads)")
                if involved:
                    lines.append(f"**Involved:** {', '.join(involved)}")
                lines.append("")
        if len(lines) > 2:
            sections.append("\n".join(lines))

    # --- Decision Prompt ---
    sections.append("---\n\n**Who should act next?**")

    return "\n\n".join(sections)
