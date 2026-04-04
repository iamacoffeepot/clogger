"""MCP server exposing Ragger tools to Claude."""

import json
import os

import requests
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("ragger")

BRIDGE_URL = f"http://127.0.0.1:{os.environ.get('RAGGER_BRIDGE_PORT', '7919')}"
BRIDGE_TOKEN = os.environ.get("RAGGER_BRIDGE_TOKEN", "")
BRIDGE_HEADERS = {"Authorization": f"Bearer {BRIDGE_TOKEN}"}


@mcp.tool(name="RaggerRun")
def ragger_run(name: str, script: str) -> str:
    """Execute a persistent Lua script in the RuneLite client.

    Args:
        name: Short descriptive name in kebab-case (e.g. "tick-counter", "npc-highlighter")
        script: Lua source code to execute
    """
    try:
        resp = requests.post(
            f"{BRIDGE_URL}/run",
            json={"name": name, "script": script},
            headers=BRIDGE_HEADERS,
            timeout=10,
        )
        return resp.text
    except requests.ConnectionError:
        return json.dumps({"error": "Bridge server not running"})


@mcp.tool(name="RaggerEval")
def ragger_eval(script: str) -> str:
    """Evaluate a Lua expression in the RuneLite client and return the result.

    Runs on the game client thread with access to all APIs (scene, player,
    client, items, coords, etc.). Returns the result as JSON.

    Args:
        script: Lua expression to evaluate (e.g. "scene:npcs()", "player:hp()")
    """
    try:
        resp = requests.post(
            f"{BRIDGE_URL}/eval",
            json={"script": script},
            headers=BRIDGE_HEADERS,
            timeout=10,
        )
        return resp.text
    except requests.ConnectionError:
        return json.dumps({"error": "Bridge server not running"})


@mcp.tool(name="RaggerScriptList")
def ragger_script_list() -> str:
    """List all currently running Lua scripts by name."""
    try:
        resp = requests.get(
            f"{BRIDGE_URL}/list",
            headers=BRIDGE_HEADERS,
            timeout=10,
        )
        return resp.text
    except requests.ConnectionError:
        return json.dumps({"error": "Bridge server not running"})


@mcp.tool(name="RaggerScriptSource")
def ragger_script_source(name: str) -> str:
    """Retrieve the Lua source code of a running script by name.

    Args:
        name: The script name (e.g. "tick-counter", "npc-highlighter")
    """
    try:
        resp = requests.post(
            f"{BRIDGE_URL}/source",
            json={"name": name},
            headers=BRIDGE_HEADERS,
            timeout=10,
        )
        return resp.text
    except requests.ConnectionError:
        return json.dumps({"error": "Bridge server not running"})


@mcp.tool(name="RaggerTemplateList")
def ragger_template_list() -> str:
    """List all registered Lua script templates by name."""
    try:
        resp = requests.get(
            f"{BRIDGE_URL}/templates",
            headers=BRIDGE_HEADERS,
            timeout=10,
        )
        return resp.text
    except requests.ConnectionError:
        return json.dumps({"error": "Bridge server not running"})


@mcp.tool(name="RaggerTemplateSource")
def ragger_template_source(name: str) -> str:
    """Retrieve the Lua source code of a registered template by name.

    Args:
        name: The template name (e.g. "tile-marker", "counter-display")
    """
    try:
        resp = requests.post(
            f"{BRIDGE_URL}/template-source",
            json={"name": name},
            headers=BRIDGE_HEADERS,
            timeout=10,
        )
        return resp.text
    except requests.ConnectionError:
        return json.dumps({"error": "Bridge server not running"})


if __name__ == "__main__":
    mcp.run()
