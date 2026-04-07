# Infinite DnD

AI-driven D&D engine where LLM agents run tabletop RPG sessions autonomously.

### 🚀 Features
- Autonomous campaign management
- NPC interaction & dialogue generation
- World generation & exploration
<!-- - character creation & tracking -->
<!-- - Combat system integration -->

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
- `infinite-dnd-logs` - runs the log viewer
- `infinite-dnd-tests` - runs the test suite

### 🤖 Code style                                                   
- Every change must leave the code easier to read than before.
- Prefer deletion over addition. If a refactor grows a file, question the approach.
- Remove dead code, redundant comments, and unused abstractions immediately.
- Simpler is correct. A smaller diff is usually a better diff.
- Before adding a function, check if the file's primary purpose is still singular. If not, it's time for a new module.

### 📂 Structure

```
src/                        - source code
├── agents/                 - LLM agent implementations
│   ├── action_resolver/        - resolves character actions
│   ├── character/              - any character agent
│   ├── dungeon_master/         - campaign management
│   └── director/               - determines turn order
├── engine/                 - game engine components
│   ├── rules.py                - game rules and derived stats
│   ├── utils.py                - shared engine helpers
│   ├── state/                  - world models and state persistence
│   ├── runtime/                - game loop orchestration
│   └── world/                  - world-state queries, interactions, and mutations
├── interface/              - user interface
├── tests/                  - test cases & fixtures
└── world/                  - world generation
```