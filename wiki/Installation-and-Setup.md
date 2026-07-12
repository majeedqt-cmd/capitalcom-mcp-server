# Installation and Setup

This page covers installing the server, generating credentials, and verifying
your configuration from the command line. To wire the server into a specific
MCP client (Claude Desktop, Cursor, VS Code, etc.), see [[Client Setup]].

## Install

No clone required. `uvx` runs the server in an isolated, throwaway
environment and always fetches the latest tested release:

```bash
uvx capitalcom-mcp --help        # smoke test
```

Or install a persistent command with `pipx`:

```bash
pipx install capitalcom-mcp
```

For production or real-money use, pin the exact version in your client
config (e.g. `capitalcom-mcp==0.3.4`) so an unexpected upstream release can't
change tool behavior under you — see the README's pinning note and
[[Configuration Reference]].

## Add your credentials

Get an API key in the Capital.com app under **Settings → API integrations**
(create a **demo** key first). Then run the interactive wizard:

```bash
uvx capitalcom-mcp init
```

`init` prompts for the environment (`demo`/`live`), your `CAP_API_KEY`,
`CAP_IDENTIFIER` (login email), and `CAP_API_PASSWORD` (the API key's custom
password), then writes them to `~/.config/capital-mcp/.env` with **file mode
`0600`** (owner read/write only). Trading and the EPIC allowlist are written
disabled by default. It also prints the exact client-config snippet
(`CAP_ENV_FILE` pointing at the file it just wrote) so you can paste it
straight into your MCP client. Pass `--path` to write the file somewhere else.

## Verify your setup

Check that configuration loads correctly, with no secrets printed:

```bash
uvx capitalcom-mcp doctor
```

This reports the active environment, redacted key/identifier, the trading
flag, and the EPIC allowlist. Add `--login` to also authenticate against the
Capital.com API and confirm your credentials actually work:

```bash
uvx capitalcom-mcp doctor --login
```

To see the full effective configuration — including size/position/order caps,
dry-run state, and where credentials are being sourced from — run:

```bash
uvx capitalcom-mcp config
```

`config` is offline and redacts all secrets; it's the fastest way to confirm
what the server will actually do before you point a client at it. See
[[Configuration Reference]] for what every setting controls.

## Keeping secrets out of client configs

Your MCP client's config file (e.g. `claude_desktop_config.json`) is often
synced, backed up, or otherwise less protected than you'd like. Two ways to
avoid putting secrets there directly:

- **`CAP_ENV_FILE`** — point the client's `env` block at the `0600` file
  `init` wrote (e.g. `"CAP_ENV_FILE": "/Users/you/.config/capital-mcp/.env"`).
  Only a file path lives in the client config; the secrets stay on disk with
  restricted permissions.
- **`CAP_API_KEY_CMD`, `CAP_IDENTIFIER_CMD`, `CAP_API_PASSWORD_CMD`** — set
  these to a command that prints the corresponding secret on stdout (e.g.
  `op read op://vault/...` for 1Password, or `pass show ...`). The secret is
  fetched fresh at server launch and is never written to disk or to your
  client config.

## Next steps

- [[Client Setup]] — exact config snippets per MCP client
- [[Configuration Reference]] — every environment variable, its type, and default
- [[Safety Model]] — how trading is gated once credentials are in place
