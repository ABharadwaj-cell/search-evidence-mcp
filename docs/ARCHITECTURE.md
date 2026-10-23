# Architecture and contracts

Pydantic input model → pure domain function → structured result → JSON/CSV/HTML/Markdown.
CLI, MCP and the Responses agent share the same registry and validation. Domain logic
is independently testable without network credentials. HTML exports escape user data;
CSV exports neutralize leading formula characters. Outputs preserve missing values
as null and include limitations. Nothing automatically edits external systems.

MCP uses the official Python SDK with typed payloads and read-only tool annotations.
The agent feeds validated tool results back into a bounded Responses loop. It is not
a recursive multi-agent swarm, browser automation system, or autonomous publisher.

Source text may contain prompt injection. It is treated as data; the agent has no
write or execution tools. Prompt-level instructions are not a complete injection
defense. Deployment authorization, request limits and human review remain necessary.
