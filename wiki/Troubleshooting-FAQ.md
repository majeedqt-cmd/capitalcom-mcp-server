# Troubleshooting FAQ

## "No credentials configured" / `ConfigMissingError`

The server can't find `CAP_API_KEY` / `CAP_IDENTIFIER` / `CAP_API_PASSWORD`
(directly, via a `.env` file, or via the `CAP_*_CMD` secret-exec variables).

**Fix:**

```bash
uvx capitalcom-mcp init      # interactive wizard, writes a 0600 .env
uvx capitalcom-mcp doctor    # confirm it now loads (no secrets printed)
```

`doctor` reports the active environment, a redacted key/identifier, the
trading flag, and the EPIC allowlist without ever printing a secret. Add
`--login` to also authenticate against the Capital.com API:

```bash
uvx capitalcom-mcp doctor --login
```

If credentials load but you want the *full* effective configuration (caps,
dry-run state, where credentials are sourced from), run:

```bash
uvx capitalcom-mcp config
```

See [[Installation and Setup]] for the full walkthrough.

## "Trading is disabled" / `TradingDisabledError` or `EpicNotAllowedError`

Trading is refused unless **both**:

- `CAP_ALLOW_TRADING=true` is set, **and**
- the instrument's EPIC is in `CAP_ALLOWED_EPICS` (comma-separated), or that
  variable is `ALL`.

An EPIC missing from the allowlist raises `EpicNotAllowedError` even with
trading enabled; missing/false `CAP_ALLOW_TRADING` raises
`TradingDisabledError`. Both checks run on every mutating call, and this is
intentional — read-only tools (market data, positions, history) keep working
regardless. Set both env vars (e.g. `CAP_ALLOW_TRADING=true`,
`CAP_ALLOWED_EPICS=BTCUSD,GOLD`) and re-check with `uvx capitalcom-mcp
config`. Full details in [[Safety Model]].

## Streaming tools do nothing / hang / aren't available

The four `cap_stream_*` tools (`cap_stream_prices`, `cap_stream_candles`,
`cap_stream_alerts`, `cap_stream_portfolio`) need `CAP_WS_ENABLED=true` — it
defaults to `false`. Set it, restart the server (via your client), and
confirm with `uvx capitalcom-mcp config` that `CAP_WS_ENABLED = True`. See
[[Configuration Reference]] and the streaming recipe in [[Recipes]].

## A trade returned `TIMEOUT` — what do I do?

A deal confirmation can come back `TIMEOUT` when the server genuinely doesn't
know whether the order reached the broker. **Do not blindly retry the same
execute call** — the original order may already be live, and a retry could
double it up.

Instead, reconcile:

- `cap_trade_positions_list` / `cap_trade_orders_list` — see if the position
  or order actually exists, or
- `cap_trade_confirm_get` / `cap_trade_confirm_wait` with the original
  `deal_reference` — poll for the real outcome.

Only decide on a next action (retry, adjust, or leave it) once you know what
actually happened. See "Ambiguous confirmations" in [[Safety Model]].

## How does version pinning work?

`uvx capitalcom-mcp` (no version) always runs the **latest** published
release — convenient for trying things out, but an upstream update could
change behavior under you. For production or real-money use, pin the exact
version in your client config, e.g. `"args": ["capitalcom-mcp==0.3.4"]` (CLI:
`uvx capitalcom-mcp==0.3.4 run …`). Pin to a version you've reviewed and bump
deliberately after reading the CHANGELOG.

Separately from pinning, the tool **surface** itself (names, parameters,
semantics) is a stable contract within a major version, enforced by an
automated snapshot test — see [[API Stability]]. Pinning protects against
*any* change, including additive ones; the stability contract protects you
even if you don't pin, as long as you stay on the same major version.

## See also

- [[Safety Model]] — the guardrails behind the errors above
- [[Error Reference]] — every error type the server can raise
- [[Configuration Reference]] — every environment variable and its default
- [[Client Setup]] — exact per-client config snippets
