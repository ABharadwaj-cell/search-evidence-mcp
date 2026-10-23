import json
from types import SimpleNamespace as NS
import pytest
from search_evidence.agent import run_agent
from search_evidence.reports import deliverables, csv_cell
from search_evidence.server import build_server
from search_evidence.tools import REGISTRY


def test_export_escaping():
    files = deliverables(
        {"kind": "x", "findings": [{"value": "<script>alert(1)</script>"}, {"value": "=1+1"}]}
    )
    assert "<script>" not in files["report.html"]
    assert "&lt;script&gt;" in files["report.html"]
    assert "'=1+1" in files["report.csv"]
    assert json.loads(files["report.json"])["kind"] == "x"


@pytest.mark.parametrize("value", ["=SUM(A1)", "+1", "-1", "@x", "  =1", "\tformula"])
def test_csv_formula_guard(value):
    assert csv_cell(value).startswith("'")


async def test_mcp_schema_and_validation():
    server = build_server()
    tools = await server.list_tools()
    assert {t.name for t in tools} == set(REGISTRY)
    for tool in tools:
        assert tool.inputSchema["properties"]["payload"]
        assert tool.annotations.readOnlyHint
    with pytest.raises(Exception):
        await server.call_tool(next(iter(REGISTRY)), {"payload": {"unexpected": True}})


class Client:
    def __init__(self, outputs):
        self.outputs = iter(outputs)
        self.requests = []
        self.responses = self

    def create(self, **kwargs):
        self.requests.append(kwargs.copy())
        return next(self.outputs)


def test_agent_unknown_tool_is_returned_as_error():
    call = NS(type="function_call", name="run_shell", arguments="{}", call_id="c1")
    client = Client([NS(output=[call]), NS(output=[], output_text="Need valid data")])
    report = run_agent("Analyze synthetic data", REGISTRY, client=client, model="test-model")
    assert report["tool_trace"] == [{"tool": "run_shell", "ok": False}]
    assert client.requests[0]["store"] is False
    assert any(
        x.get("type") == "function_call_output"
        for x in client.requests[1]["input"]
        if isinstance(x, dict)
    )


def test_agent_budget_and_validation():
    call = NS(type="function_call", name="unknown", arguments="{}", call_id="c1")
    client = Client([NS(output=[call])])
    with pytest.raises(RuntimeError, match="budget"):
        run_agent("task", REGISTRY, client=client, model="test-model", max_turns=1)
    with pytest.raises(ValueError):
        run_agent("", REGISTRY, client=client, model="test-model")


async def test_mcp_stdio_roundtrip():
    import os
    import sys
    from pathlib import Path
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    root = Path(__file__).resolve().parents[1]
    env = dict(os.environ, PYTHONPATH=str(root / "src"))
    params = StdioServerParameters(
        command=sys.executable, args=["-m", "search_evidence.cli", "serve"], env=env
    )
    demo = json.loads((root / "examples/demo.json").read_text())
    name = next(iter(REGISTRY))
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            listed = await session.list_tools()
            assert name in {t.name for t in listed.tools}
            result = await session.call_tool(name, {"payload": demo})
            assert not result.isError
            assert result.content
