"""Render the exact context sent to the Character agent.

Run:  python tests/context/character.py

Output is printed AND saved to tests/context/archive/<datetime>-character.md
"""
from __future__ import annotations

import io
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from src.core.state import StateManager
from src.prompts.character import (
    build_character_system_prompt,
    build_character_context,
    build_casting_system_prompt,
    build_casting_context,
)

DIVIDER = "=" * 70


def section(title: str, content: str) -> str:
    return f"{DIVIDER}\n  {title}\n{DIVIDER}\n{content}"


def main():
    buf = io.StringIO()
    sm = StateManager()
    state = sm.generate_state()

    # ── Hinted mode: system prompt + context per character ──
    for char_id, char in state.characters.items():
        buf.write(section(f"SYSTEM PROMPT — {char_id}", build_character_system_prompt(char)))
        buf.write(section(f"CONTEXT — {char_id}", build_character_context(char, state)))

    # ── Casting mode: pick who acts ──
    buf.write(section("CASTING SYSTEM PROMPT", build_casting_system_prompt()))
    buf.write(section("CASTING CONTEXT (no location scope)", build_casting_context(state, location_id=None)))
    first_loc = next(iter(state.locations), None)
    if first_loc:
        buf.write(section(f"CASTING CONTEXT (scoped to {first_loc})", build_casting_context(state, location_id=first_loc)))

    # ── With some history ──
    state.history = [
        'elara-swift speaks: "Have you seen my brother Kaelen?"',
        'ronn-spice-merchant speaks: "Kaelen? Last I heard he was heading to the docks."',
        "elara-swift acts: examines the notice board for clues",
    ]
    state.time = 2

    for char_id, char in state.characters.items():
        buf.write(section(f"CONTEXT (with history) — {char_id}", build_character_context(char, state)))

    buf.write(section("CASTING CONTEXT (with history)", build_casting_context(state, location_id=None)))

    # ── Write to archive ──
    output = buf.getvalue()
    print(output)

    archive_dir = os.path.join(os.path.dirname(__file__), "archive")
    os.makedirs(archive_dir, exist_ok=True)
    stamp = datetime.now().strftime("%Y-%m-%d--%H-%M")
    path = os.path.join(archive_dir, f"{stamp}-character.md")
    with open(path, "w", encoding="utf-8") as f: f.write(output)
    print(f"\n📄 Saved to {path}")


if __name__ == "__main__":
    main()
