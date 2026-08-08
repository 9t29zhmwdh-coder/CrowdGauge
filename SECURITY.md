# Security Policy

## Reporting a Vulnerability

**Do NOT open a public GitHub issue for security vulnerabilities.**

Instead, report it via
[GitHub Security Advisory](https://github.com/9t29zhmwdh-coder/CrowdGauge/security/advisories/new)
or contact the maintainer via the GitHub profile.

Include:

- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

A response within **48 hours** is the target, and the issue will be worked on promptly.

## Handling of API Keys

- Provider keys are read from environment variables or a local `.env` file, which is listed in
  `.gitignore` and never committed.
- Keys are held as `pydantic.SecretStr`, so an accidental log or repr of the settings object prints
  a placeholder instead of the value.
- Error messages returned by the API are generated from the HTTP status code alone. The upstream
  response body, which may echo a key, is never forwarded. A test asserts this
  (`test_error_messages_never_contain_the_api_key`).
- The `/api/providers` endpoint reports only whether a key is present, never any part of its value.

## Network Exposure

- The server binds to `127.0.0.1` by default.
- No CORS headers are sent, so a third party website cannot drive the API from a user's browser.
- There is no authentication layer, because the tool is designed for local single user operation.
  Exposing it on a public interface would need an authenticating reverse proxy in front, and that is
  outside the scope of this project.

## Supply Chain Security

- All GitHub Actions used in the CI pipeline are pinned to a specific commit SHA, not a mutable tag
  or branch.
- Dependencies are declared in `pyproject.toml` with minimum versions. This is a library style
  declaration rather than a lock file, which is the documented trade off for an application:
  reproducibility is weaker, and `pip-audit` in CI is what covers known vulnerabilities.
- `pip-audit` runs in CI on every pull request.
- CodeQL default setup and Dependabot are enabled on the repository.

## Supported Versions

| Version | Supported |
|---------|-----------|
| Latest  | ✅ Yes    |
| Older   | ❌ No     |

Security fixes are only applied to the latest release.
