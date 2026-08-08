"""Tests for the HTTP layer, driven through the demo provider."""

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from crowdgauge.app import create_app
from crowdgauge.config import Settings


@pytest.fixture
def client():
    settings = Settings(provider="demo", cache_ttl=0)
    return TestClient(create_app(settings))


def test_health_reports_the_active_provider(client):
    payload = client.get("/api/health").json()
    assert payload["status"] == "ok"
    assert payload["active_provider"] == "demo"


def test_providers_endpoint_lists_all_sources_without_leaking_keys(client):
    payload = client.get("/api/providers").json()
    names = [entry["name"] for entry in payload["providers"]]
    assert names == ["serpapi", "besttime", "demo"]
    assert "key" not in str(payload).lower().replace("no key", "")


def test_busyness_returns_a_full_week_with_insights(client):
    payload = client.get("/api/busyness", params={"q": "Test Cafe, Aarau"}).json()
    report = payload["report"]
    assert len(report["days"]) == 7
    assert all(len(day["hours"]) == 24 for day in report["days"])
    assert payload["insights"]["has_forecast"] is True
    assert payload["insights"]["busiest"][0]["score"] >= payload["insights"]["quietest"][0]["score"]


def test_demo_reports_are_labelled_as_synthetic(client):
    report = client.get("/api/busyness", params={"q": "Test Cafe"}).json()["report"]
    assert "Synthetic" in report["attribution"]
    assert any("Synthetic" in note for note in report["notes"])


def test_search_returns_candidates(client):
    payload = client.get("/api/search", params={"q": "Test Cafe, Aarau"}).json()
    assert payload["provider"] == "demo"
    assert payload["venues"][0]["name"] == "Test Cafe"


def test_demo_results_are_stable_for_the_same_venue(client):
    first = client.get("/api/busyness", params={"q": "Same Place"}).json()["report"]
    second = client.get("/api/busyness", params={"q": "Same Place"}).json()["report"]
    assert first["days"] == second["days"]


@pytest.mark.parametrize("query", ["", "x"])
def test_too_short_queries_are_rejected(client, query):
    assert client.get("/api/busyness", params={"q": query}).status_code == 422


def test_unknown_provider_is_rejected(client):
    response = client.get("/api/busyness", params={"q": "Test Cafe", "provider": "gossip"})
    assert response.status_code == 400


def test_requesting_an_unconfigured_provider_explains_what_is_missing(client):
    response = client.get("/api/busyness", params={"q": "Test Cafe", "provider": "serpapi"})
    assert response.status_code == 503
    assert "CROWDGAUGE_SERPAPI_KEY" in response.json()["detail"]


def test_configured_provider_takes_precedence_over_demo():
    settings = Settings(provider="auto", serpapi_key=SecretStr("configured"))
    assert settings.configured_providers()[0] == "serpapi"


def test_blank_key_counts_as_missing():
    settings = Settings(provider="auto", serpapi_key=SecretStr("   "))
    assert settings.has_serpapi() is False
    assert settings.configured_providers()[0] == "demo"


def test_interface_is_served_at_the_root(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "CrowdGauge" in response.text
