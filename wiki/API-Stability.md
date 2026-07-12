# API Stability

This page is a summary — the authoritative policy lives in the repo's
[`docs/api-stability.md`](https://github.com/SimonTarara62/capitalcom-mcp-server/blob/main/docs/api-stability.md).
Read that page for the full guarantee text; this one just orients you.

## The surface is a stable contract

The server exposes a fixed surface — **42 tools**, **4 resources**, and **7
guided prompts** — and that surface is a contract you can build a client
integration on. Within a given **major** version:

- Tool, resource, and prompt **names** don't change or get removed.
- A tool's **semantics** don't silently change — what a tool does stays what
  it did.
- Existing **parameters** keep their name, type, and meaning.

Adding a new tool/resource/prompt, or adding a new *optional* parameter to an
existing tool, is allowed without a major version bump — those are additive.
Renaming or removing something, or changing a parameter's type, requires a
major bump and (where feasible) ships with a deprecation alias, always
recorded in the CHANGELOG.

This contract covers the **shape** of the interface — names, parameters,
prompt arguments. It does not freeze the *values* returned from the live
Capital.com API (those reflect the upstream API) or the exact wording of
human-readable descriptions.

## How it's enforced

The surface is locked by an automated snapshot
(`tests/snapshots/api_surface.json`) checked in the offline test suite. Any
accidental change to a tool schema, resource URI, or prompt argument fails CI
until it's either reverted or deliberately re-frozen with a CHANGELOG entry.

## Pinning is a separate, stronger guarantee

Version stability is a promise about *major* versions — a `1.x` release can
still add tools between `1.0` and `1.4`. To pin against **any** change at
all, including additive ones, pin the exact package version in your client
config (`capitalcom-mcp==0.3.4`) — see [[Client Setup]].

## See also

- `docs/api-stability.md` in the repository — the authoritative policy text
- [[Contributing]] — the checklist for adding a tool without breaking this contract
- [[Client Setup]] — how to pin an exact version
