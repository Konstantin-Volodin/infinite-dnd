"""Deterministic faction-agenda and progress-clock operations."""

from src.engine.state.operations._base import _OpsBase


class FactionOps(_OpsBase):
    def advance_faction_clock(self, faction_id: str, clock_id: str, amount: int = 1) -> str:
        """Advance one clock, clamping at its segment count and firing its consequence once."""
        if amount < 0:
            return "Cannot advance a faction clock by a negative amount."

        faction = self.state.factions.get(faction_id)
        if not faction:
            return f"Cannot advance faction clock — faction '{faction_id}' not found."

        clock = next((candidate for candidate in faction.clocks if candidate.id == clock_id), None)
        if not clock:
            return f"Cannot advance faction clock — clock '{clock_id}' not found in faction '{faction_id}'."

        clock.progress = min(clock.segments, clock.progress + amount)
        if clock.progress == clock.segments and not clock.consequence_triggered:
            clock.consequence_triggered = True
            self._log(
                f"{faction.name} completes '{clock.name}'. {clock.consequence}",
                "",
            )
            return f"Clock '{clock_id}' completed. Consequence triggered: {clock.consequence}"
        return f"Clock '{clock_id}' advanced to {clock.progress}/{clock.segments}."

    def advance_faction_clocks(self, amount: int = 1) -> list[str]:
        """Advance every incomplete faction clock in stable faction/clock order."""
        results: list[str] = []
        for faction_id in sorted(self.state.factions):
            faction = self.state.factions[faction_id]
            for clock in sorted(faction.clocks, key=lambda candidate: candidate.id):
                if not clock.consequence_triggered:
                    results.append(self.advance_faction_clock(faction_id, clock.id, amount))
        return results
