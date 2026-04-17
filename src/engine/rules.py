"""
Game Rules - Mechanics for dice rolling, stats, and skills.
"""

import math

# Map skills to their governing attribute
SKILL_MAP = {
    "athletics": "strength",
    "acrobatics": "dexterity",
    "sleight_of_hand": "dexterity",
    "stealth": "dexterity",
    "arcana": "intelligence",
    "history": "intelligence",
    "investigation": "intelligence",
    "nature": "intelligence",
    "religion": "intelligence",
    "animal_handling": "wisdom",
    "insight": "wisdom",
    "medicine": "wisdom",
    "perception": "wisdom",
    "survival": "wisdom",
    "deception": "charisma",
    "intimidation": "charisma",
    "performance": "charisma",
    "persuasion": "charisma",
}


def get_modifier(score: int) -> int:
    """Calculate ability modifier from score (e.g., 10 -> 0, 12 -> +1)."""
    return math.floor((score - 10) / 2)


def get_skill_modifier(character, skill_name: str) -> int:
    """Get the total modifier for a skill check."""
    skill = skill_name.lower().replace(" ", "_")
    attribute = SKILL_MAP.get(skill, "dexterity")

    attrs = getattr(character.stats, "attributes", None)
    attr_score = getattr(attrs, attribute, 10) if attrs else 10
    return get_modifier(attr_score)


def get_health_status(character) -> str:
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
