"""Official MCP SDK server, local by default."""

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations
from .tools import REGISTRY


def build_server():
    server = FastMCP(
        "Search Evidence MCP", host="127.0.0.1", port=8765, stateless_http=True, json_response=True
    )
    for name, (schema, handler, description) in REGISTRY.items():
        # Factory avoids late-bound loop variables and exposes a concrete Pydantic schema.
        def bind(input_type, function):
            def invoke(payload):
                return function(payload)

            invoke.__annotations__ = {"payload": input_type, "return": dict}
            return invoke

        server.add_tool(
            bind(schema, handler),
            name=name,
            description=description,
            annotations=ToolAnnotations(
                readOnlyHint=True,
                destructiveHint=False,
                idempotentHint=True,
                openWorldHint=(name == "crawl_site"),
            ),
        )
    return server
