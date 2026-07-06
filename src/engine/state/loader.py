"""State Manager - load/save world state from JSON files."""

import json
import os
import re
import tempfile
from datetime import datetime
from pathlib import Path

from src.engine.state.models import (
    WorldState,
    Character,
    Location,
    CharacterStats,
    Quest,
)
from src.world import pick_scenario, read_manifest, scenario_dir

class StateManager:
    """Load, persist, and reset world state for a chosen scenario."""

    def __init__(
        self,
        scenario: str | None = None,
        state_dir: str = "world-state",
        run_id: str | None = None,
        *,
        resume: bool = False,
    ):
        self.ROOT_DIR = Path(__file__).resolve().parents[3]
        self.scenario = scenario or pick_scenario()
        self.manifest = read_manifest(self.scenario)
        self.setup_dir = scenario_dir(self.scenario)
        self.scenario_dir = self.ROOT_DIR / Path(state_dir) / self.scenario
        self.scenario_dir.mkdir(parents=True, exist_ok=True)
        latest_run = self.latest_run_id() if resume and run_id is None else None
        self.run_id = run_id or latest_run or datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self.state_dir = self.scenario_dir / self.run_id
        self.state_dir.mkdir(parents=True, exist_ok=True)

    def latest_run_id(self) -> str | None:
        """Return the run whose newest valid snapshot was modified most recently."""
        latest: tuple[float, str] | None = None
        for run_dir in self.scenario_dir.iterdir():
            if not run_dir.is_dir():
                continue
            snapshots = [
                path
                for path in run_dir.glob("world_state_*.json")
                if re.fullmatch(r"world_state_(\d+)\.json", path.name)
            ]
            if snapshots:
                candidate = (max(path.stat().st_mtime for path in snapshots), run_dir.name)
                if latest is None or candidate > latest:
                    latest = candidate
        return latest[1] if latest else None

    def read_json(self, path: str | Path):
        with open(path, "r", encoding="utf-8") as json_file:
            return json.load(json_file)

    def init_state(self) -> WorldState:
        """Load fresh world from setup files."""

        locations = {}
        locations_json = self.read_json(self.setup_dir / "locations.json")
        for loc in locations_json:
            locations[loc["id"]] = Location(
                id=loc["id"],
                description=loc.get("description", ""),
                connections=loc.get("connections", []),
                features=loc.get("features", []),
                items=loc.get("items", []),
            )

        characters = {}
        characters_json = self.read_json(self.setup_dir / "characters.json")
        for char in characters_json:
            characters[char["id"]] = Character(
                id=char["id"],
                location=char["location"],
                role=char.get("role", ""),
                stats=CharacterStats(**char.get("stats", {})),
                backstory=char.get("backstory", ""),
                personality=char.get("personality", ""),
                goal=char.get("goal", ""),
                inventory=char.get("inventory", []),
                knowledge=char.get("knowledge", []),
                relationships=char.get("relationships", {}),
            )

        quests = {}
        quests_json = self.read_json(self.setup_dir / "quests.json")
        for quest in quests_json:
            quests[quest["id"]] = Quest(
                id=quest["id"],
                title=quest.get("title", ""),
                description=quest.get("description", ""),
                status=quest.get("status", "active"),
                owner=quest.get("owner", ""),
                plan=quest.get("plan", []),
                current_step=quest.get("current_step", 0),
                steps=quest.get("steps", []),
            )

        word_state = WorldState(
            locations=locations,
            characters=characters,
            quests=quests
        )
        return word_state

    def load_state(self, world_state_file: str | None = None) -> WorldState:
        """Load saved state, or create fresh from setup if none exists."""

        if world_state_file:
            state_path = self.state_dir / world_state_file
            if not state_path.exists():
                raise FileNotFoundError(f"Specified world state file {state_path} does not exist.")
            return WorldState(**self.read_json(state_path))

        else:
            state = self.init_state()
            self.save_state(state)
            return state

    def latest_snapshot_name(self) -> str | None:
        """Return the highest numbered snapshot in this scenario, if any."""
        latest: tuple[int, str] | None = None
        for path in self.state_dir.glob("world_state_*.json"):
            match = re.fullmatch(r"world_state_(\d+)\.json", path.name)
            if match:
                candidate = (int(match.group(1)), path.name)
                if latest is None or candidate[0] > latest[0]:
                    latest = candidate
        return latest[1] if latest else None

    def save_state(self, state: WorldState):
        """Atomically save current world state to JSON."""
        state_file = self.state_dir / f"world_state_{state.time}.json"
        serialized_state = state.model_dump_json(indent=2)
        temp_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=self.state_dir,
                prefix=f".{state_file.name}.",
                suffix=".tmp",
                delete=False,
            ) as temp_file:
                temp_path = Path(temp_file.name)
                temp_file.write(serialized_state)
                temp_file.flush()
                os.fsync(temp_file.fileno())

            os.replace(temp_path, state_file)
        finally:
            if temp_path is not None:
                temp_path.unlink(missing_ok=True)
