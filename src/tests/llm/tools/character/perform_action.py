# tests/tools/character/perform_action.py
"""Live test: LLM calls perform_action given a physical task scenario."""

from __future__ import annotations
import sys
import os
import json
import logging
from datetime import datetime


from src.tests import ARCHIVE_DIR
from src.core.llm import LLMClient
from src.core.state import StateManager
from src.llm.prompts.character.build import character_system
from src.llm.tools import CHARACTER_TOOLS

TOOL = next(t for t in CHARACTER_TOOLS if t["name"] == "perform_action")
SCENARIO = "A locked iron chest sits in the corner of the room. You want to force it open."


def main():
    llm = LLMClient()
    state = StateManager().generate_state()

    stamp = datetime.now().strftime("%Y-%m-%d")

    for char_id, char in state.characters.items():
        system_prompt = character_system(char)
        result = llm.chat_with_tools(system=system_prompt, user=SCENARIO, tools=CHARACTER_TOOLS, require_tool=True)

        calls = result.get("calls", [])
        passed = result["type"] == "tool_calls" and bool(calls) and calls[0]["tool"] == TOOL["name"]

        output  = f"##### Tool: {TOOL['name']} | {char.id} — {'PASS' if passed else 'FAIL'}\n\n"
        output += f"##### Scenario\n{SCENARIO}\n\n"
        output += f"##### Result\n{json.dumps(result, indent=2)}\n"

        path = ARCHIVE_DIR / f"{stamp}-{TOOL['name']}-{char.id}.md"
        with open(path, "w", encoding="utf-8") as f: f.write(output)
        logging.info(f"[{'PASS' if passed else 'FAIL'}] {TOOL['name']}:{char.id} → {path}")


if __name__ == "__main__":
    main()
