"""Scenario discovery + random selection for world starts.

Each scenario lives under `src/world/<scenario-id>/` and contains four files:
    manifest.json, characters.json, locations.json, quests.json
"""

import json
import random
from pathlib import Path

_WORLD_DIR = Path(__file__).resolve().parent
_REQUIRED = ("manifest.json", "characters.json", "locations.json", "quests.json")


def list_scenarios() -> list[str]:
    """Subdirectories of src/world/ that hold a complete scenario, sorted by id."""
    return sorted(
        p.name
        for p in _WORLD_DIR.iterdir()
        if p.is_dir()
        and not p.name.startswith(("_", "."))
        and all((p / f).exists() for f in _REQUIRED)
    )


def pick_scenario(rng: random.Random | None = None) -> str:
    """Pick one scenario id at random. Pass an `rng` for deterministic tests."""
    scenarios = list_scenarios()
    if not scenarios:
        raise RuntimeError(f"No scenarios found under {_WORLD_DIR}")
    return (rng or random).choice(scenarios)


def read_manifest(scenario: str) -> dict:
    """Load the scenario manifest dict (title, pc, hook)."""
    path = _WORLD_DIR / scenario / "manifest.json"
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def scenario_dir(scenario: str) -> Path:
    """Absolute path to a scenario's directory. Raises if it doesn't exist."""
    path = _WORLD_DIR / scenario
    if not path.is_dir():
        raise FileNotFoundError(f"Scenario '{scenario}' not found at {path}")
    return path


if __name__ == "__main__":
    import logging

    logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")

    scenarios = list_scenarios()
    logging.info(f"discovered scenarios: {scenarios}")
    assert scenarios, "expected at least one scenario directory"
    assert all(isinstance(s, str) for s in scenarios)

    for s in scenarios:
        manifest = read_manifest(s)
        logging.info(f"  {s}: {manifest}")
        assert "title" in manifest and "pc" in manifest and "hook" in manifest, f"manifest missing keys for {s}"

    rng = random.Random(0)
    picks = {pick_scenario(rng) for _ in range(20)}
    logging.info(f"deterministic picks across 20 draws: {picks}")
    assert picks.issubset(set(scenarios))

    chosen = pick_scenario(random.Random(42))
    logging.info(f"random.Random(42) → {chosen}")
    assert chosen in scenarios

    d = scenario_dir(scenarios[0])
    assert d.is_dir()
    logging.info(f"scenario_dir('{scenarios[0]}') = {d}")

    logging.info(f"{__file__} tests completed successfully.")
