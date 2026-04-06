# tests/context/dungeon_master.py
"""Render the exact context sent to the DM agent."""

from __future__ import annotations
import sys
import os
import json
import re
import logging
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from src.core.state import StateManager
from src.llm.prompts import build_dm_system_prompt, build_dm_context
from src.llm.tools import DM_TOOLS


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    state = StateManager().generate_state()

    archive_dir = os.path.join(os.path.dirname(__file__), "archive")
    os.makedirs(archive_dir, exist_ok=True)
    stamp = datetime.now().strftime("%Y-%m-%d")

    system = build_dm_system_prompt()
    context = build_dm_context(state, last_action=None)
    tools = DM_TOOLS

    output = f"##### Dungeon Master\n\n"
    output += f"##### System Prompt\n{system}\n\n"
    output += f"##### Tools\n{json.dumps(tools, indent=4)}\n\n"
    output += f"##### Context\n{context}"

    path = os.path.join(archive_dir, f"{stamp}-dungeon_master.md")
    with open(path, "w", encoding="utf-8") as f: f.write(output)
    logging.info(f"saved [DM] context to {path}")


if __name__ == "__main__":
    main()
