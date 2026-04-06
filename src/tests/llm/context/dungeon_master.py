# tests/context/dungeon_master.py
"""Render the exact context sent to the DM agent."""

from __future__ import annotations
import sys
import os
import json
import re
import logging
from datetime import datetime

from src.tests import ARCHIVE_DIR
from src.core.state import StateManager
from src.llm.prompts import dm_system, dm_context


def main():
    state = StateManager().generate_state()
    stamp = datetime.now().strftime("%Y-%m-%d")

    system = dm_system()
    context = dm_context(state, last_action=None)

    output = f"##### Dungeon Master\n\n"
    output += f"##### System Prompt\n{system}\n\n"
    output += f"##### Context\n{context}"

    path = ARCHIVE_DIR / f"{stamp}-dungeon_master.md"
    with open(path, "w", encoding="utf-8") as f: f.write(output)
    logging.info(f"saved [DM] context to {path}")


if __name__ == "__main__":
    main()
