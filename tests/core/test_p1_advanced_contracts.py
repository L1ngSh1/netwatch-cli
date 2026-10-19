"""P1 reduces advanced overhead, never basic capabilities or entry points."""

import ast
import hashlib
from pathlib import Path
from unittest.mock import Mock

import pytest


ROOT = Path(__file__).resolve().parents[2]
HANDLERS = (
    "show_auto_speedtest", "show_speedtest_by_server_id", "show_keyword_speedtest",
    "show_isp_city_preset_speedtest", "show_save_last_speedtest_server",
    "show_clear_preferred_speedtest", "show_speedtest_config",
    "show_last_speedtest_raw_summary", "show_speedtest_backend_info",
    "show_ookla_selection_details", "show_librespeed_custom_menu",
    "open_speedtest_cn_reference", "show_precise_offline_location",
)


@pytest.mark.parametrize("choice,target", [(str(i), name) for i, name in enumerate(HANDLERS, 1)])
def test_every_advanced_action_keeps_its_number(monkeypatch, choice, target):
    from netwatch import cli

    callbacks = {name: Mock() for name in HANDLERS}
    for name, callback in callbacks.items():
        monkeypatch.setattr(cli, name, callback)
    answers = iter((choice, "14"))

    def prompt(*args, **kwargs):
        assert kwargs["choices"] == [str(i) for i in range(1, 15)]
        assert kwargs["default"] == "14"
        return next(answers)

    monkeypatch.setattr(cli.Prompt, "ask", prompt)
    cli.show_advanced_menu()
    for name, callback in callbacks.items():
        assert callback.call_count == int(name == target)


def test_config_action_does_not_repeat_speedtest_disclaimers(monkeypatch, capsys):
    from netwatch import cli

    answers = iter(("7", "14"))
    monkeypatch.setattr(cli.Prompt, "ask", lambda *a, **kw: next(answers))
    monkeypatch.setattr(cli, "show_speedtest_config", Mock())
    cli.show_advanced_menu()
    output = capsys.readouterr().out
    assert "通用测速诊断会依次尝试" not in output
    assert "不一定代表本地宽带最大值" not in output


def test_general_diagnostics_keeps_its_warning_once(monkeypatch, capsys):
    from netwatch import cli

    answers = iter(("1", "14"))
    monkeypatch.setattr(cli.Prompt, "ask", lambda *a, **kw: next(answers))
    monkeypatch.setattr(cli, "show_auto_speedtest", Mock())
    cli.show_advanced_menu()
    output = capsys.readouterr().out
    assert output.count("通用测速诊断会依次尝试") == 1
    assert output.count("不一定代表本地宽带最大值") == 1


def test_precise_orchestrator_is_not_a_top_level_cli_import():
    path = ROOT / "netwatch/cli_modules/location.py"
    tree = ast.parse(path.read_text())
    assert not any(isinstance(n, ast.ImportFrom) and n.module == "netwatch.location.precise_location"
                   for n in tree.body)
    wrapper = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "run_precise_location_report")
    assert any(isinstance(n, ast.ImportFrom) and n.module == "netwatch.location.precise_location"
               for n in ast.walk(wrapper))


@pytest.mark.parametrize("answer", ["n", KeyboardInterrupt])
def test_precise_cancel_does_not_load_or_run_orchestrator(monkeypatch, answer):
    import builtins
    from netwatch.cli_modules import location as ui

    original_import = builtins.__import__

    def import_without_precise(name, *args, **kwargs):
        assert name != "netwatch.location.precise_location", "cancellation imported advanced implementation"
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", import_without_precise)
    callback = Mock(side_effect=AssertionError("cancel must not execute"))
    monkeypatch.setattr(ui, "run_precise_location_report", callback)
    prompt = Mock(side_effect=KeyboardInterrupt) if answer is KeyboardInterrupt else Mock(return_value=answer)
    monkeypatch.setattr(ui.Prompt, "ask", prompt)
    ui.show_precise_offline_location()
    callback.assert_not_called()


def test_precise_lazy_wrapper_preserves_arguments_and_result(monkeypatch):
    from netwatch.cli_modules import location as ui
    from netwatch.location import precise_location as domain

    result = object()
    callback = Mock(return_value=result)
    monkeypatch.setattr(domain, "run_precise_location_report", callback)
    # The P0 eager alias and the P1 local binding must both stay fully mocked.
    if hasattr(ui, "_default_run_precise_location_report"):
        monkeypatch.setattr(ui, "_default_run_precise_location_report", callback)
    assert ui.run_precise_location_report(timeout_seconds=17) is result
    callback.assert_called_once_with(timeout_seconds=17)


def test_default_installation_retains_browser_setup_and_basic_geo_dependency():
    readme = (ROOT / "README.md").read_text()
    metadata = (ROOT / "pyproject.toml").read_text()
    dependencies = metadata.split("dependencies = [", 1)[1].split("]", 1)[0]
    assert '"reverse-geocoder>=1.5.1"' in dependencies
    assert 'python -m pip install -e ".[browser]"' in readme
    assert "python -m playwright install chromium" in readme
    assert metadata.split("browser = ", 1)[1].splitlines()[0] == '["playwright>=1.44"]'


@pytest.mark.parametrize("path,name,expected", [
    ("netwatch/cli.py", "build_menu", "167d9f3ddbee70e29681986fad00ef3a57ac34a94f98c729d260ae917e2bca6d"),
    ("netwatch/cli.py", "main", "c011436de2449fea831642ecc8c3808795ef7df0317eb1c165b158e7f6af95eb"),
    ("netwatch/cli.py", "show_realtime_traffic", "4061fdc6e5018fb3e3bf72ebc432edb5e620a0e657296fa9b554e77dc9966a95"),
    ("netwatch/cli_modules/location.py", "show_network_info", "4ddf84bdcd0f72bd669c7b533f783e125451d2e10815823697a4b996393b5c7e"),
    ("netwatch/cli_modules/location.py", "print_device_location_result", "da657770da548fb506ab40fe3e27e76e4d3fb224fbd0cd88923a755358a395e8"),
])
def test_basic_function_bodies_match_p0(path, name, expected):
    tree = ast.parse((ROOT / path).read_text())
    function = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name)
    body = ast.Module(body=function.body, type_ignores=[])
    assert hashlib.sha256(ast.dump(body, include_attributes=False).encode()).hexdigest() == expected
