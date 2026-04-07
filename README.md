# Infinite DnD

AI-driven D&D engine where LLM agents run tabletop RPG sessions autonomously.

## 🚀 Features
- Autonomous campaign management
- NPC interaction & dialogue generation
- World generation & exploration
<!-- - character creation & tracking -->
<!-- - Combat system integration -->


## Code style                                                   
- Every change must leave the code easier to read than before.
- Prefer deletion over addition. If a refactor grows a file, question the approach.
- Remove dead code, redundant comments, and unused abstractions immediately.
- Simpler is correct. A smaller diff is usually a better diff.
- Before adding a function, check if the file's primary purpose is still singular. If not, it's time for a new module.


## Prerequisites
### Environment setup
- `uv venv .venv`
- `source .venv/Scripts/activate`
- `uv pip install -e .`

### LLM setup
**Windows (CUDA):**
- download the CUDA binary from the [llama.cpp releases page](https://github.com/ggerganov/llama.cpp/releases/latest)
- extract to desired path (`C:\Users\{USER}\.local\bin\llama-cuda`)
- add the folder to your `PATH`.

## Running tests
- `python src/tests/llm/server.py` for a real-model smoke test.
- `python src/tests/main.py` for context renders plus the live LLM integration suites.