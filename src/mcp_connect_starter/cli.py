"""Command-line entry point: `mcp-connect-starter [--transport stdio|http]`.

Installed as a console script by pyproject.toml, so after
`pip install -e .` this is also available as `mcp-connect-starter` directly.
"""

from __future__ import annotations

import argparse
import sys

from mcp_connect_starter import config
from mcp_connect_starter.server import build_server


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="mcp-connect-starter",
        description="Run the MCP Connect Starter server.",
    )
    parser.add_argument(
        "--transport",
        choices=["stdio", "http"],
        default="stdio",
        help="'stdio' for Claude Desktop/Cursor (default), 'http' (streamable HTTP) for remote use.",
    )
    parser.add_argument(
        "--host",
        default=config.HTTP_HOST,
        help=f"HTTP host to bind when --transport=http (default: {config.HTTP_HOST}).",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=config.HTTP_PORT,
        help=f"HTTP port to bind when --transport=http (default: {config.HTTP_PORT}).",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = _parse_args(argv)

    if args.transport == "stdio":
        mcp = build_server()
        mcp.run(transport="stdio")
    else:
        mcp = build_server(host=args.host, port=args.port)
        print(
            f"mcp-connect-starter: serving streamable HTTP at "
            f"http://{args.host}:{args.port}{mcp.settings.streamable_http_path} "
            f"(health check: http://{args.host}:{args.port}/healthz)",
            file=sys.stderr,
        )
        mcp.run(transport="streamable-http")


if __name__ == "__main__":
    main()
