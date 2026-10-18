"""Protect menu wiring and frozen speedtest semantics with synthetic inputs."""

import ast
import hashlib
from pathlib import Path
from unittest.mock import Mock

import pytest


@pytest.mark.parametrize("choice,target", [("4", "show_speedtest_cn_main"),
                                            ("5", "show_proxy_exit_speedtest")])
def test_main_menu_speedtest_dispatch(monkeypatch, choice, target):
    from netwatch import cli

    callbacks = {name: Mock() for name in ("show_speedtest_cn_main", "show_proxy_exit_speedtest",
                                          "show_auto_speedtest")}
    for name, callback in callbacks.items():
        monkeypatch.setattr(cli, name, callback)
    answers = iter((choice, "8"))
    monkeypatch.setattr(cli.Prompt, "ask", lambda *a, **kw: next(answers))
    monkeypatch.setattr(cli, "_is_interactive_session", lambda: False)
    cli.main()
    for name, callback in callbacks.items():
        assert callback.call_count == int(name == target)


def test_advanced_menu_one_dispatches_general_diagnostics(monkeypatch):
    from netwatch import cli

    general = Mock()
    browser = Mock()
    monkeypatch.setattr(cli, "show_auto_speedtest", general)
    monkeypatch.setattr(cli, "show_speedtest_cn_main", browser)
    answers = iter(("1", "14"))
    monkeypatch.setattr(cli.Prompt, "ask", lambda *a, **kw: next(answers))
    cli.show_advanced_menu()
    general.assert_called_once_with()
    browser.assert_not_called()


@pytest.mark.parametrize("signal", [EOFError, KeyboardInterrupt])
def test_main_exit_signals_do_not_dispatch(monkeypatch, capsys, signal):
    from netwatch import cli

    callback = Mock()
    monkeypatch.setattr(cli, "show_speedtest_cn_main", callback)
    monkeypatch.setattr(cli, "_is_interactive_session", lambda: False)
    monkeypatch.setattr(cli.Prompt, "ask", Mock(side_effect=signal))
    cli.main()
    callback.assert_not_called()
    assert "已退出 netwatch-cli" in capsys.readouterr().out


@pytest.mark.parametrize("error", ["Playwright is not installed", "fixture timeout"])
def test_main_browser_failure_never_falls_back(monkeypatch, capsys, error):
    from netwatch.cli_modules import speedtest as ui
    from netwatch.speedtest.speedtest_cn import SpeedtestCnResult

    browser = Mock(return_value=SpeedtestCnResult(error=error))
    fallback = Mock(side_effect=AssertionError("unexpected fallback"))
    monkeypatch.setattr(ui.Prompt, "ask", lambda *a, **kw: "y")
    monkeypatch.setattr(ui, "run_speedtest_cn_browser_automation", browser)
    monkeypatch.setattr(ui, "run_best_speedtest", fallback)
    ui.show_speedtest_cn_main()
    browser.assert_called_once()
    options = browser.call_args.args[0]
    assert options.headless is True
    assert options.debug_screenshot is False
    fallback.assert_not_called()
    output = capsys.readouterr().out
    assert error in output
    assert "高级功能" in output
    assert "Traceback" not in output


@pytest.mark.parametrize("phase", ["prompt", "backend"])
def test_main_browser_interrupt_cancels_without_fallback(monkeypatch, capsys, phase):
    from netwatch.cli_modules import speedtest as ui

    browser = Mock(side_effect=KeyboardInterrupt)
    fallback = Mock()
    monkeypatch.setattr(ui.Prompt, "ask", Mock(side_effect=KeyboardInterrupt) if phase == "prompt" else Mock(return_value="y"))
    monkeypatch.setattr(ui, "run_speedtest_cn_browser_automation", browser)
    monkeypatch.setattr(ui, "run_best_speedtest", fallback)
    ui.show_speedtest_cn_main()
    assert browser.call_count == int(phase == "backend")
    fallback.assert_not_called()
    assert "已取消测速" in capsys.readouterr().out


@pytest.mark.parametrize("answer", ["", "n", "y"])
def test_proxy_details_are_opt_in_after_result(monkeypatch, answer):
    from netwatch.cli_modules import speedtest as ui
    from netwatch.network.proxy_probe import ExitIPInfo
    from netwatch.speedtest.backends.models import SpeedtestResult

    result = SpeedtestResult(backend="official-ookla-cli", download_mbps=100)
    events = []
    monkeypatch.setattr(ui, "probe_exit_ip", lambda: ExitIPInfo(ip=None, city=None, region=None, country=None, org=None))
    monkeypatch.setattr(ui.time, "sleep", lambda *a: None)
    backend = Mock(return_value=result)
    monkeypatch.setattr(ui, "run_best_speedtest", backend)
    monkeypatch.setattr(ui, "print_speedtest_result_table", lambda value: events.append(("table", value)))
    monkeypatch.setattr(ui, "print_speedtest_results_extra", lambda value: events.append(("details", value)))
    monkeypatch.setattr(ui, "print_proxy_exit_judgment", lambda value: None)

    def prompt(message, **kwargs):
        assert message == "是否查看详细诊断？"
        assert kwargs["default"] == "n"
        assert events == [("table", result)]
        events.append(("prompt", None))
        return answer

    monkeypatch.setattr(ui.Prompt, "ask", prompt)
    ui.show_proxy_exit_speedtest()
    backend.assert_called_once_with(use_interface=False)
    expected = [("table", result), ("prompt", None)]
    if answer == "y":
        expected.append(("details", result))
    assert events == expected


@pytest.mark.parametrize("path,name,expected", [
    ("netwatch/speedtest/runner.py", "run_best_speedtest", "a7b741989312a38f9ec67f742c411cee20642007b3405451378881cef6644533"),
    ("netwatch/cli_modules/speedtest.py", "show_auto_speedtest", "9c632a7a29c5e767d0e84aeb7237fdfd9fdc4bedc32c83a63e63070550010cdf"),
])
def test_frozen_function_ast(path, name, expected):
    root = Path(__file__).resolve().parents[2]
    tree = ast.parse((root / path).read_text())
    function = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == name)
    # Freeze bodies, not version-specific FunctionDef fields (e.g. type_params).
    body = ast.Module(body=function.body, type_ignores=[])
    digest = hashlib.sha256(ast.dump(body, include_attributes=False).encode()).hexdigest()
    assert digest == expected
