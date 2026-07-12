.PHONY: install test cov lint fmt typecheck run e2e check snapshot wiki wiki-check wiki-publish

install:
	pip install -e ".[dev]"

test:
	pytest -q

cov:
	pytest --cov=capital_mcp --cov-report=term-missing

lint:
	ruff check capital_mcp tests scripts

fmt:
	ruff format capital_mcp tests scripts

typecheck:
	mypy capital_mcp scripts

run:
	capitalcom-mcp run

e2e:
	CAP_MCP_E2E=1 pytest -m e2e -v

check: lint typecheck test

snapshot: ## regenerate the frozen API-surface golden (after an intentional change)
	UPDATE_SNAPSHOT=1 pytest tests/test_api_surface_snapshot.py -q

wiki: ## regenerate the wiki reference pages into wiki/
	python3 scripts/gen_wiki.py

wiki-check: ## fail if the committed wiki reference pages are stale
	@tmp=$$(mktemp -d); \
	python3 scripts/gen_wiki.py $$tmp >/dev/null; \
	rc=0; \
	for f in Tools-Reference Resources-Reference Prompts-Reference Configuration-Reference Error-Reference; do \
	  diff -u wiki/$$f.md $$tmp/$$f.md || rc=1; \
	done; \
	rm -rf $$tmp; \
	if [ $$rc -ne 0 ]; then echo "wiki reference is STALE — run 'make wiki' and commit"; exit 1; fi; \
	echo "wiki reference pages up to date"

wiki-publish: ## sync wiki/*.md to the LIVE GitHub wiki (publishes immediately)
	bash scripts/publish_wiki.sh
