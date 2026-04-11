---
name: runelite
description: Kill any running RuneLite instances and launch RuneLite with the Ragger plugin loaded.
user-invocable: true
allowed-tools: Bash
---

# Launch RuneLite

Kill any existing RuneLite and MCP server processes, then launch RuneLite via the plugin's `run.sh` script which sets `RAGGER_PROJECT_ROOT`.

```bash
pkill -f "net.runelite" 2>/dev/null
pkill -f "mcp_server.py" 2>/dev/null
sleep 1
cd plugin && ./run.sh 2>&1 &
```

Run the launch command in the background. Report that RuneLite is launching once the command is dispatched.
