# Infinite DnD

AI-driven D&D engine where LLM agents run tabletop RPG sessions autonomously.

## How It Works

Two agents alternate in a ping-pong loop:
- **Character**: Picks a character and acts (move, speak, think, act)
- **DM**: Reacts with narration and world changes (narrate, create, modify)

## Setup

```bash
pip install -e .
python run_game.py
```

## Environment

```bash
LLM_BASE_URL=http://localhost:1234/v1   # LM Studio / Ollama
LLM_MODEL=qwen3.5-4b
LLM_MAX_TOKENS=-1
GAME_RESET_WORLD=true
GAME_MAX_SCENES=25
```

## Project Structure

```
src/
├── agents/      # Character and DM agents
├── core/        # LLM client, models, state, rules
├── engine/      # Game loop and action execution
├── prompts/     # System prompts per agent
└── tools.py     # Tool definitions
```
