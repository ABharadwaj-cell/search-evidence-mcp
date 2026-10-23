import json
import socket
from pathlib import Path
import asyncio
import httpx
import uvicorn
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client
from mcp.server.transport_security import TransportSecuritySettings
from search_evidence.server import build_server
from search_evidence.tools import REGISTRY


async def test_real_http_discovery_call_and_host_protection():
    server = build_server()
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    port = listener.getsockname()[1]
    server.settings.transport_security = TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=[f"127.0.0.1:{port}"],
        allowed_origins=[f"http://127.0.0.1:{port}"],
    )
    app = uvicorn.Server(uvicorn.Config(server.streamable_http_app(), log_level="error"))
    task = asyncio.create_task(app.serve(sockets=[listener]))
    try:
        for _ in range(100):
            if app.started:
                break
            await asyncio.sleep(0.02)
        assert app.started
        url = f"http://127.0.0.1:{port}/mcp"
        async with httpx.AsyncClient(trust_env=False) as http:
            blocked = await http.post(url, headers={"Host": "attacker.example"}, json={})
            assert blocked.status_code == 421
        async with (
            httpx.AsyncClient(trust_env=False) as transport,
            streamable_http_client(url, http_client=transport) as (read, write, _),
        ):
            async with ClientSession(read, write) as client:
                await client.initialize()
                listed = await client.list_tools()
                assert len(listed.tools) == len(REGISTRY)
                payload = json.loads(
                    (Path(__file__).resolve().parents[1] / "examples/demo.json").read_text()
                )
                result = await client.call_tool(next(iter(REGISTRY)), {"payload": payload})
                assert not result.isError
    finally:
        app.should_exit = True
        await asyncio.wait_for(task, timeout=5)
        listener.close()
