"""`python -m backend` listens on this PC only by default; --host opens it, and --port changes the port."""
import backend.__main__ as launcher


def test_the_default_listens_on_this_pc_only():
    args = launcher.parse_args([])
    assert args.host == "127.0.0.1"
    assert args.port == 8000


def test_host_can_be_set_to_open_the_api_to_the_network():
    assert launcher.parse_args(["--host", "0.0.0.0"]).host == "0.0.0.0"


def test_the_server_is_started_with_the_chosen_host_and_port(monkeypatch):
    calls = []
    monkeypatch.setattr(launcher.uvicorn, "run", lambda app, **kw: calls.append((app, kw)))
    launcher.main(["--port", "9100"])
    assert calls == [("backend.main:app", {"host": "127.0.0.1", "port": 9100})]


def test_the_vite_proxy_targets_the_ipv4_address_the_backend_listens_on():
    from pathlib import Path
    cfg = (Path(__file__).resolve().parents[2] / "frontend" / "vite.config.ts").read_text(encoding="utf-8")
    assert "target: 'http://127.0.0.1:8000'" in cfg
