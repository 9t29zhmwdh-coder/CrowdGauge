<div align="center">
  <img src="RayStudio.png" alt="RayStudio Logo" width="120"/>
  <h1>CrowdGauge</h1>
</div>

[🇬🇧 English Version](README.md)

**Wie voll ein Ort üblicherweise ist, Stunde für Stunde. Python, FastAPI, austauschbare Datenquellen.**

CrowdGauge nimmt einen Standort, fragt bei einem Anbieter für Besucherfrequenz nach, wie voll dieser
Ort über die Woche typischerweise ist, und zeigt das Ergebnis als Heatmap plus Live-Wert, sofern die
Quelle einen liefert. Die Datenquelle ist ein Adapter, dieselbe Oberfläche funktioniert also mit
Google-basierten Daten, mit einem unabhängigen Handysignal-Panel oder mit einer synthetischen
Demo-Quelle, die gar keinen API-Key braucht.

[![CI](https://github.com/9t29zhmwdh-coder/CrowdGauge/actions/workflows/ci.yml/badge.svg)](https://github.com/9t29zhmwdh-coder/CrowdGauge/actions/workflows/ci.yml) [![CodeQL](https://github.com/9t29zhmwdh-coder/CrowdGauge/actions/workflows/github-code-scanning/codeql/badge.svg)](https://github.com/9t29zhmwdh-coder/CrowdGauge/actions/workflows/github-code-scanning/codeql) [![OpenSSF Scorecard](https://api.scorecard.dev/projects/github.com/9t29zhmwdh-coder/CrowdGauge/badge)](https://scorecard.dev/viewer/?uri=github.com/9t29zhmwdh-coder/CrowdGauge)
![Platform](https://img.shields.io/badge/platform-macOS%20%7C%20Linux%20%7C%20Windows-lightgrey) ![Python](https://img.shields.io/badge/Python-3.11%2B-orange?logo=python&logoColor=white) ![FastAPI](https://img.shields.io/badge/FastAPI-0.111%2B-blue?logo=fastapi&logoColor=white) ![AI | Claude Code](https://img.shields.io/badge/AI-Claude%20Code-black)

> **Wie es läuft:** ein lokaler Webserver auf `http://127.0.0.1:8734`, gestartet mit
> `crowdgauge serve`. Kein Hintergrunddienst, kein Konto, keine Telemetrie. Zusätzlich gibt es einen
> CLI-Modus, der die Woche direkt ins Terminal schreibt.

![CrowdGauge](docs/screenshot.png)

---

**In der Praxis:** du tippst einen Ort ein, zum Beispiel ein Fitnessstudio oder einen Supermarkt,
und siehst auf einen Blick, wann es dort ruhig und wann es voll ist. Hat die Datenquelle einen
Live-Wert, siehst du zusätzlich, wie voll es gerade im Vergleich zu einem normalen Moment dieser
Woche ist. Das reicht für die Entscheidung, ob du jetzt hingehst oder in zwei Stunden.

## Was die Zahlen bedeuten

Auslastung ist ein **Anteil am eigenen Spitzenwert des Orts**. 100 heisst so voll wie hier überhaupt
je, 40 heisst deutlich ruhiger als das eigene Maximum. Es ist keine Personenzahl und lässt sich auch
nicht in eine umrechnen. Eine gut besuchte Quartierbäckerei und ein halb leeres Stadion können beide
80 anzeigen.

## Datenquellen

Weder Google noch Apple geben diese Daten über ihre offiziellen APIs heraus. Google zeigt die
Stosszeiten nur in der Maps-Oberfläche, der Feature-Request zur Freigabe liegt seit 2017 offen
([issuetracker.google.com/issues/35827550](https://issuetracker.google.com/issues/35827550)). Apple
Maps hat gar kein entsprechendes Feld. CrowdGauge spricht deshalb mit Anbietern, welche die Daten
selbst lizenzieren oder messen, statt irgendwo zu scrapen.

| Anbieter | Datenherkunft | Live-Wert | Kosten zum Zeitpunkt der Erstellung |
|----------|---------------|-----------|--------------------------------------|
| `serpapi` | Google-Maps-Stosszeiten, unter der Lizenz von SerpApi weitergegeben | ja | 250 Abfragen pro Monat gratis, danach ab 25 USD |
| `besttime` | Unabhängiges Panel anonymisierter Handysignale, 150+ Länder | ja | credit-basiert, Gratis-Kontingent vorhanden |
| `demo` | Lokal erzeugte synthetische Kurven, kein Netzwerkzugriff | ja | gratis, immer verfügbar |

Ohne konfigurierten Key läuft die Demo-Quelle, und jeder daraus erzeugte Bericht ist in der
Oberfläche und in der API-Antwort als synthetisch gekennzeichnet.

## Funktionen

- Wochen-Heatmap über 7 Tage und 24 Stunden, die aktuelle Stunde ist markiert
- Live-Auslastung inklusive Abweichung von dem, was für diese Stunde üblich ist
- Ruhigste und vollste Zeitfenster der Woche, berechnet statt geschätzt
- Anbieter-Abstraktion: ein Adapter pro Quelle, pro Abfrage wählbar
- JSON-API neben der Oberfläche, damit die Daten andere Tools speisen können
- Terminal-Modus mit Sparklines, nutzbar über SSH
- Oberfläche auf Englisch und Deutsch, folgt der Browsersprache
- Prognosen werden im Arbeitsspeicher zwischengespeichert, Live-Werte immer frisch geholt, das hält
  den Credit-Verbrauch berechenbar

## Voraussetzungen

- Python 3.11 oder neuer
- Ein API-Key für `serpapi` oder `besttime`, optional; ohne Key läuft die Demo-Quelle

## Schnellstart

```bash
git clone https://github.com/9t29zhmwdh-coder/CrowdGauge.git
cd CrowdGauge
python3 -m venv .venv && source .venv/bin/activate
pip install -e .

# Optional: Anbieter-Key hinterlegen
cp .env.example .env
# danach .env bearbeiten

crowdgauge serve
```

Danach `http://127.0.0.1:8734` öffnen.

Terminal-Modus:

```bash
crowdgauge lookup "Bahnhof, Zürich"
crowdgauge providers
```

## JSON-API

| Endpunkt | Zweck |
|----------|-------|
| `GET /api/health` | Version und aktuell aktive Datenquelle |
| `GET /api/providers` | Welche Anbieter existieren und welche Zugangsdaten haben |
| `GET /api/search?q=` | Treffer-Kandidaten zu einer Suche |
| `GET /api/busyness?q=` | Vollständiger Bericht zum ersten Treffer |
| `GET /api/venues/{id}/busyness` | Bericht zu einem aus der Suche gewählten Ort |

Jeder Endpunkt akzeptiert zusätzlich den Parameter `provider`. Die interaktive Dokumentation liegt
unter `/docs`, solange der Server läuft.

## Konfiguration

Alle Einstellungen sind Umgebungsvariablen mit dem Präfix `CROWDGAUGE_` und können in einer
`.env`-Datei neben dem Projekt liegen. Die vollständige Liste steht in `.env.example`. Keys werden
nur in den Arbeitsspeicher gelesen, von der Anwendung nie auf die Festplatte geschrieben und nie in
eine API-Antwort oder eine Fehlermeldung aufgenommen.

## Deinstallation / Aufräumen

```bash
pip uninstall crowdgauge
```

CrowdGauge schreibt keine Dateien ausserhalb des eigenen Verzeichnisses: keine Datenbank, keine
Konfiguration im Benutzerordner, kein Cache auf der Festplatte. Der Prognose-Cache liegt im
Arbeitsspeicher und verschwindet mit dem Serverstopp. Falls du eine `.env` angelegt hast, entfernt
das Löschen dieser Datei die API-Keys. Wer das Repository geklont hat, löscht mit dem Ordner den
Rest.

## Dokumentation

- [ARCHITECTURE.md](ARCHITECTURE.md), wie die Schichten zusammenspielen und wie eine Quelle dazukommt
- [SECURITY.md](SECURITY.md), Meldung von Schwachstellen und die Supply-Chain-Baseline
- [PRIVACY.md](PRIVACY.md), was den Rechner verlässt und was nicht
- [ROADMAP.md](ROADMAP.md), was geplant ist und was bewusst draussen bleibt
- [CHANGELOG.md](CHANGELOG.md), Versionsverlauf

---

**Autor:** [Rafael Yilmaz](https://github.com/9t29zhmwdh-coder) · **Status:** Early Release · ![version](https://img.shields.io/github/v/release/9t29zhmwdh-coder/CrowdGauge?color=6b7280&style=flat-square) · **Lizenz:** MIT
