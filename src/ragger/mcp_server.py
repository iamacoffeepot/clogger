"""MCP server exposing Ragger tools to Claude."""

import json

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("ragger")


@mcp.tool(name="RaggerRun")
def ragger_run(name: str, script: str) -> str:
    """Execute a Lua script in the RuneLite client.

    Args:
        name: Short descriptive name for the script in kebab-case (e.g. "tick-counter", "camera-spin")
        script: Lua source code to execute
    """
    return json.dumps({"type": "script", "name": name, "source": script})


if __name__ == "__main__":
    mcp.run()
