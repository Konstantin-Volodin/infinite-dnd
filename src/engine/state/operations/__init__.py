"""World operations — character and world scoped."""

from .character import CharacterOps
from .world import WorldOps


class WorldOperations(CharacterOps, WorldOps):
    """Full operation surface. CharacterOps takes MRO precedence for shared methods (_log, __init__)."""
