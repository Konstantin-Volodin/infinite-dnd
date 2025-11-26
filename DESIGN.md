# Infinite D&D - Design Document

## 1. Overview
A simulation-based D&D system where LLMs act as "drivers" for different entities within the world. The system separates the **World State** (the truth) from the **Intelligence** (the AI actors).

## 2. Core Architecture

### The World State (Data)
The state is the single source of truth. It is mutable and persists between turns.
- **Storage**: JSON files (initially) or Database.
- **Components**:
  - `Time`: Current game time/turn.
  - `Locations`: Static details (name, description) + Dynamic state (items on floor, weather).
  - `Characters`: PCs and NPCs with stats, inventory, and memory.
  - `Quests`: Active objectives and their completion status.

### The Engine (The Law)
A Python application that:
1. Loads the current state.
2. Enforces rules (e.g., "You cannot walk through a locked door").
3. Executes "Tools" requested by the AI.
4. Updates the State.

### The AI Actors (The Drivers)
Different "System Prompts" define the role the LLM plays.
- **DM Agent**:
  - **Goal**: Drive narrative, introduce novelty, manage pacing, adjudicate outcomes.
  - **Capabilities**: Change weather, spawn enemies, update quest logs, narrate scene transitions.
- **Character Agent (NPC/PC)**:
  - **Goal**: Roleplay a specific persona, achieve personal goals, survive.
  - **Capabilities**: `move`, `say`, `attack`, `pickup_item`, `use_item`.

## 3. Data Models

### Character
- **Identity**: Name, Race, Class, Backstory/Personality.
- **Stats**: HP, AC, Level, Attributes (STR, DEX, etc.).
- **State**: Current Location ID, Inventory, Status Effects.

### Location
- **Static**: ID, Name, Base Description, Connections (Exits).
- **Dynamic**: Current occupants, Items on ground, Environmental state (e.g., "burning").

### Quest
- **Meta**: Title, Description, Giver.
- **State**: Status (Not Started, Active, Completed, Failed), Current Stage.

## 4. The Game Loop
1. **State Refresh**: Engine loads the latest `world_state`.
2. **Turn Selection**: Engine decides whose turn it is (DM or specific Character).
3. **Context Assembly**: Engine builds a prompt:
   - *Who are you?* (System Prompt)
   - *Where are you?* (Location Description)
   - *What is happening?* (Recent History/Logs)
4. **Decision**: LLM receives context and selects a **Tool** (Action).
5. **Execution**: Engine validates and runs the tool.
   - *Success*: State is updated, event is logged.
   - *Failure*: Error returned to LLM to try again.
