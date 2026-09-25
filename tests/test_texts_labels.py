from crowdgauge.config import Settings
from crowdgauge.providers.registry import provider_status


def test_provider_labels_follow_the_language():
    german = {entry["name"]: entry["label"] for entry in provider_status(Settings(), "de")}
    english = {entry["name"]: entry["label"] for entry in provider_status(Settings(), "en")}
    assert german["demo"] == "Demo (synthetisch)"
    assert english["demo"] == "Demo (synthetic)"
    assert german["opendata"].startswith("Open Data (Zählstellen): ")
    assert english["opendata"].startswith("Open data (counting stations): ")
