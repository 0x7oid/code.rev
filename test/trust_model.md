# Trust Model - acme_notes

## Overview
acme_notes is a public-facing HTTP service. All Flask route handlers are
reachable by **unauthenticated, anonymous internet users**.

## Trust boundaries
- **Untrusted:** every value read from `request.args`, `request.data`,
  query strings, and request bodies. Treat all of it as attacker-controlled.
- **Trusted:** values hardcoded in source and the local SQLite file on disk.

## Sensitive assets
- The user table in `app.db` (PII).
- The host operating system / shell.
- Any secrets embedded in the codebase.

## Assumptions
- The service runs in production on an internet-facing host.
- There is no WAF or input-sanitisation proxy in front of the app.
