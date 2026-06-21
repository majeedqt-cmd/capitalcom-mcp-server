import os
import stat
from types import SimpleNamespace

from capital_mcp import cli


def _fake_cfg(**over):
    base = {
        "cap_env": SimpleNamespace(value="demo"),
        "cap_api_key": "abcd1234",
        "cap_identifier": "me@example.com",
        "cap_api_password": "sekret",
        "cap_allow_trading": False,
        "cap_allowed_epics": "",
        "cap_ws_enabled": False,
        "cap_dry_run": False,
        "cap_max_position_size": 1.0,
        "cap_max_working_order_size": 1.0,
        "cap_max_open_positions": 3,
        "cap_max_orders_per_day": 20,
        "cap_require_explicit_confirm": True,
        "base_url": "https://demo-api-capital.backend-capital.com",
    }
    base.update(over)
    return SimpleNamespace(**base)


def test_build_parser_defaults():
    args = cli.build_parser().parse_args(["run"])
    assert args.command == "run"
    assert args.transport is None


def test_run_uses_env_transport(monkeypatch):
    monkeypatch.setenv("CAP_MCP_TRANSPORT", "http")
    monkeypatch.setenv("CAP_MCP_PORT", "9000")
    captured = {}

    def fake_run(**kwargs):
        captured.update(kwargs)

    import capital_mcp.server as server
    monkeypatch.setattr(server.mcp, "run", fake_run)
    cli.main(["run"])  # no flags -> env wins
    assert captured["transport"] == "http"
    assert captured["host"] == "127.0.0.1"
    assert captured["port"] == 9000


def test_run_stdio_passes_only_transport(monkeypatch):
    captured = {}
    import capital_mcp.server as server
    monkeypatch.setattr(server.mcp, "run", lambda **k: captured.update(k))
    cli.main(["run", "--transport", "stdio"])
    assert captured == {"transport": "stdio"}


def test_init_writes_0600_env_file(tmp_path, monkeypatch):
    target = tmp_path / "cfg" / ".env"
    written = cli.write_env_file(
        target, env="demo", api_key="my-key", identifier="me@example.com", api_password="api-pass"
    )
    assert written == target
    content = target.read_text()
    assert "CAP_API_KEY=my-key" in content
    assert "CAP_ENV=demo" in content
    mode = stat.S_IMODE(os.stat(target).st_mode)
    assert mode == 0o600


def test_doctor_reports_missing(monkeypatch, capsys):
    from capital_cli.core.errors import ConfigMissingError

    def boom():
        raise ConfigMissingError("Missing CAP_API_KEY")

    monkeypatch.setattr(cli, "_load_config", boom)
    rc = cli.cmd_doctor(cli.build_parser().parse_args(["doctor"]))
    out = capsys.readouterr().out
    assert rc == 1
    assert "Missing" in out
    assert "init" in out


def test_doctor_login_success(monkeypatch, capsys):
    monkeypatch.setattr(cli, "_load_config", _fake_cfg)
    monkeypatch.setattr(cli, "_try_login", lambda: {"accountId": "ABC123"})
    rc = cli.cmd_doctor(cli.build_parser().parse_args(["doctor", "--login"]))
    out = capsys.readouterr().out
    assert rc == 0
    assert "Login OK" in out
    assert "ABC123" in out


def test_doctor_login_failure(monkeypatch, capsys):
    monkeypatch.setattr(cli, "_load_config", _fake_cfg)

    def boom():
        raise RuntimeError("bad creds")

    monkeypatch.setattr(cli, "_try_login", boom)
    rc = cli.cmd_doctor(cli.build_parser().parse_args(["doctor", "--login"]))
    out = capsys.readouterr().out
    assert rc == 1
    assert "Login failed" in out


def test_doctor_offline_by_default(monkeypatch):
    monkeypatch.setattr(cli, "_load_config", _fake_cfg)
    called = {"login": False}
    monkeypatch.setattr(cli, "_try_login", lambda: called.__setitem__("login", True) or {})
    rc = cli.cmd_doctor(cli.build_parser().parse_args(["doctor"]))
    assert rc == 0
    assert called["login"] is False


def test_config_prints_redacted_view(monkeypatch, capsys):
    monkeypatch.setattr(cli, "_load_config", lambda: _fake_cfg(cap_api_key="supersecretkey"))
    rc = cli.cmd_config(cli.build_parser().parse_args(["config"]))
    out = capsys.readouterr().out
    assert rc == 0
    assert "Effective configuration" in out
    assert "supersecretkey" not in out   # never print the full secret
    assert "su***" in out                # _redact: first 2 chars + ***
    assert "CAP_ALLOW_TRADING" in out
    assert "max_open_positions" in out


def test_config_missing_creds(monkeypatch, capsys):
    from capital_cli.core.errors import ConfigMissingError

    def boom():
        raise ConfigMissingError("Missing CAP_API_KEY")

    monkeypatch.setattr(cli, "_load_config", boom)
    rc = cli.cmd_config(cli.build_parser().parse_args(["config"]))
    out = capsys.readouterr().out
    assert rc == 1
    assert "init" in out


def test_config_source_detects_cmd(monkeypatch, capsys):
    monkeypatch.setenv("CAP_API_KEY_CMD", "echo k")
    monkeypatch.setattr(cli, "_load_config", _fake_cfg)
    rc = cli.cmd_config(cli.build_parser().parse_args(["config"]))
    out = capsys.readouterr().out
    assert rc == 0
    assert "secret-exec" in out
    assert "CAP_API_KEY_CMD" in out
