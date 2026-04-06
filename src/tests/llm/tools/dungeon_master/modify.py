# tests/tools/dungeon_master/modify.py
"""Live test: LLM calls modify to update world state."""

from __future__ import annotations
import sys
import os
import json
import logging
from datetime import datetime

from src.tests import ARCHIVE_DIR
from src.core.llm import LLMClient
from src.llm.tools import DM_TOOLS

TOOL = next(t for t in DM_TOOLS if t["name"] == "modify")

SYSTEM = "You are the Dungeon Master managing the world state. Use the modify tool to update existing entities."
SCENARIO = "elara-swift has found kaelen-swift and resolved the quest. Update quest 'missing-brother' to status 'completed'."


def main():
    llm = LLMClient()
    result = llm.chat_with_tools(system=SYSTEM, user=SCENARIO, tools=DM_TOOLS, require_tool=True)

    calls = result.get("calls", [])
    passed = result["type"] == "tool_calls" and bool(calls) and calls[0]["tool"] == TOOL["name"]

    stamp = datetime.now().strftime("%Y-%m-%d")

    output  = f"##### Tool: {TOOL['name']} — {'PASS' if passed else 'FAIL'}\n\n"
    output += f"##### Scenario\n{SCENARIO}\n\n"
    output += f"##### Result\n{json.dumps(result, indent=2)}\n"

    path = ARCHIVE_DIR / f"{stamp}-{TOOL['name']}.md"
    with open(path, "w", encoding="utf-8") as f:
        f.write(output)
    logging.info(f"[{'PASS' if passed else 'FAIL'}] {TOOL['name']} → {path}")


if __name__ == "__main__":
    main()
