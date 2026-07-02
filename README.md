# Infinite DnD

AI-driven D&D engine where LLM agents run tabletop RPG sessions autonomously.

### 🚀 Features
- Autonomous campaign management
- NPC interaction & dialogue generation
- World generation & exploration
- Character creation & tracking
- Gold/item economy & trading
- Combat, death & kill XP

### 📋 Prerequisites
**python environment**
- `uv venv .venv`
- `source .venv/Scripts/activate`
- `uv pip install -e .`

**LLM (CUDA):**
- download the LLAMA CUDA binary from the [llama.cpp releases page](https://github.com/ggerganov/llama.cpp/releases/latest)
- extract to desired path (`C:\Users\{USER}\.local\bin\llama-cuda`)
- add the folder to your `PATH`.

### ⚡ Running stuff
- `infinite-dnd` - runs the game
- `infinite-dnd --new-character` - runs the game with an interactively-created PC
- `infinite-dnd-logs` - runs the log viewer
- `infinite-dnd-scorecard` - compares campaign runs
- `infinite-dnd-dump-context` - dumps each agent's exact prompt/tools/context for inspection

### 🤖 Code style                                                   
- Every change must leave the code easier to read than before.
- Prefer deletion over addition. If a refactor grows a file, question the approach.
- Remove dead code, redundant comments, and unused abstractions immediately.
- Simpler is correct. A smaller diff is usually a better diff.
- Before adding a function, check if the file's primary purpose is still singular. If not, it's time for a new module.

### 🧪 Tests
- Tests live under `tests/`, mirroring `src/`'s layout — one `test_*.py` per source module.
- `uv run pytest` runs the unit suite: deterministic, fast, no live LLM calls.
- `uv run pytest -m integration` runs the live-agent suite (`tests/integration/`); needs a reachable LLM provider and is skipped otherwise.

### 📂 Structure

```
src/                        - source code
├── agents/                 - LLM agent implementations
│   ├── action_resolver/        - sole writer; resolves intents against state
│   ├── character/              - PC/NPC turn: emits a CharacterTool
│   ├── quest_reviewer/         - post-tick quest progress (Modify)
│   ├── time_keeper/            - per-event minute estimates
│   └── world_builder/          - post-tick entity enrichment (Create)
├── engine/                 - game engine components
│   ├── rules.py                - game rules and derived stats
│   ├── utils.py                - shared engine helpers
│   ├── state/                  - world models and state persistence
│   ├── runtime/                - game loop orchestration
│   └── world/                  - world-state queries, interactions, and mutations
├── interface/              - user interface
├── tests/                  - dumps each agent's exact prompt/tools/context for inspection
└── world/                  - scenario data (one subdir per scenario)
tests/                      - pytest suite, mirrors src/ layout
└── integration/                - live-agent tests, needs a reachable LLM provider
```