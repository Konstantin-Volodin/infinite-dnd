# tests/context/character.py
"""Render the exact context sent to each Character agent."""

from __future__ import annotations
import sys
import os
import json
import logging
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from src.core.state import StateManager
from src.llm.prompts import build_character_system_prompt, build_character_context
from src.llm.tools import CHARACTER_TOOLS


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    state = StateManager().generate_state()

    archive_dir = os.path.join(os.path.dirname(__file__), "archive")
    os.makedirs(archive_dir, exist_ok=True)
    stamp = datetime.now().strftime("%Y-%m-%d")

    # per character context
    for char_id, char in state.characters.items():
        path = os.path.join(archive_dir, f"{stamp}-{char.id}.md")

        system = build_character_system_prompt(char)
        context = build_character_context(char, state)
        tools = CHARACTER_TOOLS

        output = f"##### Character: {char.id}\n\n"
        output += f"##### System Prompt\n{system}\n\n"
        output += f"##### Tools\n{json.dumps(tools, indent=4)}\n\n"
        output += f"##### Context\n{context}"

        with open(path, "w", encoding="utf-8") as f: f.write(output)
        logging.info(f"saved [{char.id}] context to {path}")


if __name__ == "__main__":
    main()
