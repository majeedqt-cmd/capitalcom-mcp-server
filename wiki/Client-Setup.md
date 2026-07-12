# Client Setup

This page has the exact config snippet for each MCP client. Every client uses
the same `command` / `args` / `env` shape — only the file location (and, for
VS Code, the root key) differs. See [[Installation and Setup]] first if you
haven't run `uvx capitalcom-mcp init` yet; it prints the `CAP_ENV_FILE` path
you'll paste below.

Pasting `"CAP_ENV_FILE": "<path from init>"` keeps secrets out of the client
config file entirely; you can instead put `CAP_API_KEY` / `CAP_IDENTIFIER` /
`CAP_API_PASSWORD` directly in `env` if you prefer, though `CAP_ENV_FILE` (or
the `CAP_*_CMD` secret-exec variables) is the safer default — see
[[Installation and Setup]] for why.

## Claude Desktop

`~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) /
`%APPDATA%\Claude\claude_desktop_config.json` (Windows):

```json
{
  "mcpServers": {
    "capitalcom": {
      "command": "uvx",
      "args": ["capitalcom-mcp"],
      "env": { "CAP_ENV_FILE": "/Users/you/.config/capital-mcp/.env" }
    }
  }
}
```

## Claude Code

```bash
claude mcp add --transport stdio \
  --env CAP_ENV_FILE=/Users/you/.config/capital-mcp/.env \
  capitalcom -- uvx capitalcom-mcp
```

## Cursor

`~/.cursor/mcp.json` (global) or `.cursor/mcp.json` (project):

```json
{
  "mcpServers": {
    "capitalcom": {
      "command": "uvx",
      "args": ["capitalcom-mcp"],
      "env": { "CAP_ENV_FILE": "/Users/you/.config/capital-mcp/.env" }
    }
  }
}
```

## VS Code (Copilot)

`.vscode/mcp.json` — note the root key is `servers`, not `mcpServers`, and
each entry needs `"type": "stdio"`:

```json
{
  "servers": {
    "capitalcom": {
      "type": "stdio",
      "command": "uvx",
      "args": ["capitalcom-mcp"],
      "env": { "CAP_ENV_FILE": "/Users/you/.config/capital-mcp/.env" }
    }
  }
}
```

## Windsurf

`~/.codeium/windsurf/mcp_config.json`:

```json
{
  "mcpServers": {
    "capitalcom": {
      "command": "uvx",
      "args": ["capitalcom-mcp"],
      "env": { "CAP_ENV_FILE": "/Users/you/.config/capital-mcp/.env" }
    }
  }
}
```

## ChatGPT

ChatGPT requires a **remote** server — stdio launchers (the config shapes
above) are not supported. Run the server with streamable-HTTP instead:

```bash
CAP_ENV_FILE=/home/you/.config/capital-mcp/.env \
  capitalcom-mcp run --transport http --host 0.0.0.0 --port 8000
# endpoint: http://<host>:8000/mcp
```

Put it behind a TLS-terminating reverse proxy for any public use. Once your
server is reachable over HTTPS, enable **Developer Mode** in ChatGPT
(Settings → Connectors → Advanced) and add the server URL ending in `/mcp`.
ChatGPT's **Deep Research** connector calls two read-only tools, `search` and
`fetch`, which this server implements natively; the rest of the tool surface
requires Developer Mode to access.

## Pinning for production / real-money use

`uvx capitalcom-mcp` always runs the **latest** published release, which is
fine for trying things out. For production or real-money use, pin the exact
version so an unexpected update can't change tool behavior under you:

```json
{
  "mcpServers": {
    "capitalcom": {
      "command": "uvx",
      "args": ["capitalcom-mcp==0.3.4"],
      "env": { "CAP_ENV_FILE": "/Users/you/.config/capital-mcp/.env" }
    }
  }
}
```

The CLI form is `uvx capitalcom-mcp==0.3.4 run …`. Pin to a version you've
reviewed, and bump deliberately after reading the CHANGELOG. See
[[API Stability]] for what a version pin actually protects you against.

## See also

- [[Installation and Setup]] — install, generate credentials, run the wizard
- [[Configuration Reference]] — every environment variable the `env` block can set
- [[Troubleshooting FAQ]] — fixes for the most common setup issues
