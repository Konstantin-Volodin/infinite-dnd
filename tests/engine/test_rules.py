import random

from src.engine.rules import attack_damage, get_health_status, kill_xp
from src.engine.state.models import Character, CharacterStats


def _char(hp: int, max_hp: int, level: int = 1) -> Character:
    return Character(id="test", stats=CharacterStats(hp=hp, max_hp=max_hp, level=level))


def test_get_health_status_thresholds():
    assert get_health_status(_char(0, 20)) == "dead"
    assert get_health_status(_char(5, 20)) == "critical"   # 25%
    assert get_health_status(_char(10, 20)) == "injured"   # 50%
    assert get_health_status(_char(15, 20)) == "healthy"   # 75%
    assert get_health_status(_char(20, 20)) == "healthy"   # 100%
    assert get_health_status(_char(0, 0)) == "dead"        # hp<=0 wins over 0/0 division


def test_get_health_status_fallback():
    assert get_health_status(object()) == "unknown"  # malformed input falls back safely


def test_attack_damage_scales_with_level():
    rng = random.Random(0)
    for level, low, high in [(1, 1, 4), (3, 3, 6)]:
        rolls = {attack_damage(_char(5, 5, level), rng) for _ in range(50)}
        assert min(rolls) == low and max(rolls) == high


def test_kill_xp_scales_with_level():
    assert kill_xp(_char(0, 5, 1)) == 25
    assert kill_xp(_char(0, 5, 3)) == 75
