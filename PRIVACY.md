# Privacy Policy: CrowdGauge

## What I Collect

Nothing. CrowdGauge has no telemetry, no analytics, no crash reporting and no account system. I
never see what you look up.

## What Leaves Your Machine

Only the lookup itself, and only to the provider you selected:

| Provider | What is sent | To whom |
|----------|--------------|---------|
| `serpapi` | Your search text or a place id, plus your API key | serpapi.com |
| `besttime` | The venue name and address, plus your API key | besttime.app |
| `opendata_ch` | The station name you picked, no key, no identifier | the city's open data portal |
| `demo` | Nothing at all, it never opens a network connection | nobody |

Those providers have their own privacy policies and their own retention rules, and I have no
influence over either. The Swiss open data portals need no account, so a query there carries no
identifier of yours beyond the usual web request. If you would rather send nothing at all, the demo
provider runs entirely offline.

## What Stays on Your Machine

- API keys, in your environment or your local `.env`
- The forecast cache, in memory only, discarded when the server stops
- Your interface language choice, in the browser's local storage

CrowdGauge writes no database, no log file and no configuration in your home folder.

## Location Data

CrowdGauge does not request, read or store your device location. The place you are asking about is
typed by you, and the coordinates that come back belong to the venue, not to you.

## Third Party Data

The busyness figures themselves are aggregated and anonymised by the providers before CrowdGauge
ever sees them. They describe a place, not the people in it, and they cannot be traced back to an
individual visitor.
