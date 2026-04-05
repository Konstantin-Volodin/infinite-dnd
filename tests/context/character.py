"""Render the exact context sent to the Character agent.

Run:  python tests/context/character.py

Output is printed AND saved to tests/context/archive/<datetime>-character.md
"""
from __future__ import annotations

import sys
import os
import logging
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from src.core.state import StateManager
from src.prompts.character import build_character_system_prompt, build_character_context


def main():
    sm = StateManager()
    state = sm.generate_state()

    archive_dir = os.path.join(os.path.dirname(__file__), "archive")
    os.makedirs(archive_dir, exist_ok=True)
    stamp = datetime.now().strftime("%Y-%m-%d")

    # per character context
    for char_id, char in state.characters.items():
        path = os.path.join(archive_dir, f"{stamp}-{char_id}.md")

        system_prompt = build_character_system_prompt(char)
        context = build_character_context(char, state)

        output = f"##### Character: {char.id}\n\n"
        output += f"##### System Prompt\n{system_prompt}\n\n"
        output += f"##### Context\n{context}"

        with open(path, "w", encoding="utf-8") as f: f.write(output)
        logging.info(f"saved [{char_id}] context to {path}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    main()
