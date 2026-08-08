"""Demo provider with synthetic curves, so the app runs without any API key.

This exists so the tool can be tried, tested in CI and screenshotted without
spending provider credits. Every report it produces is labelled as synthetic in
the API response and in the interface. It never contacts a network service.
"""

import hashlib
import math

from crowdgauge.models import (
    BusynessReport,
    DayBusyness,
    HourBusyness,
    LiveBusyness,
    Venue,
    Weekday,
)
from crowdgauge.providers.base import DEFAULT_SEARCH_LIMIT, BusynessProvider, normalise_query

# Peak hours and relative weight per venue archetype, picked so the shapes are
# visually distinguishable in the heatmap.
_ARCHETYPES = {
    "restaurant": ((12, 1.0), (19, 0.95)),
    "cafe": ((9, 1.0), (15, 0.7)),
    "gym": ((7, 0.9), (18, 1.0)),
    "store": ((11, 0.8), (17, 1.0)),
}
_WEEKEND_FACTOR = {5: 1.15, 6: 0.8}
_OPENING_HOURS = range(7, 23)


class DemoProvider(BusynessProvider):
    """Generates a deterministic, clearly labelled synthetic week."""

    name = "demo"
    display_name = "Demo (synthetic)"
    attribution_key = "attribution_demo"
    supports_live = True

    async def search_venues(self, query: str, limit: int = DEFAULT_SEARCH_LIMIT) -> list[Venue]:
        cleaned = normalise_query(query) or "Sample venue"
        name, _, address = cleaned.partition(",")
        return [
            Venue(
                provider=self.name,
                provider_venue_id=f"demo-{_fingerprint(cleaned)}",
                name=name.strip() or "Sample venue",
                address=address.strip() or None,
            )
        ][:limit]

    async def fetch_report(self, venue: Venue) -> BusynessReport:
        seed = _fingerprint(venue.name)
        archetype = self._pick_archetype(seed)
        days = [self._build_day(Weekday(index), archetype, seed) for index in range(7)]
        return BusynessReport(
            venue=venue,
            provider=self.name,
            provider_label=self.display_name,
            attribution=self.attribution,
            days=days,
            live=self._build_live(days, seed),
            # A bare duration instead of a sentence, so it needs no translation
            # and reads the same next to an English or a German label.
            typical_visit_duration="45 min",
            notes=[
                self._note("note_demo_synthetic"),
                self._note("note_demo_archetype", archetype=self._note(f"archetype_{archetype}")),
                self._note("note_demo_add_key"),
            ],
        )

    @staticmethod
    def _pick_archetype(seed: int) -> str:
        keys = sorted(_ARCHETYPES)
        return keys[seed % len(keys)]

    def _build_day(self, weekday: Weekday, archetype: str, seed: int) -> DayBusyness:
        factor = _WEEKEND_FACTOR.get(int(weekday), 1.0)
        hours = [
            HourBusyness(hour=hour, score=self._score(hour, archetype, factor, seed))
            for hour in range(24)
        ]
        return DayBusyness(weekday=weekday, hours=hours)

    @staticmethod
    def _score(hour: int, archetype: str, factor: float, seed: int) -> int | None:
        if hour not in _OPENING_HOURS:
            return None
        # Sum of two gaussian bumps around the archetype's peaks, so the curve
        # looks like a real footfall pattern instead of a flat block.
        total = sum(
            weight * math.exp(-(((hour - peak) / 2.1) ** 2))
            for peak, weight in _ARCHETYPES[archetype]
        )
        jitter = ((seed >> hour) % 7) - 3
        return max(0, min(100, int(total * 78 * factor) + jitter))

    @staticmethod
    def _build_live(days: list[DayBusyness], seed: int) -> LiveBusyness:
        """Derive a live value from a fixed reference slot, Wednesday 18:00.

        A fixed slot keeps the output reproducible, which matters for tests and
        for the screenshot in the README. No label is set, because the notes
        already state that everything here is synthetic.
        """
        reference = next(slot for slot in days[2].hours if slot.hour == 18)
        typical = reference.score or 40
        live = max(0, min(100, typical + (seed % 21) - 10))
        return LiveBusyness(score=live, delta_to_typical=live - typical)


def _fingerprint(text: str) -> int:
    """Stable positive integer for a venue name, independent of process start."""
    digest = hashlib.sha256(text.strip().lower().encode("utf-8")).digest()
    return int.from_bytes(digest[:4], "big")
