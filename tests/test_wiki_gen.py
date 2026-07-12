import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "gen_wiki", Path(__file__).resolve().parents[1] / "scripts" / "gen_wiki.py"
)
gen = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gen)


def _run(tmp_path, monkeypatch):
    monkeypatch.setattr(gen, "WIKI", tmp_path)
    gen.main()
    return tmp_path


def test_generator_writes_all_reference_pages(tmp_path, monkeypatch):
    out = _run(tmp_path, monkeypatch)
    assert {p.name for p in out.glob("*.md")} == {
        "Tools-Reference.md", "Resources-Reference.md", "Prompts-Reference.md",
        "Configuration-Reference.md", "Error-Reference.md",
    }


def test_tools_page_lists_all_42(tmp_path, monkeypatch):
    md = (_run(tmp_path, monkeypatch) / "Tools-Reference.md").read_text(encoding="utf-8")
    assert md.startswith(gen.BANNER)
    for name in ("cap_session_status", "cap_market_prices", "cap_trade_preview_position",
                 "cap_watchlists_create", "cap_stream_prices", "search", "fetch"):
        assert f"`{name}`" in md
    assert md.count("### `") == 42


def test_config_page_has_env_vars(tmp_path, monkeypatch):
    md = (_run(tmp_path, monkeypatch) / "Configuration-Reference.md").read_text(encoding="utf-8")
    assert "`CAP_API_KEY`" in md
    assert "`CAP_ALLOW_TRADING`" in md


def test_error_page_lists_safety_errors(tmp_path, monkeypatch):
    md = (_run(tmp_path, monkeypatch) / "Error-Reference.md").read_text(encoding="utf-8")
    for e in ("TradingDisabledError", "EpicNotAllowedError", "DryRunError",
              "ConfirmRequiredError", "RiskLimitError"):
        assert f"`{e}`" in md
