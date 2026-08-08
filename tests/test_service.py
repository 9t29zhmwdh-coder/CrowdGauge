"""Tests for caching and the derived insight figures."""

import pytest

from crowdgauge.cache import TTLCache
from crowdgauge.config import Settings
from crowdgauge.models import BusynessReport, DayBusyness, HourBusyness, Venue, Weekday
from crowdgauge.providers.base import BusynessProvider
from crowdgauge.service import LookupService, busiest_hours, day_summary, quietest_hours


class CountingProvider(BusynessProvider):
    """Provider that records how often the upstream call would have happened."""

    name = "counting"
    display_name = "Counting"
    attribution = "test"

    def __init__(self):
        super().__init__(timeout=1.0)
        self.calls = 0

    async def search_venues(self, query, limit=8):
        return [Venue(provider=self.name, provider_venue_id="v1", name=query)]

    async def fetch_report(self, venue):
        self.calls += 1
        return BusynessReport(
            venue=venue,
            provider=self.name,
            provider_label=self.display_name,
            attribution=self.attribution,
            days=[
                DayBusyness(
                    weekday=Weekday(index),
                    hours=[HourBusyness(hour=hour, score=hour) for hour in range(24)],
                )
                for index in range(7)
            ],
        )


@pytest.fixture
def report():
    days = [
        DayBusyness(
            weekday=Weekday.MONDAY,
            hours=[
                HourBusyness(hour=0, score=None),
                HourBusyness(hour=9, score=0),
                HourBusyness(hour=12, score=95),
                HourBusyness(hour=15, score=20),
            ],
        )
    ]
    return BusynessReport(
        venue=Venue(provider="t", provider_venue_id="1", name="Test"),
        provider="t",
        provider_label="Test",
        attribution="test",
        days=days,
    )


def test_busiest_hours_are_sorted_high_to_low(report):
    assert [entry["score"] for entry in busiest_hours(report)] == [95, 20, 0]


def test_quietest_hours_skip_closed_and_empty_slots(report):
    quiet = quietest_hours(report)
    # Score 0 means closed here, and hour 0 has no data at all. Neither is a
    # useful "go at this time" recommendation.
    assert [entry["score"] for entry in quiet] == [20, 95]


def test_day_summary_reports_peak_and_mean(report):
    summary = day_summary(report.days[0])
    assert summary["peak_hour"] == 12
    assert summary["peak_score"] == 95
    assert summary["mean"] == round((0 + 95 + 20) / 3)


async def test_the_forecast_is_served_from_cache_on_the_second_call():
    provider = CountingProvider()
    service = LookupService(Settings(cache_ttl=600))
    venue = Venue(provider=provider.name, provider_venue_id="v1", name="Test")

    await service.report_for_venue(provider, venue)
    await service.report_for_venue(provider, venue)

    assert provider.calls == 1


async def test_a_disabled_cache_always_asks_the_provider():
    provider = CountingProvider()
    service = LookupService(Settings(cache_ttl=0))
    venue = Venue(provider=provider.name, provider_venue_id="v1", name="Test")

    await service.report_for_venue(provider, venue)
    await service.report_for_venue(provider, venue)

    assert provider.calls == 2


def test_ttl_cache_stores_and_clears():
    cache = TTLCache(ttl_seconds=60)
    cache.set("k", "v")
    assert cache.get("k") == "v"
    cache.clear()
    assert cache.get("k") is None


def test_ttl_cache_of_zero_stores_nothing():
    cache = TTLCache(ttl_seconds=0)
    cache.set("k", "v")
    assert cache.get("k") is None
    assert len(cache) == 0
