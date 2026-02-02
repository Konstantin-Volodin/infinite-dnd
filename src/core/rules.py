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
    attribute = SKILL_MAP.get(skill, "dexterity")  # Default to dex if unknown

    # Get attribute score
    attr_score = getattr(character.stats.attributes, attribute, 10)
    mod = get_modifier(attr_score)

    # Add proficiency bonus if applicable (simplified: level/4 + 2)
    # For now, we'll just use raw stats to keep it simple
    return mod


def get_health_status(character) -> str:
    """Return a health status string based on current hp percentage."""
    try:
        hp = character.stats.hp
        max_hp = character.stats.max_hp
        if hp <= 0:
            return "dead"
        pct = (hp / max_hp) * 100 if max_hp else 0
        if pct <= 25:
            return "critical"
        if pct <= 50:
            return "injured"
        return "healthy"
    except Exception:
        return "unknown"
