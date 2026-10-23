# Security policy

Version 0.1.x receives best-effort security fixes. This is an alpha project, not a hosted service.

Do not publish credentials, customer records, exploit payloads containing private data,
or vulnerabilities in a public issue. Use GitHub's **Report a vulnerability** button
on the Security tab when available. If unavailable, open an issue requesting a private
reporting channel without disclosing the vulnerability. No response SLA is promised.

## Boundaries

Tools validate inputs and return data. They do not execute shell commands, publish
content, send messages, or write to arbitrary paths. CLI exports use fixed filenames.
Source excerpts, HTML and model output are untrusted data, never instructions.
The agent has a bounded tool loop; human review is required before using its advice.

The MCP server defaults to local stdio. HTTP binds to 127.0.0.1 and has DNS-rebinding
protection. It has **no application authentication**. Do not expose it directly to
the internet. A production ChatGPT integration needs a TLS gateway, authentication,
rate/body limits, tenant isolation, and retention controls. These are deployment
requirements, not features claimed by this repository.

OpenAI requests use store=False. Provider retention is governed by your account
terms; this flag is not a zero-retention guarantee. API calls transmit the task and
tool results to OpenAI. Use synthetic or approved data and never put secrets in prompts.
Report artifacts can contain supplied business information. Keep them out of Git.

## Verification

Run pytest, ruff and pip-audit as described in CONTRIBUTING.md. Dependency scanning
cannot establish that an application is secure. Review changes to tool permissions,
network access, input bounds and report escaping explicitly.
