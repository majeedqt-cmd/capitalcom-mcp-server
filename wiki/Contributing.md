# Contributing

This is a community project — contributions are welcome. The full checklist
lives in the repo's
[`CONTRIBUTING.md`](https://github.com/SimonTarara62/capitalcom-mcp-server/blob/main/CONTRIBUTING.md);
this page is a short pointer, not a replacement.

## Dev setup

```bash
git clone https://github.com/SimonTarara62/capitalcom-mcp-server
cd capitalcom-mcp-server
make install        # editable install + the capitalcom-cli SDK from PyPI
make check           # ruff + mypy + pytest (offline; no network/credentials)
```

`make check` is fully offline — no live credentials or network access
required to develop and validate a change. End-to-end tests that exercise
every tool against the live **demo** API are optional and separate (see
`CONTRIBUTING.md`); always use a **demo** account for development, never live.

## Where to start

- **New to the project?** Pick something from
  [`docs/good-first-issues.md`](https://github.com/SimonTarara62/capitalcom-mcp-server/blob/main/docs/good-first-issues.md) —
  small, well-scoped tasks across documentation, tests, and low-risk
  read-only tools.
- **Adding a tool, resource, or prompt?** Follow
  [`docs/extending.md`](https://github.com/SimonTarara62/capitalcom-mcp-server/blob/main/docs/extending.md) —
  it has the architecture, a worked example, the unit-test pattern, e2e
  coverage registration, and how to re-freeze the API snapshot. See also
  [[Architecture]] for a short orientation.
- **Changing an existing tool's name, parameters, or semantics?** Read
  [[API Stability]] first — that's a breaking change and needs a major
  version bump and a deprecation path.

## Ground rules

- Be respectful — see `CODE_OF_CONDUCT.md`.
- Never commit secrets; `.env` and credential files are gitignored.
- Develop and test against a **demo** Capital.com account.
- Keep PRs focused, update `CHANGELOG.md` under `## [Unreleased]`, and
  prefer Conventional Commit messages (`feat:`, `fix:`, `docs:`).

## See also

- `CONTRIBUTING.md` in the repository — the full contributor checklist
- `docs/extending.md` in the repository — the architecture and extension guide
- `docs/good-first-issues.md` in the repository — scoped starter tasks
- [[Architecture]] — a short orientation to the three-layer design
- [[API Stability]] — what counts as a breaking change to the tool surface
