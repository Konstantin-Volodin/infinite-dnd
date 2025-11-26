# Infinite D&D - Roadmap

This roadmap prioritizes **Narrative Progression** to ensure the game tells a compelling story, followed by the mechanics needed to support it.

---

## 📖 Phase 1: The Narrative Engine (Story Progression)
*Goal: Give the AI a reason to act and a direction to go.*

- [ ] **Quest System**: Add `quests` to `WorldState`.
    - *Example*: `{"main_quest": "Find the Skeleton Key", "status": "active"}`.
- [ ] **Character Motivations**: Update `Character` model with `goals`.
    - *Example*: `goal="Protect the innocent"`.
    - *Implementation*: Inject this goal into the System Prompt so the agent proactively pursues it.
- [ ] **Active Director (Orchestrator Upgrade)**:
    - Give the Orchestrator the power to inject **Events** if the story stalls.
    - *Logic*: If 3 turns pass with no progress, spawn a "Complication" (e.g., "The roof collapses", "A goblin ambush").

---

## 📍 Phase 2: Spatial Consistency (Grounding)
*Goal: Prevent the story from breaking due to hallucinations.*

- [ ] **Enforce Connections**: Ensure characters can't teleport. They must move through connected rooms.
- [ ] **Location Descriptions**: Ensure the DM updates the description when the state changes (e.g., "The door is now broken").

---

## ⚔️ Phase 3: Core Mechanics (Resolution)
*Goal: meaningful consequences for actions.*

- [ ] **Simple Combat**: Basic HP tracking so threats are real.
- [ ] **Skill Consequences**: If a skill check fails, the story must branch negatively (e.g., "You trigger the trap").

---

## 🔄 Phase 4: The Loop
- [ ] **Game Runner**: A loop that continues until the Quest is resolved or the Party is defeated.