# tests/tools/dungeon_master/modify.py
"""Live test: LLM calls modify to update world state."""

from __future__ import annotations
import sys
import os
import json
import logging
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))
from src.core.llm import LLMClient
from src.tools import DM_TOOLS

TOOL = next(t for t in DM_TOOLS if t["name"] == "modify")

SYSTEM = "You are the Dungeon Master managing the world state. Use the modify tool to update existing entities."
SCENARIO = "elara-swift has found kaelen-swift and resolved the quest. Update quest 'missing-brother' to status 'completed'."


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    llm = LLMClient()
    result = llm.chat_with_tools(system=SYSTEM, user=SCENARIO, tools=[TOOL], require_tool=True)

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
