# Validation record — 2026-10-23

Local environment: Python 3.12.14, Linux. `28` pytest tests passed.
Ruff check passed. The installed dependency environment passed pip-audit with no known
vulnerabilities after upgrading the virtual environment's pip to 26.2.2. This is a
point-in-time database check, not a security guarantee.

Tests include actual MCP stdio and local Streamable HTTP discovery/tool-call round
trips, hostile Host rejection, domain edge cases, export escaping and fake-client
Responses loop behavior. The CLI synthetic example produces four report files.

Not tested: a paid live OpenAI model call, a signed-in ChatGPT custom connection,
production TLS/OAuth infrastructure, real customer data or real-world result quality.
Python 3.11 and 3.13 are configured in GitHub Actions, but local tests used only 3.12.
Any remote CI status should be read from Actions, not inferred from this local record.

The first GitHub CI run exposed preinstalled setuptools 79.0.1 on Python 3.11
(PYSEC-2026-3447). CI now upgrades setuptools to >=83 before auditing, and the
build-system minimum matches that fixed version. The audit was not disabled.
