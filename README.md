# Infinite DnD

AI-driven D&D engine where LLM agents run tabletop RPG sessions autonomously.

## How It Works

Two LLM agents alternate in loop:
- **Character**: Picks a character and acts (move, speak, think, act)
- **DM**: Reacts with narration and world changes (narrate, create, modify)



```
src/
├── agents/      # Character and DM agents
├── core/        # LLM client, models, state, rules
├── engine/      # Game loop and action execution
├── prompts/     # System prompts per agent
└── tools.py     # Tool definitions
```


## TODO:
- add dotend?