#!/usr/bin/env bash
# Mirror wiki/*.md into the live GitHub wiki (…capitalcom-mcp-server.wiki.git).
# Publishing is immediate (wikis have no PR review) — run only after reviewing wiki/.
set -euo pipefail

REPO="SimonTarara62/capitalcom-mcp-server"
SRC="$(cd "$(dirname "$0")/.." && pwd)/wiki"
SHA="$(git -C "$(dirname "$SRC")" rev-parse --short HEAD)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

git clone --depth 1 "https://github.com/${REPO}.wiki.git" "$TMP/wiki"
# Add/update the wiki with our source-of-truth pages (including _Sidebar/_Footer).
# This is a merge-overwrite, not an exact mirror: it does not delete pages that
# exist live but have no corresponding file in wiki/.
cp "$SRC"/*.md "$TMP/wiki/"
cd "$TMP/wiki"
git add -A
if git diff --cached --quiet; then
  echo "Wiki already up to date — nothing to publish."
  exit 0
fi
git commit -m "docs(wiki): sync from ${REPO}@${SHA}"
git push
echo "Published wiki from ${SHA}."
