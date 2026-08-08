<div align="center">
  <img src="RayStudio.png" alt="RayStudio Logo" width="120"/>
  <h1>CrowdGauge</h1>
</div>

[🇩🇪 Deutsche Version](README.de.md)

**How busy a place usually is, hour by hour. Python, FastAPI, swappable footfall providers.**

CrowdGauge takes a location, asks a footfall data provider how busy that venue typically is across
the week, and shows the result as a heatmap plus a live value where the source offers one. The
provider is an adapter, so the same interface works with Google based data, with an independent
phone signal panel, or with a synthetic demo source that needs no API key at all.

[![CI](https://github.com/9t29zhmwdh-coder/CrowdGauge/actions/workflows/ci.yml/badge.svg)](https://github.com/9t29zhmwdh-coder/CrowdGauge/actions/workflows/ci.yml) [![CodeQL](https://github.com/9t29zhmwdh-coder/CrowdGauge/actions/workflows/github-code-scanning/codeql/badge.svg)](https://github.com/9t29zhmwdh-coder/CrowdGauge/actions/workflows/github-code-scanning/codeql) [![OpenSSF Scorecard](https://api.scorecard.dev/projects/github.com/9t29zhmwdh-coder/CrowdGauge/badge)](https://scorecard.dev/viewer/?uri=github.com/9t29zhmwdh-coder/CrowdGauge)
![Platform](https://img.shields.io/badge/platform-macOS%20%7C%20Linux%20%7C%20Windows-lightgrey) ![Python](https://img.shields.io/badge/Python-3.11%2B-orange?logo=python&logoColor=white) ![FastAPI](https://img.shields.io/badge/FastAPI-0.111%2B-blue?logo=fastapi&logoColor=white) ![AI | Claude Code](https://img.shields.io/badge/AI-Claude%20Code-black)

> **How it runs:** a local web server on `http://127.0.0.1:8734`, started with `crowdgauge serve`.
> No background service, no account, no telemetry. There is also a CLI mode that prints the week
> straight into the terminal.

![CrowdGauge](docs/screenshot.png)

---

**In practice:** you type a place, for example a gym or a supermarket, and you see at a glance when
it is quiet and when it is packed. If the data source has a live reading, you also see how busy it
is right now compared to a normal moment of that week. That is enough to decide whether to go now
or in two hours.

## What the numbers mean

Busyness is a **share of that venue's own peak**. 100 means as busy as this place ever gets, 40
means clearly quieter than its own maximum. It is not a head count, and it cannot be converted into
one. A busy corner bakery and a half empty stadium can both read 80.

## Data sources

Neither Google nor Apple exposes this data through their official APIs. Google shows popular times
only in the Maps interface, and the feature request to expose it has been open since 2017
([issuetracker.google.com/issues/35827550](https://issuetracker.google.com/issues/35827550)). Apple
Maps has no equivalent field at all. CrowdGauge therefore talks to providers that license or measure
the data themselves, instead of scraping anyone.

| Provider | Data origin | Live value | Cost at the time of writing |
|----------|-------------|-----------|------------------------------|
| `serpapi` | Google Maps popular times, relayed under SerpApi's licence | yes | 250 searches per month free, then from 25 USD |
| `besttime` | Independent panel of anonymised phone signals, 150+ countries | yes | credit based, free tier available |
| `demo` | Synthetic curves generated locally, no network access | yes | free, always available |

The demo provider is the default when no key is configured, and every report it produces is labelled
as synthetic in the interface and in the API response.

## Features

- Weekly heatmap of 7 days by 24 hours, with the current hour marked
- Live busyness including the difference to what is typical for that hour
- Quietest and busiest slots of the week, computed rather than eyeballed
- Provider abstraction: one adapter per source, selectable per request
- JSON API alongside the interface, so the data can feed other tools
- Terminal mode with sparklines, for use over SSH
- Interface in English and German, following the browser language
- Forecast responses cached in memory, live values always fetched fresh, which keeps provider
  credit use predictable

## Requirements

- Python 3.11 or newer
- An API key for `serpapi` or `besttime`, optional; without one the demo provider runs

## Quick Start

```bash
git clone https://github.com/9t29zhmwdh-coder/CrowdGauge.git
cd CrowdGauge
python3 -m venv .venv && source .venv/bin/activate
pip install -e .

# Optional: add a provider key
cp .env.example .env
# then edit .env

crowdgauge serve
```

Then open `http://127.0.0.1:8734`.

Terminal mode:

```bash
crowdgauge lookup "Central Station, Zurich"
crowdgauge providers
```

## JSON API

| Endpoint | Purpose |
|----------|---------|
| `GET /api/health` | Version and the currently active provider |
| `GET /api/providers` | Which providers exist and which ones have credentials |
| `GET /api/search?q=` | Candidate venues for a query |
| `GET /api/busyness?q=` | Full report for the first matching venue |
| `GET /api/venues/{id}/busyness` | Report for a venue picked from a search result |

Every endpoint accepts an optional `provider` parameter. Interactive documentation is available at
`/docs` while the server runs.

## Configuration

All settings are environment variables with the prefix `CROWDGAUGE_`, and they can live in a `.env`
file next to the project. See `.env.example` for the full list. Keys are read into memory only,
never written to disk by the application and never included in an API response or an error message.

## Uninstall / Cleanup

```bash
pip uninstall crowdgauge
```

CrowdGauge writes no files outside its own directory: no database, no config in your home folder,
no cache on disk. The forecast cache lives in memory and disappears when the server stops. If you
created a `.env`, delete it to remove the API keys. If you cloned the repository, deleting the
folder removes everything that is left.

## Documentation

- [ARCHITECTURE.md](ARCHITECTURE.md), how the layers fit together and how to add a provider
- [SECURITY.md](SECURITY.md), reporting a vulnerability and the supply chain baseline
- [PRIVACY.md](PRIVACY.md), what leaves your machine and what does not
- [ROADMAP.md](ROADMAP.md), what is planned and what is deliberately out of scope
- [CHANGELOG.md](CHANGELOG.md), version history

---

**Author:** [Rafael Yilmaz](https://github.com/9t29zhmwdh-coder) · **Status:** Early Release · ![version](https://img.shields.io/github/v/release/9t29zhmwdh-coder/CrowdGauge?color=6b7280&style=flat-square) · **License:** MIT
