"""mcp-connect-starter: a production-minded MCP server starter kit.

Built on the official MCP Python SDK (FastMCP). See the README for
architecture, security model, and quickstart instructions.
"""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("mcp-connect-starter")
except PackageNotFoundError:  # running from a source checkout without an install
    __version__ = "0.0.0+dev"

__all__ = ["__version__"]
