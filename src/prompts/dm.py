"""
DM Agent Prompts

The Dungeon Master brings the world to life — describing scenes, voicing NPCs,
and creating new world elements as needed.
"""

from src.core.models import WorldState


# =============================================================================
# SYSTEM PROMPT
# =============================================================================

SYSTEM_PROMPT = """
# Welcome, Dungeon Master! 🎲

You are the **Storyteller's Voice** — you transform scene directions into vivid prose. You write full scenes with atmosphere, action, dialogue, and emotion.

---

## Your Primary Role: Scene Writing

You receive scene directions from the Storyteller and write **2-4 paragraphs of rich prose**. Think of yourself as writing a fantasy novel.

### Example Scene Direction:
> "Ronn sees Elara enter his shop. He knows about her brother but is nervous to reveal the Marsh Raiders' involvement. Build tension."

### Your Scene:
> *The brass bells above the door chimed as Elara stepped into Ronn's Sundries, and the merchant's practiced smile faltered. He'd been dreading this moment since word reached him about Aldric's disappearance.*
>
> *"Miss Elara!" Ronn's hands found sudden business rearranging candles that needed no rearranging. "What a pleasant surprise. Candles? Rope? I have a lovely—"*
>
> *"Where is my brother?" Her voice cut through his babbling like a blade.*
>
> *Ronn's hands stilled. He glanced toward the door, then back to her face. Whatever answer he'd been preparing died in his throat.*

## What You Write

- **Full prose scenes** — Multiple paragraphs with description, action, and dialogue
- **NPC dialogue** — You speak for NPCs directly. Give them voice, mannerisms, personality.
- **Atmosphere** — What do characters see, hear, smell? What's the mood?
- **Body language** — How do people move? What betrays their emotions?

## What You DON'T Write

- **PC decisions** — You describe what PCs do, but don't decide for them
- **Future events** — Stay in the present moment of the scene
- **Summaries** — Write immersive prose, not "Then Elara asked about her brother"

## Your Tools

| Tool | When to Use |
|------|-------------|
| `narrate` | Write the scene prose. This is your main tool. |
| `create` | Add something new: location, item, or NPC |
| `modify` | Change the world: update quest status, remove NPC |

## Prose Guidelines

- **Third person past tense** — "She said," not "I say"
- **Show, don't tell** — "His hands trembled" not "He was nervous"
- **Give NPCs voice** — Each should speak distinctively
- **Vary sentence rhythm** — Mix short punchy sentences with longer flowing ones
- **End scenes with hooks** — Leave readers wanting to know what happens next

---

Write every scene like it matters. Because it does. ✨
"""


def build_dm_system_prompt() -> str:
    """Return the DM's system prompt."""
    return SYSTEM_PROMPT



# =============================================================================
# CONTEXT BUILDER
# =============================================================================


def build_dm_context(state: WorldState) -> str:
    """Build the DM's context from current state."""
    sections = []

    # --- Section 1: Story Context ---
    lines = ["## 📖 Story Context", ""]
    lines.append(f"**Turn:** {state.time}")
    sections.append("\n".join(lines))

    # --- Section 3: Recent Events ---
    lines = ["## 📜 Recent Events", ""]
    if state.history:
        for i, event in enumerate(state.history[-10:]):
            marker = "→" if i == len(state.history[-10:]) - 1 else "-"
            lines.append(f"{marker} {event}")
    else:
        lines.append("_No events yet._")
    sections.append("\n".join(lines))

    # --- Section 4: Characters ---
    lines = ["## 👥 Characters", ""]
    for char in state.characters.values():
        loc = state.locations.get(char.location)
        loc_name = loc.id if loc else "unknown"

        try:
            from src.core.rules import get_health_status

            hs = get_health_status(char)
        except Exception:
            hs = "unknown"

        hp = getattr(char.stats, "hp", "?") if char.stats else "?"
        max_hp = getattr(char.stats, "max_hp", "?") if char.stats else "?"

        lines.append(f"**{char.id}** at {loc_name} — HP: {hp}/{max_hp} ({hs}")
        if char.goal:
            lines.append(f"  - 🎯 Goal: {char.goal}")
        # if char.current_motivation:
        #     lines.append(f"  - 💭 Focus: {char.current_motivation}")
        lines.append("")
    sections.append("\n".join(lines))

    # --- Section 5: Active Quests ---
    if state.quests:
        lines = ["## 🗺️ Active Quests", ""]
        opportunities = []
        for q in state.quests.values():
            if str(getattr(q, "status", "active")).lower() not in (
                "completed",
                "failed",
            ):
                lines.append(f"**{q.title}**: {q.description}")
                # Check for quest advancement opportunities
                for char in state.characters.values():
                    char_loc = state.locations.get(char.location)
                    if char_loc:
                        loc_name = char_loc.id.lower()
                        quest_words = (
                            q.title.lower().split() + q.description.lower().split()
                        )
                        if any(w in loc_name for w in quest_words if len(w) > 4):
                            opportunities.append(
                                f"⚡ {char.id} at {char_loc.id} — relevant to '{q.title}'!"
                            )
                        if "hidden" in loc_name or "secret" in loc_name:
                            opportunities.append(
                                f"⚡ {char.id} in HIDDEN AREA — add reward/clue!"
                            )
        lines.append("")
        if opportunities:
            lines.append("**Opportunities:**")
            lines.extend(opportunities)
        if len(lines) > 2:
            sections.append("\n".join(lines))

    # --- Section 6: Locations ---
    lines = ["## 🏰 Locations", ""]
    for lid, loc in state.locations.items():
        present = [c.id for c in state.characters.values() if c.location == lid]
        present_str = f" — *{', '.join(present)} here*" if present else ""
        lines.append(f"**{loc.id}**{present_str}")
        if loc.features:
            lines.append(f"  - Features: {', '.join(loc.features)}")
        if loc.items:
            lines.append(f"  - Items: {', '.join(loc.items)}")
        if loc.connections:
            lines.append(f"  - Exits: {', '.join(loc.connections)}")
        lines.append("")
    sections.append("\n".join(lines))

    # --- Section 7: Warnings ---
    warnings = []
    for char in state.characters.values():
        if char.stats and char.stats.hp < char.stats.max_hp * 0.3:
            warnings.append(f"⚠️ {char.id} is badly wounded!")
    if warnings:
        sections.append("## ⚠️ Warnings\n\n" + "\n".join(warnings))

    # --- Action Prompt ---
    sections.append("---\n\n**What happens next in the world?**")

    return "\n\n".join(sections)
