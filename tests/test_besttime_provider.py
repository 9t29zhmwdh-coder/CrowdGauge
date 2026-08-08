"""Tests for the BestTime.app adapter.

The important detail under test is the 06:00 offset: BestTime's day_raw starts
at 6 AM, so hours after midnight belong to the following calendar day. Getting
this wrong shifts a whole night of data onto the wrong weekday.
"""

import httpx
import pytest
import respx

from crowdgauge.errors import BusynessUnavailable
from crowdgauge.models import Venue
from crowdgauge.providers.besttime import FORECAST_URL, LIVE_URL, BestTimeProvider


@pytest.fixture
def provider():
    return BestTimeProvider(private_key="priv-key", public_key="pub-key", timeout=5.0)


@pytest.fixture
def venue():
    return Venue(
        provider="besttime",
        provider_venue_id="Test Bar, Aarau",
        name="Test Bar",
        address="Aarau",
    )


def _day(day_int: int, raw: list[int]) -> dict:
    return {"day_info": {"day_int": day_int, "day_text": "Monday"}, "day_raw": raw}


def _forecast_payload(analysis: list) -> dict:
    return {
        "status": "OK",
        "analysis": analysis,
        "venue_info": {
            "venue_id": "ven-123",
            "venue_name": "Test Bar",
            "venue_address": "Bahnhofstrasse 1, Aarau",
            "venue_lat": 47.39,
            "venue_lon": 8.05,
        },
    }


async def test_search_splits_name_and_address_without_a_request(provider):
    venues = await provider.search_venues("Test Bar, Aarau")
    assert venues[0].name == "Test Bar"
    assert venues[0].address == "Aarau"


@respx.mock
async def test_day_raw_index_zero_is_six_in_the_morning(provider, venue):
    raw = [0] * 24
    raw[0] = 42  # index 0 is 06:00
    raw[6] = 77  # index 6 is 12:00
    respx.post(FORECAST_URL).mock(
        return_value=httpx.Response(200, json=_forecast_payload([_day(0, raw)]))
    )
    respx.post(LIVE_URL).mock(return_value=httpx.Response(404, json={}))

    report = await provider.fetch_report(venue)

    monday = report.days[0]
    assert monday.hours[6].score == 42
    assert monday.hours[12].score == 77
    assert monday.hours[0].score is None


@respx.mock
async def test_hours_after_midnight_land_on_the_next_calendar_day(provider, venue):
    raw = [0] * 24
    raw[19] = 88  # index 19 is 01:00 of the following day
    respx.post(FORECAST_URL).mock(
        return_value=httpx.Response(200, json=_forecast_payload([_day(0, raw)]))
    )
    respx.post(LIVE_URL).mock(return_value=httpx.Response(404, json={}))

    report = await provider.fetch_report(venue)

    assert report.days[1].hours[1].score == 88
    assert report.days[0].hours[1].score is None


@respx.mock
async def test_venue_info_replaces_what_the_user_typed(provider, venue):
    respx.post(FORECAST_URL).mock(
        return_value=httpx.Response(200, json=_forecast_payload([_day(0, [10] * 24)]))
    )
    respx.post(LIVE_URL).mock(return_value=httpx.Response(404, json={}))

    report = await provider.fetch_report(venue)

    assert report.venue.provider_venue_id == "ven-123"
    assert report.venue.address == "Bahnhofstrasse 1, Aarau"
    assert report.venue.latitude == pytest.approx(47.39)


@respx.mock
async def test_live_value_is_read_when_available(provider, venue):
    respx.post(FORECAST_URL).mock(
        return_value=httpx.Response(200, json=_forecast_payload([_day(0, [10] * 24)]))
    )
    respx.post(LIVE_URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "analysis": {
                    "venue_live_busyness": 61,
                    "venue_forecasted_busyness": 45,
                    "venue_live_busyness_available": True,
                    "venue_live_forecasted_delta": 16,
                }
            },
        )
    )

    report = await provider.fetch_report(venue)

    assert report.live is not None
    assert report.live.score == 61
    assert report.live.delta_to_typical == 16


@respx.mock
async def test_live_unavailable_flag_yields_no_live_value(provider, venue):
    respx.post(FORECAST_URL).mock(
        return_value=httpx.Response(200, json=_forecast_payload([_day(0, [10] * 24)]))
    )
    respx.post(LIVE_URL).mock(
        return_value=httpx.Response(
            200, json={"analysis": {"venue_live_busyness_available": False}}
        )
    )
    report = await provider.fetch_report(venue)
    assert report.live is None


@respx.mock
async def test_a_failing_live_call_does_not_lose_the_forecast(provider, venue):
    respx.post(FORECAST_URL).mock(
        return_value=httpx.Response(200, json=_forecast_payload([_day(0, [10] * 24)]))
    )
    respx.post(LIVE_URL).mock(return_value=httpx.Response(500, json={}))
    report = await provider.fetch_report(venue)
    assert report.live is None
    assert report.has_forecast is True


@respx.mock
async def test_empty_analysis_is_a_data_gap(provider, venue):
    respx.post(FORECAST_URL).mock(return_value=httpx.Response(200, json={"analysis": []}))
    with pytest.raises(BusynessUnavailable):
        await provider.fetch_report(venue)


@respx.mock
async def test_forecast_uses_the_private_key_and_live_uses_the_public_one(provider, venue):
    forecast_route = respx.post(FORECAST_URL).mock(
        return_value=httpx.Response(200, json=_forecast_payload([_day(0, [10] * 24)]))
    )
    live_route = respx.post(LIVE_URL).mock(
        return_value=httpx.Response(
            200, json={"analysis": {"venue_live_busyness_available": False}}
        )
    )

    await provider.fetch_report(venue)

    assert forecast_route.calls.last.request.url.params["api_key_private"] == "priv-key"
    assert live_route.calls.last.request.url.params["api_key_public"] == "pub-key"
