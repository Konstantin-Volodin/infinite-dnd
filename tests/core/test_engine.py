import pytest
from src.engine.game_loop import Engine

def test_slugify():
    engine = Engine()
    
    # Basic strings
    assert engine._slugify("Market Square") == "market-square"
    assert engine._slugify("Guild Hall") == "guild-hall"
    
    # Underscores
    assert engine._slugify("guild_hall") == "guild-hall"
    assert engine._slugify("old_spice_cellar") == "old-spice-cellar"
    
    # Punctuation
    assert engine._slugify("The Old Spice Cellar!") == "the-old-spice-cellar"
    assert engine._slugify("Ronn's Shop") == "ronns-shop"
    assert engine._slugify("What?") == "what"
    
    # Multiple spaces and hyphens
    assert engine._slugify("Valley   Bridge") == "valley-bridge"
    assert engine._slugify("Valley---Bridge") == "valley-bridge"
    assert engine._slugify("  Space  ") == "space"
    
    # Leading/trailing hyphens
    assert engine._slugify("-Market-") == "market"
    assert engine._slugify("---Market---") == "market"
    
    # Empty/None
    assert engine._slugify("") == ""
    assert engine._slugify(None) == ""
    
    # Numbers
    assert engine._slugify("Level 10") == "level-10"
    assert engine._slugify("123-456") == "123-456"   