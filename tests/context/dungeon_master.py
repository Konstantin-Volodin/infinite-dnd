"""Render the exact context sent to the DM agent.

Run:  python tests/context/dungeon-master.py

Output is printed AND saved to tests/context/archive/<datetime>-dungeon_master.md
"""
from __future__ import annotations

import io
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from src.core.state import StateManager
from src.prompts.dungeon_master import build_dm_system_prompt, build_dm_context

DIVIDER = "=" * 70


def section(title: str, content: str) -> str:
    return f"\n{DIVIDER}\n  {title}\n{DIVIDER}\n{content}"


def main():
    buf = io.StringIO()
    sm = StateManager()
    state = sm.generate_state()

    # ── System prompt (same every turn) ──
    buf.write(section("DM SYSTEM PROMPT", build_dm_system_prompt()))

    # ── Opening: no prior action ──
    buf.write(section("DM CONTEXT — opening (no last action)", build_dm_context(state, last_action=None)))

    # ── After a character action ──
    first_char = next(iter(state.characters), "unknown")
    fake_action = {
        "character_id": first_char,
        "tool": "speak",
        "result": {
            "status": "success",
            "intent": "Asks the merchant about her missing brother",
            "message": '"Have you seen Kaelen? He was supposed to meet me at the bridge."',
        },
    }
    buf.write(section("DM CONTEXT — after character speaks", build_dm_context(state, last_action=fake_action)))

    # ── With accumulated history ──
    state.history = [
        'elara-swift speaks: "Have you seen my brother Kaelen?"',
        'ronn-spice-merchant speaks: "Kaelen? Last I heard he was heading to the docks."',
        "elara-swift acts: examines the notice board for clues",
        "DM narrates: The notice board is covered in faded parchments. One catches Elara's eye — a torn note mentioning 'midnight shipment'.",
    ]
    state.time = 2

    buf.write(section("DM CONTEXT — with history (turn 2)", build_dm_context(state, last_action={
        "character_id": "elara-swift",
        "tool": "act",
        "result": {
            "status": "success",
            "intent": "examines the notice board",
            "message": "Elara examines the notice board carefully.",
        },
    })))

    # ── Write to archive ──
    output = buf.getvalue()
    print(output)

    archive_dir = os.path.join(os.path.dirname(__file__), "archive")
    os.makedirs(archive_dir, exist_ok=True)
    stamp = datetime.now().strftime("%Y-%m-%d--%H-%M")
    path = os.path.join(archive_dir, f"{stamp}-dungeon_master.md")
    with open(path, "w", encoding="utf-8") as f: f.write(output)
    print(f"\n📄 Saved to {path}")


if __name__ == "__main__":
    main()
