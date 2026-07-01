from src.engine.rules import get_health_status
from src.engine.state.models import Character, CharacterStats


def _char(hp: int, max_hp: int) -> Character:
    return Character(id="test", stats=CharacterStats(hp=hp, max_hp=max_hp))


def test_get_health_status_thresholds():
    assert get_health_status(_char(0, 20)) == "dead"
    assert get_health_status(_char(5, 20)) == "critical"   # 25%
    assert get_health_status(_char(10, 20)) == "injured"   # 50%
    assert get_health_status(_char(15, 20)) == "healthy"   # 75%
    assert get_health_status(_char(20, 20)) == "healthy"   # 100%
    assert get_health_status(_char(0, 0)) == "dead"        # hp<=0 wins over 0/0 division


def test_get_health_status_fallback():
    assert get_health_status(object()) == "unknown"  # malformed input falls back safely
