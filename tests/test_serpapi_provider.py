"""Tests for the SerpApi adapter, driven by recorded response shapes."""

import httpx
import pytest
import respx

from crowdgauge.errors import BusynessUnavailable, UpstreamError, VenueNotFound
from crowdgauge.models import Venue
from crowdgauge.providers.serpapi import SerpApiProvider, clamp_score, parse_hour_label

SEARCH_URL = "https://serpapi.com/search.json"


@pytest.fixture
def provider():
    return SerpApiProvider(api_key="test-key", timeout=5.0)


@pytest.fixture
def venue():
    return Venue(provider="serpapi", provider_venue_id="place-1", name="Test Cafe")


def _place_payload(popular_times: dict | None) -> dict:
    place: dict = {"place_id": "place-1", "title": "Test Cafe", "address": "Main Street 1"}
    if popular_times is not None:
        place["popular_times"] = popular_times
    return {"place_results": place}


@pytest.mark.parametrize(
    ("label", "expected"),
    [
        ("6 AM", 6),
        ("12 AM", 0),
        ("12 PM", 12),
        ("1 PM", 13),
        ("11 PM", 23),
        ("6 a.m.", 6),
        ("18", 18),
        ("noon", None),
        ("13 PM", None),
    ],
)
def test_parse_hour_label(label, expected):
    assert parse_hour_label(label) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [(0, 0), (55, 55), (100, 100), (140, 100), (-5, 0), (61.6, 62), ("55", None), (True, None)],
)
def test_clamp_score(value, expected):
    assert clamp_score(value) == expected


@respx.mock
async def test_search_maps_local_results_to_venues(provider):
    respx.get(SEARCH_URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "local_results": [
                    {
                        "place_id": "abc",
                        "title": "Cafe Central",
                        "address": "Bahnhofstrasse 1",
                        "gps_coordinates": {"latitude": 47.39, "longitude": 8.05},
                    }
                ]
            },
        )
    )
    venues = await provider.search_venues("Cafe Central")
    assert len(venues) == 1
    assert venues[0].name == "Cafe Central"
    assert venues[0].provider_venue_id == "abc"
    assert venues[0].latitude == pytest.approx(47.39)


@respx.mock
async def test_search_without_hits_raises(provider):
    respx.get(SEARCH_URL).mock(return_value=httpx.Response(200, json={"local_results": []}))
    with pytest.raises(VenueNotFound):
        await provider.search_venues("nowhere at all")


@respx.mock
async def test_fetch_report_parses_the_weekly_graph(provider, venue):
    payload = _place_payload(
        {
            "graph_results": {
                "monday": [
                    {"time": "8 AM", "info": "Usually not busy", "busyness_score": 20},
                    {"time": "1 PM", "info": "Usually a little busy", "busyness_score": 65},
                ],
                "saturday": [{"time": "6 PM", "busyness_score": 90}],
            },
            "live_hash": {
                "info": "Busier than usual",
                "busyness_score": 78,
                "time_spent": "People typically spend 30 min here",
            },
        }
    )
    respx.get(SEARCH_URL).mock(return_value=httpx.Response(200, json=payload))

    report = await provider.fetch_report(venue)

    monday = report.days[0]
    assert monday.hours[8].score == 20
    assert monday.hours[13].score == 65
    assert monday.hours[0].score is None
    assert report.days[5].hours[18].score == 90
    assert report.live is not None
    assert report.live.score == 78
    assert report.live.label == "Busier than usual"
    assert report.typical_visit_duration == "People typically spend 30 min here"
    assert report.has_forecast is True


@respx.mock
async def test_missing_popular_times_is_a_data_gap_not_a_failure(provider, venue):
    respx.get(SEARCH_URL).mock(return_value=httpx.Response(200, json=_place_payload(None)))
    with pytest.raises(BusynessUnavailable):
        await provider.fetch_report(venue)


@respx.mock
async def test_report_notes_the_absence_of_a_live_value(provider, venue):
    payload = _place_payload(
        {"graph_results": {"monday": [{"time": "9 AM", "busyness_score": 40}]}}
    )
    respx.get(SEARCH_URL).mock(return_value=httpx.Response(200, json=payload))
    report = await provider.fetch_report(venue)
    assert report.live is None
    assert any("no live value" in note for note in report.notes)


@respx.mock
@pytest.mark.parametrize(
    ("status", "fragment"),
    [(401, "rejected the API key"), (429, "rate limit"), (500, "HTTP 500")],
)
async def test_upstream_status_codes_become_readable_errors(provider, status, fragment):
    respx.get(SEARCH_URL).mock(return_value=httpx.Response(status, json={}))
    with pytest.raises(UpstreamError) as excinfo:
        await provider.search_venues("anything")
    assert fragment in str(excinfo.value)


@respx.mock
async def test_error_messages_never_contain_the_api_key(provider):
    respx.get(SEARCH_URL).mock(return_value=httpx.Response(403, json={"error": "bad key test-key"}))
    with pytest.raises(UpstreamError) as excinfo:
        await provider.search_venues("anything")
    assert "test-key" not in str(excinfo.value)


@respx.mock
async def test_timeout_becomes_an_upstream_error(provider):
    respx.get(SEARCH_URL).mock(side_effect=httpx.ConnectTimeout("timed out"))
    with pytest.raises(UpstreamError):
        await provider.search_venues("anything")
