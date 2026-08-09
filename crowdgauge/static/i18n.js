/* Interface strings. English is the default, German is offered as an option,
   and the initial choice follows the browser language instead of being fixed.

   Wrapped in an IIFE: a top level const in a classic script lands in the global
   scope, where it collides with the name app.js destructures out of the exported
   object. */

(function () {
const TRANSLATIONS = {
  en: {
    tagline:
      "How busy a place usually is, hour by hour, plus the live value when the data source provides one.",
    language: "Language",
    queryLabel: "Location",
    queryPlaceholder: "Venue name, city",
    queryHint: "Add the city or street, that is what the providers geocode against.",
    providerLabel: "Data source",
    submit: "Look up",
    submitBusy: "Looking up",
    weekTitle: "Typical week",
    weekSubtitle:
      "Share of this venue's own peak. 100 percent means as busy as it ever gets, it is not a head count.",
    daySubtitle: "Hour by hour for the selected day.",
    legendQuiet: "quiet",
    legendBusy: "busy",
    legendNoData: "no data",
    tableToggle: "Show the numbers as a table",
    tableCaption: "Busyness in percent of peak, by weekday and hour.",
    notesTitle: "What these numbers are",
    liveLabel: "Right now",
    liveNone: "No live value",
    liveNoneNote: "This source published no live reading for this venue.",
    vsTypical: "vs typical",
    peakLabel: "Weekly peak",
    quietLabel: "Quietest open slot",
    durationLabel: "Typical visit",
    durationUnknown: "Not reported",
    noForecastTitle: "No footfall data",
    noForecast: "The provider has no busyness curve for this venue.",
    errorTitle: "Lookup failed",
    setupTitle: "Running on synthetic demo data",
    setupBody:
      "No provider key is configured, so the numbers below are generated locally and describe no real venue. Add a key in .env to query real data.",
    hourAt: "at",
    percentOfPeak: "% of peak",
    noData: "no data",
    day: "Day",
    weekdays: ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
    weekdaysShort: ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
    providerConfigured: "ready",
    providerMissing: "no key",
    footerSource: "Source",
    peoplePerHour: "people per hour",
    weekSubtitleCounts:
      "Measured people per hour, shown as a share of this spot's own weekly peak.",
    openDataTitle: "Running on open data",
    openDataBody:
      "No provider key is configured, so the active source is public pedestrian counting stations. These are real measurements, but they only cover the cities listed in the data source selector. For any venue worldwide, get your own free key and put it in .env:",
    keyLinksIntro: "Where to get a key:",
  },
  de: {
    tagline:
      "Wie voll ein Ort üblicherweise ist, Stunde für Stunde, plus Live-Wert, falls die Datenquelle einen liefert.",
    language: "Sprache",
    queryLabel: "Standort",
    queryPlaceholder: "Name des Orts, Stadt",
    queryHint: "Stadt oder Strasse ergänzen, darauf geocodieren die Anbieter.",
    providerLabel: "Datenquelle",
    submit: "Abfragen",
    submitBusy: "Frage ab",
    weekTitle: "Typische Woche",
    weekSubtitle:
      "Anteil am eigenen Spitzenwert dieses Orts. 100 Prozent heisst so voll wie hier überhaupt je, es ist keine Personenzahl.",
    daySubtitle: "Stunde für Stunde für den gewählten Tag.",
    legendQuiet: "ruhig",
    legendBusy: "voll",
    legendNoData: "keine Daten",
    tableToggle: "Zahlen als Tabelle anzeigen",
    tableCaption: "Auslastung in Prozent des Spitzenwerts, nach Wochentag und Stunde.",
    notesTitle: "Was diese Zahlen sind",
    liveLabel: "Jetzt",
    liveNone: "Kein Live-Wert",
    liveNoneNote: "Diese Quelle hat für diesen Ort keinen Live-Wert veröffentlicht.",
    vsTypical: "gegenüber üblich",
    peakLabel: "Wochen-Spitze",
    quietLabel: "Ruhigste offene Stunde",
    durationLabel: "Typischer Aufenthalt",
    durationUnknown: "Nicht ausgewiesen",
    noForecastTitle: "Keine Auslastungsdaten",
    noForecast: "Der Anbieter hat für diesen Ort keine Auslastungskurve.",
    errorTitle: "Abfrage fehlgeschlagen",
    setupTitle: "Läuft mit synthetischen Demo-Daten",
    setupBody:
      "Es ist kein Anbieter-Key konfiguriert, die Zahlen unten sind lokal erzeugt und beschreiben keinen echten Ort. Für echte Daten einen Key in .env eintragen.",
    hourAt: "um",
    percentOfPeak: "% der Spitze",
    noData: "keine Daten",
    day: "Tag",
    weekdays: ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"],
    weekdaysShort: ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"],
    providerConfigured: "bereit",
    providerMissing: "kein Key",
    footerSource: "Quelle",
    peoplePerHour: "Personen pro Stunde",
    weekSubtitleCounts:
      "Gemessene Personen pro Stunde, dargestellt als Anteil am Wochen-Spitzenwert dieses Orts.",
    openDataTitle: "Läuft mit Open Data",
    openDataBody:
      "Es ist kein Anbieter-Key konfiguriert, aktive Quelle sind darum öffentliche Passantenzählstellen. Das sind echte Messwerte, sie decken aber nur die in der Quellenauswahl genannten Städte ab. Für beliebige Orte weltweit einen eigenen Gratis-Key holen und in .env eintragen:",
    keyLinksIntro: "Wo es einen Key gibt:",
  },
};

const STORAGE_KEY = "crowdgauge.language";

function detectLanguage() {
  const stored = window.localStorage.getItem(STORAGE_KEY);
  if (stored && TRANSLATIONS[stored]) {
    return stored;
  }
  const preferred = (navigator.languages || [navigator.language || "en"])
    .map((tag) => String(tag).slice(0, 2).toLowerCase())
    .find((code) => TRANSLATIONS[code]);
  return preferred || "en";
}

function rememberLanguage(code) {
  window.localStorage.setItem(STORAGE_KEY, code);
}

window.CrowdGaugeI18n = { TRANSLATIONS, detectLanguage, rememberLanguage };
})();
