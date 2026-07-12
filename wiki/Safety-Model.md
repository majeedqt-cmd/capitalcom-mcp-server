# Safety Model

This server brokers real trading credentials and can place real orders, so it
is built to refuse by default and require explicit, narrow opt-in at every
step. This page explains the guardrails; see [[Error Reference]] for the
exact errors they raise when they trigger.

> ⚠️ Trading is risky. These guardrails reduce the blast radius of mistakes
> and bugs — they do not make trading safe. Always start on a **demo**
> account, and only enable live trading once you understand every setting
> below.

## Trading is off by default

Trading is refused (`TradingDisabledError`) unless **both** of the following
are true:

- `CAP_ALLOW_TRADING=true` is set, **and**
- the instrument's EPIC is present in `CAP_ALLOWED_EPICS` (a comma-separated
  allowlist), or that variable is set to `ALL`.

Both conditions are checked on every mutating call. Leaving either unset — or
misconfigured — keeps the account fully read-only from the server's
perspective: market data, positions, orders, and history can still be read,
but nothing can be opened, closed, or amended. An EPIC outside the allowlist
raises `EpicNotAllowedError` even with trading enabled.

## Two-phase execution

Every trade goes through two distinct tool calls, never one:

1. **Preview** (`cap_trade_preview_position` / `cap_trade_preview_working_order`)
   validates the trade against the broker without executing it, and returns a
   preview reference.
2. **Execute** (`cap_trade_execute_position` / `cap_trade_execute_working_order`)
   places the previously previewed trade, and requires `confirm=true` in the
   call. Without it, the tool raises `ConfirmRequiredError` and does nothing.

The same `confirm=true` requirement applies to every other mutating tool —
closing a position, cancelling or amending an order, changing account
preferences, topping up a demo balance, and watchlist writes. There is no
single tool call that both decides and executes a trade; an agent (or a
careless script) cannot skip straight to execution.

## Caps

Even with trading enabled and the EPIC allowed, the server enforces limits so
a single bad decision — automated or human — can't do unbounded damage:

- a maximum position size and maximum working-order size per trade,
- a cap on the number of open positions at once,
- a cap on the number of orders placed per day.

These are configured via `CAP_MAX_POSITION_SIZE`, `CAP_MAX_WORKING_ORDER_SIZE`,
`CAP_MAX_OPEN_POSITIONS`, and `CAP_MAX_ORDERS_PER_DAY` — see
[[Configuration Reference]] for defaults. Exceeding one raises
`RiskLimitError`.

## Dry run

Setting `CAP_DRY_RUN=true` blocks **all** executions regardless of the other
settings — useful for exercising an agent's full decision flow (search,
preview, reasoning) without ever letting an execute call reach the broker. A
blocked dry-run call raises `DryRunError`.

## Demo-first

`CAP_ENV=demo` (the `init` wizard's default) points the server at
Capital.com's demo environment, where trades use simulated funds. Treat
`CAP_ENV=live` as a deliberate, separate opt-in you make only after you trust
your configuration and workflow — never the starting point.

## Ambiguous confirmations: reconcile, don't retry

A deal confirmation can come back as `TIMEOUT` — the server genuinely doesn't
know whether the order reached the broker. In that case, **do not blindly
retry the same execute call**, since the original order may already be live
and a retry could double it up. Instead, reconcile: check
`cap_trade_positions_list` / `cap_trade_orders_list` (or
`cap_trade_confirm_get` / `cap_trade_confirm_wait` with the original
reference) to see what actually happened before deciding on a next action.

## See also

- [[Error Reference]] — the full list of safety-refusal and other errors
- [[Configuration Reference]] — every setting mentioned above, with defaults
- [[Installation and Setup]] — how to configure credentials and verify setup
