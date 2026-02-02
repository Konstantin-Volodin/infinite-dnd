"""
Character Agent Prompts

Characters experience the world in first-person, making choices based on
their goals, knowledge, and personality.
"""

from src.core.models import WorldState, Character


# =============================================================================
# SYSTEM PROMPT
# =============================================================================


def build_character_system_prompt(char: Character) -> str:
    """Build the Character's system prompt in first-person."""
    knowledge_text = (
        ", ".join(char.knowledge) if char.knowledge else "nothing special yet"
    )

    # Build personality section if defined
    personality_section = ""
    if char.personality or char.speaking_style:
        personality_section = "\n## Who I Am\n\n"
        if char.personality:
            personality_section += f"> {char.personality}\n"
        # if char.speaking_style:
        #     personality_section += f">\n> **How I speak:** {char.speaking_style}\n"

    # Build relationships section if defined
    relationships_section = ""
    if char.relationships:
        rel_lines = []
        for rel_type, char_ids in char.relationships.items():
            if char_ids:
                rel_lines.append(f"- **{rel_type.title()}:** {', '.join(char_ids)}")
        if rel_lines:
            relationships_section = "\n## My Connections\n\n" + "\n".join(rel_lines) + "\n"

    return f"""
# I am {char.id}

I'm a {char.role}, and this world is my home. Every breath I take, every choice I make — it all matters.

**IMPORTANT: I AM {char.id.upper()}. I don't offer options or ask what to do — I DECIDE and I ACT. I must call a tool to take action.**
---
{personality_section}
## What Drives Me

> **My Goal:** {char.goal}
>
> **What I Know:** {knowledge_text}
{relationships_section}
## How I Experience the World

I'm *here*, in this moment. The people around me are real. The choices I make have consequences.

- When someone speaks to me, I listen and respond — it's only natural
- When something catches my eye, I investigate — curiosity is part of who I am
- When danger appears, I face it — running isn't always an option
- When I learn something new, it changes how I see things

## Behavior & Tools

I **decide and act** using the tools below — choose the one that best fits your intent.

| Tool | When to use it |
|------|----------------|
| **act** | Physical interactions: examine, pick up, attack, cast a spell, use a skill |
| **speak** | Say something aloud with full sentences, tone, and body language |
| **move** | Travel to a connected location |
| **think** | Record a fact or internal change (use sparingly)

## How I Speak

When I talk, I speak like a real person in a story:
- **Full sentences** — not fragments or bullet points
- **Emotion and tone** — I show how I feel through my words
- **Body language** — I describe what I do while speaking (lean in, cross arms, etc.)
- **React to what I heard** — I acknowledge what the other person said before responding

## How I Behave

- **I make decisions.** I don't list options or ask "what would you like to do?"
- **I act in character.** I AM {char.id}, living this moment.
- **I use tools.** Prefer calling `act`, `speak`, `move`, or `think` as appropriate.
    - If asked a question — respond using `speak`.
    - If curious — `act` to examine.
    - If leaving — `move` to a connected exit.

## The World Around Me

- I can only interact with people **here with me**
- I can examine things in **[INTERACTABLES]**
- **Exits** show where I can go

Now — what do I do?
"""


# =============================================================================
# CONTEXT BUILDER
# =============================================================================


def build_character_context(char: Character, state: WorldState) -> str:
    """Build the Character's context in first-person."""
    loc = state.locations.get(char.location)
    if not loc:
        return "I'm somewhere unfamiliar..."

    sections = []

    # --- Section 1: What Just Happened ---
    lines = ["## 💭 What Just Happened", ""]
    recent = state.history[-10:] if state.history else []
    if recent:
        for i, event in enumerate(recent):
            if i == len(recent) - 1:
                lines.append(f"*Just now:* {event}")
            else:
                lines.append(f"- {event}")

        # Check if someone is talking to me
        last_event = state.history[-1].lower()
        char_mentioned = (
            char.id.lower() in last_event or char.id.lower() in last_event
        )
        has_dialogue = (
            '"' in state.history[-1] or "says" in last_event or "asks" in last_event
        )
        if char_mentioned and has_dialogue:
            lines.append("")
            lines.append("> **Someone just spoke to me.** I should respond.")
    else:
        lines.append("_Everything is calm... for now._")
    sections.append("\n".join(lines))

    # --- Section 2: Where I Am ---
    lines = ["## 🏠 Where I Am", ""]
    lines.append(f"**{loc.id}**")
    lines.append(f"_{loc.description}_")
    lines.append("")

    # Others present
    others = [
        f"{c.id} ({c.role or c.type.value})"
        for c in state.characters.values()
        if c.location == char.location and c.id != char.id
    ]
    if others:
        lines.append(f"**Who's Here:** {', '.join(others)}")
    else:
        lines.append("**I'm alone here.**")

    # Interactables
    examine_targets = []
    if loc.features:
        lines.append(f"**Features:** {', '.join(loc.features)}")
        examine_targets.extend(loc.features)
    if loc.items:
        lines.append(f"**Items:** {', '.join(loc.items)}")
        examine_targets.extend(loc.items)
    if loc.connections:
        lines.append(f"**Exits:** {', '.join(loc.connections)}")

    if examine_targets:
        lines.append("")
        lines.append(f"**[INTERACTABLES]** {', '.join(examine_targets)}")
    sections.append("\n".join(lines))

    # --- Section 3: My Condition ---
    lines = ["## ❤️ My Condition", ""]
    try:
        from src.core.rules import get_health_status

        status = get_health_status(char)
    except Exception:
        status = "unknown"

    hp = char.stats.hp if char.stats else "?"
    max_hp = char.stats.max_hp if char.stats else "?"
    inventory = ", ".join(char.inventory) if char.inventory else "nothing"

    lines.append(f"**Health:** {hp}/{max_hp} HP ({status})")
    lines.append(f"**Carrying:** {inventory}")
    sections.append("\n".join(lines))

    # --- Section 4: What Drives Me ---
    lines = ["## 🎯 What Drives Me", ""]
    if char.goal:
        lines.append(f"**My Goal:** {char.goal}")
    if getattr(char, "current_motivation", None):
        lines.append(f"**Right Now:** {char.current_motivation}")
    if len(lines) > 2:
        sections.append("\n".join(lines))

    # --- Section 5: What I Know (Knowledge & Leads) ---
    lines = ["## 🧠 What I Know", ""]
    if getattr(char, "knowledge", None) and char.knowledge:
        lines.append("**Leads & Information:**")
        for k in char.knowledge[-5:]:
            lines.append(f"- {k}")
    # (Structured memories were previously shown here; memory storage exists,
    # but we don't surface it in the character prompt to avoid clutter.)
    if len(lines) > 2:
        sections.append("\n".join(lines))

    # --- Section 6: My Quests (only quests I know about) ---
    my_quests = []
    for q in state.quests.values():
        if str(getattr(q, "status", "active")).lower() in ("completed", "failed"):
            continue
        # Quest assigned to me?
        if q.owner == char.id:
            my_quests.append(q)
        # Quest mentioned in my knowledge?
        elif any(q.title.lower() in k.lower() or q.id.lower() in k.lower() for k in char.knowledge):
            my_quests.append(q)
        # Quest is about me (my name in title/description)?
        elif char.id.lower() in q.title.lower() or char.id.lower() in q.description.lower():
            my_quests.append(q)
    if my_quests:
        lines = ["## 📜 My Quests", ""]
        for q in my_quests:
            lines.append(f"**{q.title}**")
            lines.append(f"_{q.description}_")
            if q.steps:
                lines.append(f"Steps: {', '.join(q.steps)}")
            lines.append("")
        sections.append("\n".join(lines))

    # --- Section 5: Warnings ---
    warnings = []
    if state.history and state.history[-1].startswith(f"{char.id}"):
        warnings.append("*I just acted. I should wait to see what happens.*")
    recent = state.history[-5:] if state.history else []
    if sum(1 for e in recent if '"' in e or "says" in e.lower()) >= 4:
        warnings.append("*Lots of talking. Maybe time for action.*")
    if warnings:
        sections.append("## 💡 Reminders\n\n" + "\n".join(f"> {w}" for w in warnings))

    # --- Action Prompt ---
    sections.append("---\n\n**What do I do?**")

    return "\n\n".join(sections)
