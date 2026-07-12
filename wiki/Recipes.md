# Recipes

Worked, copy-pasteable workflows using the tools and prompts in the
[[Tools Reference]] and [[Prompts Reference]]. Every recipe assumes you've
completed [[Installation and Setup]] and pointed the server at a **demo**
account — start there, not on live.

## 1. Preview and place a demo trade

The trading tools are deliberately **two-phase** — see [[Safety Model]] for
why. You always preview before you execute; nothing is placed on the broker
until a separate, explicit `confirm=true` call.

1. **Preview** the position — this validates the trade (size, stops, margin)
   against the broker but has **no side effects**:

   ```
   cap_trade_preview_position(
     epic="BTCUSD",
     direction="BUY",
     size=0.1,
     stop_distance=200,
     profit_distance=400
   )
   ```

   This returns a `preview_id` (and the validated trade detail) if the
   request is sound.

2. **Execute** the previewed trade — this is the only call that actually
   places an order, and it requires `confirm=true`:

   ```
   cap_trade_execute_position(
     preview_id="<preview_id from step 1>",
     confirm=true
   )
   ```

   Without `confirm=true` the tool raises `ConfirmRequiredError` and does
   nothing — see [[Error Reference]].

3. If the confirmation comes back `TIMEOUT`, don't retry blindly — reconcile
   first. See "How does pinning / a `TIMEOUT` confirmation work?" in
   [[Troubleshooting FAQ]].

For working orders (limit/stop entries rather than market fills), the same
shape applies with `cap_trade_preview_working_order` →
`cap_trade_execute_working_order`.

## 2. Stream live prices

Streaming tools use a persistent WebSocket connection and are gated behind
`CAP_WS_ENABLED=true` (see [[Configuration Reference]]). With that set:

```
cap_stream_prices(
  epics=["BTCUSD", "GOLD"],
  duration_s=60
)
```

This streams live bid/ask updates for the given EPICs for `duration_s`
seconds. If you want threshold-based notifications instead of a raw feed, use
`cap_stream_alerts` with an `alerts` map (`{EPIC: {level, direction}}`), or
launch the guided `live_price_monitor` / `real_time_alerts` prompts, which
wrap the same streaming tools with movement-alert logic.

## 3. Scan a watchlist

The `market_scan` prompt orchestrates market-data tools into a single guided
workflow: it fetches a watchlist, pulls price data for each market in it, and
prompts your client to analyze the results for opportunities. It never trades
on its own — see [[Prompts Reference]].

Launch it by name from your MCP client, optionally with arguments:

```
market_scan(watchlist_id="<id from cap_watchlists_list>", timeframe="HOUR", lookback_periods=24)
```

Under the hood it's just `cap_watchlists_get` + `cap_market_prices` (+
`cap_market_sentiment`) per market — you can call those tools directly if you
want more control than the prompt gives you.

## 4. Review positions

The `position_review` prompt is purely analytical — it reviews your open
positions and working orders and suggests adjustments, but never executes
anything:

```
position_review()
```

It calls `cap_trade_positions_list` and `cap_trade_orders_list`, then walks
through P&L, risk, and concentration per position. If it surfaces an
adjustment you want to make (e.g. tightening a stop), that's a separate,
explicit call to `cap_trade_positions_amend` with `confirm=true` — the prompt
itself won't do it for you.

## See also

- [[Tools Reference]] — every tool, grouped by area, with full parameters
- [[Prompts Reference]] — every guided prompt and its arguments
- [[Safety Model]] — why trading is two-phase and capped
- [[Troubleshooting FAQ]] — what to do when a recipe doesn't behave as expected
