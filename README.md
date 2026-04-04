# Infinite DnD

AI-driven D&D engine where LLM agents run collaborative tabletop RPG sessions autonomously.

## How It Works

Three agents collaborate:
- **Director**: Orchestrates the game flow and scene transitions
- **Character**: Acts within the world (move, speak, think, act)
- **DM**: Reacts to actions and drives the narrative (narrate, create, modify)

The agents work together in a structured loop until the session concludes.

## Environment

```bash
LLM_BASE_URL=http://localhost:11434/v1  # Default: Ollama
LLM_MODEL=qwen/qwen3-vl-4b
LLM_MAX_TOKENS=8192
```

## Project Structure

```
src/
├── agents/      # Runtime agents (director, character, dm)
├── core/        # LLM integration, game state, rules
├── engine/      # Game loop and action execution
├── prompts/     # System prompts per agent
└── tools.py     # Tool definitions
```


# TO TRY
- pydantic ai
- jinja template