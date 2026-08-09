"""Tests for the open data adapter.

Two things carry real risk here and are covered explicitly: the station name
travels from client input into a query language, and a stale reading must never
be presented as a live value.
"""

from datetime import UTC, datetime, timedelta

import httpx
import pytest
import respx

from crowdgauge.errors import BusynessUnavailable, UpstreamError, VenueNotFound
from crowdgauge.models import Venue
from crowdgauge.providers import opendata
from crowdgauge.providers.opendata import (
    CITIES,
    LIVE_MAX_AGE_HOURS,
    OpenDataProvider,
    _quote,
)

BASEL = next(city for city in CITIES if city.key == "basel")
RECORDS_URL = BASEL.records_url()


@pytest.fixture
def provider(monkeypatch):
    """Pin the city list, so adding a city later cannot break these tests."""
    monkeypatch.setattr(opendata, "CITIES", (BASEL,))
    return OpenDataProvider(timeout=5.0)


@pytest.fixture
def venue():
    return Venue(
        provider="opendata",
        provider_venue_id="basel:812 Wettsteinbrücke",
        name="812 Wettsteinbrücke",
        address="Basel (CH)",
    )


def _week_rows(peak_value: float = 300.0) -> list[dict]:
    """A full week where Saturday 16:00 is the peak."""
    rows = []
    for weekday in range(7):
        for hour in range(24):
            value = peak_value if (weekday, hour) == (5, 16) else 30.0
            rows.append({"weekday": weekday, "hourfrom": hour, "mean_value": value})
    return rows


def _mock_records(week: dict, latest: dict):
    """Answer by inspecting the select clause, since all calls share one URL.

    The weekly aggregation and the latest reading hit the same endpoint and
    differ only in their query, so routing has to look at the request itself.
    """

    def handler(request: httpx.Request) -> httpx.Response:
        select = request.url.params.get("select", "")
        return httpx.Response(200, json=latest if "hour_value" in select else week)

    return respx.get(RECORDS_URL).mock(side_effect=handler)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("Rebgasse", "'Rebgasse'"),
        ("O'Brien", "'O''Brien'"),
        ("back\\slash", "'backslash'"),
        ("' or 1=1 --", "''' or 1=1 --'"),
    ],
)
def test_quote_escapes_query_literals(value, expected):
    """Station names reach the query language from client supplied input."""
    assert _quote(value) == expected


@respx.mock
async def test_search_returns_station_names(provider):
    respx.get(RECORDS_URL).mock(
        return_value=httpx.Response(200, json={"results": [{"sitename": "812 Wettsteinbrücke"}]})
    )
    venues = await provider.search_venues("Wettstein")
    assert venues[0].name == "812 Wettsteinbrücke"
    assert venues[0].provider_venue_id == "basel:812 Wettsteinbrücke"
    assert venues[0].address == "Basel (CH)"


@respx.mock
async def test_search_uses_substring_search_not_equality(provider):
    """ODSQL 'like' matches the whole value, so search() is the correct call."""
    route = respx.get(RECORDS_URL).mock(
        return_value=httpx.Response(200, json={"results": [{"sitename": "812 Wettsteinbrücke"}]})
    )
    await provider.search_venues("Wettstein")
    where = route.calls.last.request.url.params["where"]
    assert "search(sitename, 'Wettstein')" in where


@respx.mock
async def test_search_without_matches_raises_venue_not_found(provider):
    respx.get(RECORDS_URL).mock(return_value=httpx.Response(200, json={"results": []}))
    with pytest.raises(VenueNotFound):
        await provider.search_venues("Bahnhof Aarau")


@respx.mock
async def test_search_surfaces_an_outage_instead_of_an_empty_result(provider):
    """Every city failing is an outage, not "nothing found"."""
    respx.get(RECORDS_URL).mock(return_value=httpx.Response(503, json={}))
    with pytest.raises(UpstreamError):
        await provider.search_venues("Wettstein")


@respx.mock
async def test_one_failing_portal_does_not_hide_the_others(monkeypatch):
    """A city being down must not swallow results from the remaining cities."""
    melbourne = next(city for city in CITIES if city.key == "melbourne")
    monkeypatch.setattr(opendata, "CITIES", (BASEL, melbourne))
    respx.get(RECORDS_URL).mock(return_value=httpx.Response(503, json={}))
    respx.get(melbourne.records_url()).mock(
        return_value=httpx.Response(200, json={"results": [{"sensor_name": "Bourke155_T"}]})
    )

    venues = await OpenDataProvider(timeout=5.0).search_venues("Bourke")

    assert [venue.name for venue in venues] == ["Bourke155_T"]
    assert venues[0].provider_venue_id == "melbourne:Bourke155_T"


def test_every_city_declares_a_usable_weekday_base():
    """Monday must be zero after the offset, or a whole week lands wrong."""
    assert all(city.weekday_base in (0, 1) for city in CITIES)


def test_every_city_points_at_a_concrete_dataset():
    """No placeholders: Dortmund renames columns between yearly datasets, so a
    computed dataset id would silently query the wrong schema."""
    assert all("{" not in city.dataset for city in CITIES)
    assert all(city.records_url().startswith("https://") for city in CITIES)


@respx.mock
async def test_week_is_scored_against_the_weekly_peak(provider, venue):
    _mock_records({"results": _week_rows(peak_value=300.0)}, {"results": []})

    report = await provider.fetch_report(venue)

    saturday = report.days[5]
    assert saturday.hours[16].score == 100
    assert saturday.hours[16].count == 300
    # 30 of 300 is ten percent, and the head count survives normalisation.
    assert report.days[0].hours[9].score == 10
    assert report.days[0].hours[9].count == 30


@respx.mock
async def test_a_recent_reading_becomes_a_live_value(provider, venue):
    recent = datetime.now(UTC) - timedelta(minutes=30)
    _mock_records(
        {"results": _week_rows(peak_value=300.0)},
        {"results": [{"datetimefrom": recent.isoformat(), "hour_value": 150.0}]},
    )

    report = await provider.fetch_report(venue)

    assert report.live is not None
    assert report.live.score == 50
    assert report.live.count == 150
    assert report.live.measured_at is not None


@respx.mock
async def test_a_stale_reading_is_not_presented_as_live(provider, venue):
    stale = datetime.now(UTC) - timedelta(hours=LIVE_MAX_AGE_HOURS + 1)
    _mock_records(
        {"results": _week_rows()},
        {"results": [{"datetimefrom": stale.isoformat(), "hour_value": 150.0}]},
    )

    report = await provider.fetch_report(venue)

    assert report.live is None
    # The absence has to be explained, otherwise it reads as a broken station.
    assert any("No live value" in note for note in report.notes)


@respx.mock
async def test_missing_readings_are_reported_as_a_data_gap(provider, venue):
    _mock_records({"results": []}, {"results": []})
    with pytest.raises(BusynessUnavailable):
        await provider.fetch_report(venue)


@respx.mock
async def test_unknown_city_prefix_is_rejected(provider):
    unknown = Venue(provider="opendata", provider_venue_id="genf:Rue du Test", name="Rue du Test")
    with pytest.raises(VenueNotFound):
        await provider.fetch_report(unknown)


@respx.mock
async def test_history_window_is_applied_to_the_query(provider, venue):
    route = _mock_records({"results": _week_rows()}, {"results": []})
    await provider.fetch_report(venue)
    week_calls = [
        call for call in route.calls if "mean_value" in call.request.url.params.get("select", "")
    ]
    where = week_calls[-1].request.url.params["where"]
    assert "datetimefrom > date'" in where
    assert "sitename='812 Wettsteinbrücke'" in where
