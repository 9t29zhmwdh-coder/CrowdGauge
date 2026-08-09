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
    "attribution_opendata": {
        "en": "Measured pedestrian counts from open government data",
        "de": "Gemessene Passantenzahlen aus Open Government Data",
    },
    "source_opendata": {
        "en": "Public pedestrian counting stations, no API key needed",
        "de": "Öffentliche Passantenzählstellen, kein API-Key nötig",
    },
    "note_counting_station": {
        "en": (
            "Measured head counts at a public counting station, so this is how busy the spot is, "
            "not how full a venue is."
        ),
        "de": (
            "Gemessene Personenzahlen an einer öffentlichen Zählstelle, das beschreibt also die "
            "Frequenz am Ort, nicht die Auslastung eines Lokals."
        ),
    },
    "note_open_licence": {
        "en": "Published under an open licence by {city}.",
        "de": "Unter offener Lizenz veröffentlicht von {city}.",
    },
    "note_history_window": {
        "en": "Hourly average over the last {weeks} weeks.",
        "de": "Stundenmittel über die letzten {weeks} Wochen.",
    },
    "note_reading_too_old": {
        "en": (
            "No live value: this station publishes in batches, its newest reading is from "
            "{timestamp}."
        ),
        "de": (
            "Kein Live-Wert: diese Zählstelle publiziert schubweise, der jüngste Messwert "
            "stammt vom {timestamp}."
        ),
    },
    "note_no_reading": {
        "en": "No live value: the station returned no recent reading.",
        "de": "Kein Live-Wert: die Zählstelle lieferte keinen aktuellen Messwert.",
    },
    "live_measured_people": {
        "en": "{count} people counted in that hour",
        "de": "{count} Personen in dieser Stunde gezählt",
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
    "cli_week_title": {
        "en": "Busyness as share of this place's peak",
        "de": "Auslastung als Anteil am Spitzenwert dieses Orts",
    },
    "cli_day": {"en": "Day", "de": "Tag"},
    "cli_hours": {"en": "00 to 23", "de": "00 bis 23"},
    "cli_peak": {"en": "Peak", "de": "Spitze"},
    "cli_no_data": {"en": "no data", "de": "keine Daten"},
    "cli_at": {"en": "at", "de": "um"},
    "cli_right_now": {"en": "Right now", "de": "Jetzt"},
    "cli_of_peak": {"en": "of peak", "de": "der Spitze"},
    "cli_vs_typical": {"en": "vs typical", "de": "gegenüber üblich"},
    "cli_quietest": {"en": "Quietest open slots", "de": "Ruhigste offene Zeiten"},
    "cli_people_per_hour": {"en": "people per hour", "de": "Personen pro Stunde"},
    "cli_providers": {"en": "Data providers", "de": "Datenquellen"},
    "cli_provider": {"en": "Provider", "de": "Anbieter"},
    "cli_configured": {"en": "Configured", "de": "Konfiguriert"},
    "cli_source": {"en": "Source", "de": "Quelle"},
    "cli_yes": {"en": "yes", "de": "ja"},
    "cli_no": {"en": "no", "de": "nein"},
    "cli_weekdays_short": {
        "en": "Mon,Tue,Wed,Thu,Fri,Sat,Sun",
        "de": "Mo,Di,Mi,Do,Fr,Sa,So",
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
