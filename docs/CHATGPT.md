# ChatGPT and OpenAI integration

## Local MCP client (including Codex)

Install the project into a virtual environment. Configure a stdio MCP client with
command `/absolute/path/.venv/bin/search-evidence-mcp` and arguments `["serve"]`.
Use the client's tool-discovery UI to inspect schemas before approving access.
Each tool accepts one `payload` object. `examples/demo.json` is a working payload.
No API key is needed for deterministic MCP tools.

## ChatGPT custom MCP connection

Run `search-evidence-mcp serve --transport streamable-http`. The endpoint is
`http://127.0.0.1:8765/mcp`, accessible locally only. For a short synthetic-data demo,
use the supported ChatGPT tunnel workflow. For a production connection, deploy behind
an authenticated TLS gateway with rate limits and tenant controls. This repository
does not implement an OAuth authorization server and is not production-hosted for you.
In ChatGPT's custom MCP connection flow, supply your reachable endpoint and configure
authentication. Availability depends on your ChatGPT plan and workspace settings.

Official guides:
- https://developers.openai.com/api/docs/guides/custom-mcp-server
- https://developers.openai.com/plugins/build/app-quickstart

## OpenAI agent runner

Set OPENAI_API_KEY and OPENAI_MODEL in your environment. Then run:

```sh
search-evidence-mcp agent examples/task.txt --out output/agent
```

This calls OpenAI's Responses API with validated function tools. It caps turns,
per-turn calls, prompt size, response tokens and tool-result size. It never executes
shell commands or publishes content. Input and results are sent to OpenAI. `store=False`
is set, but does not override account retention terms. No model subscription or API
credits are bundled. Tests use a fake client; a live model run is a separate check.
