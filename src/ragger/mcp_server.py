"""MCP server exposing Ragger tools to Claude."""

import json

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("ragger")


@mcp.tool(name="RaggerRun")
def ragger_run(script: str) -> str:
    """Execute a Lua script in the RuneLite client."""
    return json.dumps({"type": "script", "source": script})


if __name__ == "__main__":
    mcp.run()
