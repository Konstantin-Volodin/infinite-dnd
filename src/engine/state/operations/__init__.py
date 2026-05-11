"""World operations — character and world scoped."""

from .character import CharacterOps
from .world import WorldOps


class WorldOperations(CharacterOps, WorldOps):
    """Full operation surface. Shared __init__ / _log live on _OpsBase."""
