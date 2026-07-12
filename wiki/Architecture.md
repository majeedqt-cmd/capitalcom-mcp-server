# Architecture

This is a summary for orientation — the authoritative, up-to-date guide
(including a worked "add a tool" example and the testing patterns) is the
repo's [`docs/extending.md`](https://github.com/SimonTarara62/capitalcom-mcp-server/blob/main/docs/extending.md).
Read this page first if you're deciding whether to contribute; read
`docs/extending.md` before you start writing code.

## Three layers

The server is a thin [FastMCP](https://github.com/jlowin/fastmcp) layer over
the [`capitalcom-cli`](https://github.com/SimonTarara62/capitalcom-cli) SDK.
If you can call the SDK, you can add a tool:

```
MCP client ──▶ capital_mcp/server.py        @mcp.tool() async functions
                     │                       (the surface MCP clients see)
                     ▼
              capital_mcp/context.py         get_app() → one lazy CapitalComApp
                     │                       (no login until first call)
                     ▼
              capital_cli SDK facade         app.markets / accounts / trading /
                     │                       watchlists / stream / session
                     ▼
              capital_mcp/serialization.py   optional helpers (e.g. preview_to_dict)
```

- **`server.py`** holds every tool, resource, and prompt. Tools never talk to
  the network directly — they call the SDK facade via `get_app()`.
- **`context.py`** owns the single `CapitalComApp` instance and builds it
  lazily.
- **`serialization.py`** holds small helpers for the few flows whose SDK
  result needs flattening into the tool's response shape. Most tools return
  the SDK's dict as-is — it's already JSON-safe.

## Credential-free startup

The `CapitalComApp` is constructed lazily: the server process starts, and can
be introspected (e.g. listed by an MCP client, or hit with `cap://status`),
**without logging in or even having valid credentials on hand for that**.
Login happens on first tool call that needs it, always by going through
`get_app()`. This is why `uvx capitalcom-mcp --help` and the tool/resource/prompt
listing work even before you've run `init`.

## The safety layer

Mutating tools don't enforce their own guardrails ad hoc — the two-phase
preview/execute flow, the trading allowlist, and the risk caps all live in
the SDK facade the tools call through. See [[Safety Model]] for the
guardrails themselves, and [[Error Reference]] for what they raise when
triggered.

## Extending the server

For adding a new tool, resource, or prompt — including a worked example, the
unit-test pattern with the in-memory `client`/`fake_app` fixtures, e2e
coverage registration, and re-freezing the API snapshot — see the repo's
[`docs/extending.md`](https://github.com/SimonTarara62/capitalcom-mcp-server/blob/main/docs/extending.md).
That page is the source of truth; this wiki page won't be kept in lockstep
with its details.

## See also

- [[Contributing]] — how to get set up and send a PR
- [[API Stability]] — what changes are additive vs. breaking to this surface
- [[Safety Model]] — the guardrails enforced below the tool layer
