# Contributing

Thanks for looking. I maintain this project on my own, so the process is deliberately light.

## Before You Start

For anything larger than a bug fix, open an issue first. It saves us both from a pull request that
turns out to point somewhere I do not want the project to go. `ROADMAP.md` lists what is planned and,
just as usefully, what is deliberately out of scope.

## Development Setup

```bash
git clone https://github.com/9t29zhmwdh-coder/CrowdGauge.git
cd CrowdGauge
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

## Before You Open a Pull Request

```bash
ruff check .
ruff format --check .
pytest tests/ --cov=crowdgauge
```

All three have to pass, the same three run in CI.

## Adding a Data Provider

This is the most likely useful contribution. `ARCHITECTURE.md` has the step by step list. Two things
I will look at closely:

- **Tests against recorded response shapes.** Use `respx`, do not call the live API in a test.
- **No credentials in error messages.** The base class handles this if you use `_get_json` and
  `_post_json`. If you write your own request code, you own that guarantee.

A provider that scrapes a service against its terms of use will not be merged, regardless of how
well it works.

## Code Style

- Functions stay short, roughly 20 lines as an upper bound
- Comments explain why, not what
- Names say what they mean, no `data`, no `tmp`
- Commits follow `type(scope): description`, for example `feat(providers): add foursquare adapter`

## Reporting Bugs

Include the provider you used, what you searched for, what you expected and what you got. If the
lookup failed, the exact error message from the interface or the terminal is the most useful thing
you can attach. Never paste an API key into an issue.
