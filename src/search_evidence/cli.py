"""CLI entry point: inspect tools, run one, export reports, or start MCP."""

import argparse
import json
from pathlib import Path
from .agent import run_agent
from .reports import write_reports
from .server import build_server
from .tools import REGISTRY


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("tools")
    call = sub.add_parser("run")
    call.add_argument("tool", choices=sorted(REGISTRY))
    call.add_argument("input", help="JSON file, maximum 5 MB")
    call.add_argument("--out", default="output")
    agent = sub.add_parser("agent")
    agent.add_argument("task", help="UTF-8 task file; sent to OpenAI")
    agent.add_argument("--out", default="output")
    server = sub.add_parser("serve")
    server.add_argument("--transport", choices=["stdio", "streamable-http"], default="stdio")
    args = parser.parse_args()
    if args.command == "tools":
        print(
            json.dumps(
                {
                    n: {"description": d, "schema": s.model_json_schema()}
                    for n, (s, f, d) in REGISTRY.items()
                },
                indent=2,
            )
        )
    elif args.command == "serve":
        build_server().run(transport=args.transport)
    elif args.command == "agent":
        if Path(args.task).stat().st_size > 240_000:
            parser.error("Task file too large")
        write_reports(run_agent(Path(args.task).read_text(encoding="utf-8"), REGISTRY), args.out)
    else:
        if Path(args.input).stat().st_size > 5_000_000:
            parser.error("Input file too large")
        schema, handler, _ = REGISTRY[args.tool]
        result = handler(schema.model_validate_json(Path(args.input).read_text(encoding="utf-8")))
        write_reports(result, args.out)


if __name__ == "__main__":
    main()
