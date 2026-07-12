# Capital.com MCP Server

**capitalcom-mcp** is an unofficial, community-built [Model Context
Protocol](https://modelcontextprotocol.io) server for the **Capital.com Open
API**. It exposes **42 guarded trading and market-data tools** — plus
resources and guided prompts — to any MCP client (Claude Desktop, Claude Code,
Cursor, VS Code, Windsurf, ChatGPT, and others), over stdio or HTTP. Trading is
disabled by default, every mutation is two-phase (preview → confirm →
execute), and the project is **demo-first**: you're expected to point it at a
Capital.com demo account before ever touching a live one.

> ⚠️ **Unofficial and educational.** This project is not affiliated with, and
> not endorsed by, Capital.com. It is a community integration built against
> Capital.com's public API. Nothing here is financial advice, and trading
> carries risk of loss — always start on a demo account and understand the
> tool before enabling live trading.

## Who this is for

**End users** — you just want an AI assistant (Claude, ChatGPT, etc.) that can
check prices, review your positions, and place trades under your explicit
control. Start with [[Installation and Setup]], skim [[Safety Model]] so you
know what the guardrails do, then point your client at a demo account.

**Developers** — you want to extend the server, add a tool, or understand how
the two-phase execution and risk checks are implemented. Start with the
[[Tools Reference]] for the full tool surface, then see [[Architecture]] and
[[Contributing]] for the codebase design.

## Quick links

- [[Installation and Setup]] — install, get credentials, run the wizard
- [[Safety Model]] — how trading is gated, capped, and made two-phase
- [[Tools Reference]] — the full list of 42 tools, grouped by area
- [[Recipes]] — worked, copy-pasteable end-to-end workflows
