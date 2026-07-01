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
