"""
Game Rules - Mechanics derived from character stats.
"""

from src.engine.state.models import Character


def get_health_status(character: Character) -> str:
    """Return a health status string based on current hp percentage."""
    try:
        hp = character.stats.hp
        max_hp = character.stats.max_hp
        pct = (hp / max_hp) * 100 if max_hp else 0

        if hp <= 0: return "dead"
        if pct <= 25: return "critical"
        if pct <= 50: return "injured"
        else: return "healthy"

    except Exception:
        return "unknown"


if __name__ == "__main__":
    import logging
    from src.engine.state.models import CharacterStats

    logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")

    def _char(hp: int, max_hp: int) -> Character:
        return Character(id="test", stats=CharacterStats(hp=hp, max_hp=max_hp))

    assert get_health_status(_char(0, 20)) == "dead"
    assert get_health_status(_char(5, 20)) == "critical"   # 25%
    assert get_health_status(_char(10, 20)) == "injured"   # 50%
    assert get_health_status(_char(15, 20)) == "healthy"   # 75%
    assert get_health_status(_char(20, 20)) == "healthy"   # 100%
    assert get_health_status(_char(0, 0)) == "dead"        # hp<=0 wins over 0/0 division
    logging.info("get_health_status thresholds passed.")

    assert get_health_status(object()) == "unknown"  # malformed input falls back safely
    logging.info("get_health_status fallback passed.")

    logging.info(f"{__file__} tests completed successfully.")
