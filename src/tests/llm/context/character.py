# tests/context/character.py
"""Render the exact context sent to each Character agent."""

from __future__ import annotations
import sys
import os
import json
import logging
from datetime import datetime

from src.tests import ARCHIVE_DIR
from src.core.state import StateManager
from src.llm.prompts import character_system, character_context
from src.llm.character import agent


def main():
    state = StateManager().generate_state()
    stamp = datetime.now().strftime("%Y-%m-%d")

    # per character context
    for char_id, char in state.characters.items():
        path = ARCHIVE_DIR / f"{stamp}-{char.id}.md"

        system = character_system(char)
        context = character_context(char, state)

        tools = {
            name: {"description": td.description, "parameters": td.parameters_json_schema}
            for name, t in agent._function_toolset.tools.items()
            if (td := t.tool_def)
        }

        output = f"##### Character: {char.id}\n\n"
        output += f"##### System Prompt\n{system}\n\n"
        output += f"##### Tools\n{json.dumps(tools, indent=2)}\n\n"
        output += f"##### Context\n{context}"

        with open(path, "w", encoding="utf-8") as f: f.write(output)
        logging.info(f"saved [{char.id}] context to {path}")


if __name__ == "__main__":
    main()
