# tests/tools/dungeon_master/create.py
"""Live test: LLM calls create to add a new entity to the world."""

from __future__ import annotations
import sys
import os
import json
import logging
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))
from src.core.llm import LLMClient
from src.llm.tools import DM_TOOLS

TOOL = next(t for t in DM_TOOLS if t["name"] == "create")

SYSTEM = "You are the Dungeon Master managing the world state. Use the create tool to add new entities."
SCENARIO = "The characters have arrived at a ruined watchtower that doesn't exist in the world yet. Add it as a new location connected to the forest-trail."


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    llm = LLMClient()
    result = llm.chat_with_tools(system=SYSTEM, user=SCENARIO, tools=DM_TOOLS, require_tool=True)

    calls = result.get("calls", [])
    passed = result["type"] == "tool_calls" and bool(calls) and calls[0]["tool"] == TOOL["name"]

    archive_dir = os.path.join(os.path.dirname(__file__), "..", "archive")
    os.makedirs(archive_dir, exist_ok=True)
    stamp = datetime.now().strftime("%Y-%m-%d")

    output  = f"##### Tool: {TOOL['name']} — {'PASS' if passed else 'FAIL'}\n\n"
    output += f"##### Scenario\n{SCENARIO}\n\n"
    output += f"##### Result\n{json.dumps(result, indent=2)}\n"

    path = os.path.join(archive_dir, f"{stamp}-{TOOL['name']}.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write(output)
    logging.info(f"[{'PASS' if passed else 'FAIL'}] {TOOL['name']} → {path}")


if __name__ == "__main__":
    main()
