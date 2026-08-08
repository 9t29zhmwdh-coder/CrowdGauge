"""Tests for language handling across the backend.

The rule under test: nothing the interface displays may come back in a language
the user did not ask for.
"""

import httpx
import pytest
import respx
from fastapi.testclient import TestClient

from crowdgauge.app import create_app
from crowdgauge.config import Settings
from crowdgauge.providers.demo import DemoProvider
from crowdgauge.providers.serpapi import SEARCH_URL, SerpApiProvider
from crowdgauge.texts import TEXTS, normalise_language, text


@pytest.fixture
def client():
    return TestClient(create_app(Settings(provider="demo", cache_ttl=0)))


@pytest.mark.parametrize(
    ("tag", "expected"),
    [("de", "de"), ("de-CH", "de"), ("DE", "de"), ("en", "en"), ("fr", "en"), ("", "en")],
)
def test_language_tags_are_reduced_to_a_supported_code(tag, expected):
    assert normalise_language(tag) == expected


def test_none_falls_back_to_english():
    assert normalise_language(None) == "en"


def test_every_text_key_exists_in_both_languages():
    missing = [key for key, entry in TEXTS.items() if set(entry) != {"en", "de"}]
    assert missing == []


def test_unknown_key_raises_instead_of_returning_a_placeholder():
    with pytest.raises(KeyError):
        text("no_such_key", "en")


async def test_demo_notes_follow_the_requested_language():
    german = await DemoProvider(language="de").fetch_report(
        (await DemoProvider(language="de").search_venues("Testcafe"))[0]
    )
    assert "Synthetische Beispieldaten" in german.attribution
    assert any("keine Messung" in note for note in german.notes)


async def test_demo_visit_duration_needs_no_translation():
    provider = DemoProvider(language="de")
    report = await provider.fetch_report((await provider.search_venues("Testcafe"))[0])
    # A bare duration reads correctly next to either language's label.
    assert report.typical_visit_duration == "45 min"


def test_api_returns_german_notes_when_asked(client):
    payload = client.get("/api/busyness", params={"q": "Testcafe", "lang": "de"}).json()
    assert "Synthetische" in payload["report"]["attribution"]


def test_api_defaults_to_english(client):
    payload = client.get("/api/busyness", params={"q": "Testcafe"}).json()
    assert "Synthetic" in payload["report"]["attribution"]


def test_provider_sources_are_localised(client):
    german = client.get("/api/providers", params={"lang": "de"}).json()["providers"]
    assert "Stosszeiten" in german[0]["source"]


@respx.mock
async def test_serpapi_passes_the_language_upstream():
    """Google localises its own busyness captions via the hl parameter."""
    route = respx.get(SEARCH_URL).mock(
        return_value=httpx.Response(
            200, json={"local_results": [{"place_id": "x", "title": "Cafe"}]}
        )
    )
    await SerpApiProvider(api_key="k", language="de").search_venues("Cafe")
    assert route.calls.last.request.url.params["hl"] == "de"


def test_cache_separates_languages(client):
    english = client.get("/api/busyness", params={"q": "Same Place"}).json()
    german = client.get("/api/busyness", params={"q": "Same Place", "lang": "de"}).json()
    assert english["report"]["attribution"] != german["report"]["attribution"]
    assert english["report"]["days"] == german["report"]["days"]
