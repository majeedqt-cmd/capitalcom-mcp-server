# NOOR LIVE TRADING V2 — implementation checkpoint

Status: **NOT DEPLOYED / NOT CONTINUOUSLY MONITORING** (20 October 2026).

## Existing system and observed fixes

- Existing Railway service: `win-capital-mcp-direct`, project `Win Capital Demo 24x7`.
- This service currently runs the upstream Capital MCP server. Its bounded streaming tool returned `WebSocket streaming is disabled`. No persistent V2 worker was present in that service's start command.
- Demo session/account name verified as `Noor live trading 1`; no account switching or trading actions were performed.
- GOLD reports streaming availability, USD contract size 1, minimum size and increment 0.01, margin factor 5 percent. These are observed account rules, not constants to assume for other accounts.
- Saved n8n Slack credential initially failed with `channel_not_found`. `auth.test` confirmed TheBoard and bot `win alrets`. Adding that existing bot to the designated private channel fixed posting.
- Successful n8n execution `5451`: 2026-10-20 07:20:36.737–07:20:37.264 UTC; Slack node 239 ms, full execution 527 ms. This does **not** measure market-to-Slack or delivery-to-phone latency.
- Workflow `yEHnnx3l0FMmPMMl` was created in personal n8n project `MAJEED Alzaqut <majeed.qt@icloud.com>` at project root. It remains inactive.

## Implemented, locally tested

- Independent process and in-memory Demo-only REST/WS session; no SDK state sharing or account switching.
- Hard endpoint allowlist: no order, close, amend or preferences endpoints; only login POST and read endpoints.
- H1/M30 closed-candle trend, M5 pullback/resumption, direct quote trigger; EMA20/50, MACD12/26/9, Wilder RSI14/ATR14, swing support/resistance.
- Conservative net cost allowance, technical stop first, lot increment/minimum checks, approximately $20 margin, risk at most $10, net reward/risk at least 1.5, initial minimum target profit $7.
- This combination can produce few or zero signals. It does not guarantee returns. At the observed 5 percent margin, one ounce would reserve roughly $207 at a $4,132 price; a roughly $20 margin corresponds to approximately 0.10 ounce, subject to broker increments.
- Stale and future timestamps, unclear/opposing directions, high spreads, invalid contract conventions and occupied account suppress signals.
- WS timeout/reconnect with capped exponential backoff; historical reseed after reconnect; bounded healthy-stream logs; no exception bodies or credentials logged.
- Baseline JSON with dated reason; whole approved setting override via `NOOR_V2_CONFIG`. No automatic strategy adaptation.
- Synthetic signals are explicitly `executed=false`; no synthetic performance results.

## Authenticated delivery draft

The inactive n8n workflow includes Header Auth, freshness/risk checks, duplicate routing, Slack posting, successful-send recording and source-to-Slack timing. The tool auto-assigned an existing generic Header Auth credential. Its suitability and matching secret have **not** been established; do not publish it on that assumption. A dedicated NOOR V2 credential must be bound securely.

An unauthenticated webhook proposal was rejected by automatic approval review. It was not applied. The safer authenticated draft was accepted and remains inactive. No open callback was published.

The available n8n tools can reference credentials, but cannot create a new shared-secret credential. Railway OAuth returns variable names, not secret values. Browser fallback requires explicit user approval under the available browser tool's instructions. This is the current deployment blocker.

## Deployment prerequisites and next checks

1. Create n8n Header Auth credential dedicated to V2: header `X-Noor-Token`, randomly generated secret; bind it to `V2 authenticated webhook`. Store the same secret as service-level Railway `NOOR_V2_RELAY_TOKEN`. Never put the secret in chat, source control or a public URL.
2. Store service-level `NOOR_V2_ACCOUNT_ID` for the verified Noor Demo account, `NOOR_V2_RELAY_URL` for the authenticated n8n endpoint, and `NOOR_V2_DEPLOY_ID` for an auditable release ID.
3. Test unauthenticated rejection, authenticated delivery, stale payload rejection, duplicate suppression and durable record persistence. n8n manual executions can bypass inbound auth; use an actual HTTP call for the auth test.
4. Before enabling, review coexistence/restart impact on the existing service. Do not edit or restart WIN monitor/runtime/worker or Scalping Noor. Do not create a new billable worker/volume without authorization.
5. Pin code/dependencies and run the worker with the existing MCP server only after those prerequisites. Preserve the original start command for rollback. Observe Railway terminal `SUCCESS`, worker healthy logs, and a live WS quote through the authenticated relay.
6. Measure source timestamp to Slack timestamp, test reconnect and process independence, then have Majeed confirm receipt of the uniquely labelled test on his phone. Slack API success alone is insufficient.
7. Actual trade-outcome attribution and a review after 30 **executed** Demo trades remain to be connected and verified. Signal logs alone are not executed trades. Success metrics must use broker-confirmed IDs and net P/L, including fees; no report can be produced before that data exists.

## Local verification

`python -m unittest test_noor_v2 -v` — 9 tests passed before the final runtime validation additions; rerun for the final commit.

Tests cover known indicator values, sizing/cost math, impossible minimum contracts, excess risk/low reward, a synthetic opportunity, stale/future/unclosed candles, unclear/opposing trend, hard mutation blocking, and disconnected-stream timeout. Broker WS, live worker reconnect, n8n dedup persistence and phone delivery are not yet verified.

No Railway variables, start commands, deployments, account settings, trades, WIN services or Scalping Noor services were changed in this checkpoint.
