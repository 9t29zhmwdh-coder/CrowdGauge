"""Localised strings that originate in the backend.

Attribution lines and provider notes are shown verbatim in the interface, so
they have to follow the interface language rather than being fixed English. The
interface passes its language down with every request, the providers use it both
here and as the upstream language parameter.
"""

DEFAULT_LANGUAGE = "en"
SUPPORTED_LANGUAGES = ("en", "de")

TEXTS: dict[str, dict[str, str]] = {
    "attribution_serpapi": {
        "en": "Popular times data from Google Maps, retrieved via SerpApi",
        "de": "Stosszeiten-Daten von Google Maps, abgerufen über SerpApi",
    },
    "attribution_besttime": {
        "en": "Footfall data from BestTime.app, based on anonymised phone signals",
        "de": "Frequenzdaten von BestTime.app, basierend auf anonymisierten Handysignalen",
    },
    "attribution_demo": {
        "en": "Synthetic sample data, generated locally by CrowdGauge",
        "de": "Synthetische Beispieldaten, lokal von CrowdGauge erzeugt",
    },
    "note_share_of_peak": {
        "en": "Scores are a share of this venue's own peak, not a head count.",
        "de": "Die Werte sind ein Anteil am eigenen Spitzenwert des Orts, keine Personenzahl.",
    },
    "note_google_origin": {
        "en": "Derived from aggregated Google Location History of users who opted in.",
        "de": "Abgeleitet aus dem aggregierten Standortverlauf zustimmender Google-Nutzer.",
    },
    "note_no_live_value": {
        "en": "Google published no live value for this venue at request time.",
        "de": "Google hat zum Abfragezeitpunkt keinen Live-Wert für diesen Ort veröffentlicht.",
    },
    "note_panel_origin": {
        "en": "Panel based estimate from anonymised phone signals, independent of Google.",
        "de": "Panel-Schätzung aus anonymisierten Handysignalen, unabhängig von Google.",
    },
    "note_day_starts_at_six": {
        "en": (
            "BestTime reports a venue day from 06:00, hours after midnight are shown on the "
            "following calendar day."
        ),
        "de": (
            "BestTime rechnet den Tag eines Orts ab 06:00, Stunden nach Mitternacht erscheinen "
            "am folgenden Kalendertag."
        ),
    },
    "note_demo_synthetic": {
        "en": "Synthetic sample data, not a measurement of any real venue.",
        "de": "Synthetische Beispieldaten, keine Messung eines echten Orts.",
    },
    "note_demo_archetype": {
        "en": "Shape modelled after a typical {archetype} week.",
        "de": "Verlauf nachgebildet nach einer typischen {archetype}-Woche.",
    },
    "note_demo_add_key": {
        "en": "Set a provider API key in .env to query real footfall data.",
        "de": "Für echte Frequenzdaten einen Anbieter-Key in .env eintragen.",
    },
    "source_serpapi": {
        "en": "Google Maps popular times, relayed by SerpApi",
        "de": "Google-Maps-Stosszeiten, weitergegeben durch SerpApi",
    },
    "source_besttime": {
        "en": "Independent panel of anonymised phone signals",
        "de": "Unabhängiges Panel anonymisierter Handysignale",
    },
    "source_demo": {
        "en": "Synthetic data generated locally, no network access",
        "de": "Lokal erzeugte synthetische Daten, kein Netzwerkzugriff",
    },
    "archetype_restaurant": {"en": "restaurant", "de": "Restaurant"},
    "archetype_cafe": {"en": "cafe", "de": "Café"},
    "archetype_gym": {"en": "gym", "de": "Fitnessstudio"},
    "archetype_store": {"en": "store", "de": "Ladengeschäft"},
}


def normalise_language(language: str | None) -> str:
    """Reduce a browser language tag to a code the providers understand.

    Google returns its own busyness labels in this language, so passing it
    through is what keeps a German interface from showing English captions.
    """
    code = (language or DEFAULT_LANGUAGE).strip().lower()[:2]
    return code if code in SUPPORTED_LANGUAGES else DEFAULT_LANGUAGE


def text(key: str, language: str = DEFAULT_LANGUAGE, **fields: str) -> str:
    """Look up a localised string, falling back to English for unknown languages."""
    entry = TEXTS.get(key)
    if entry is None:
        raise KeyError(f"Unknown text key '{key}'.")
    template = entry.get(normalise_language(language), entry[DEFAULT_LANGUAGE])
    return template.format(**fields) if fields else template
