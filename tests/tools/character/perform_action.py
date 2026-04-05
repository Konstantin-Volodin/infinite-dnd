# tests/tools/character/perform_action.py
"""Live test: LLM calls perform_action given a physical task scenario."""

from __future__ import annotations
import sys
import os
import json
import logging
from datetime import datetime


sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))
from src.core.llm import LLMClient
from src.core.state import StateManager
from src.prompts.character.build import build_character_system_prompt
from src.tools import CHARACTER_TOOLS

TOOL = next(t for t in CHARACTER_TOOLS if t["name"] == "perform_action")
SCENARIO = "A locked iron chest sits in the corner of the room. You want to force it open."


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    llm = LLMClient()
    state = StateManager().generate_state()

    archive_dir = os.path.join(os.path.dirname(__file__), "..", "archive")
    os.makedirs(archive_dir, exist_ok=True)
    stamp = datetime.now().strftime("%Y-%m-%d")

    for char_id, char in state.characters.items():
        system_prompt = build_character_system_prompt(char)
        result = llm.chat_with_tools(system=system_prompt, user=SCENARIO, tools=CHARACTER_TOOLS, require_tool=True)

        calls = result.get("calls", [])
        passed = result["type"] == "tool_calls" and bool(calls) and calls[0]["tool"] == TOOL["name"]

        output  = f"##### Tool: {TOOL['name']} | {char.id} — {'PASS' if passed else 'FAIL'}\n\n"
        output += f"##### Scenario\n{SCENARIO}\n\n"
        output += f"##### Result\n{json.dumps(result, indent=2)}\n"

        path = os.path.join(archive_dir, f"{stamp}-{TOOL['name']}-{char.id}.md")
        with open(path, "w", encoding="utf-8") as f: f.write(output)
        logging.info(f"[{'PASS' if passed else 'FAIL'}] {TOOL['name']}:{char.id} → {path}")


if __name__ == "__main__":
    main()
