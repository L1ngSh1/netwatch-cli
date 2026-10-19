"""Advanced keyword/preset lists and execution must share the official backend."""

from io import StringIO
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from rich.console import Console

from netwatch.cli_modules import speedtest as ui
from netwatch.speedtest import runner
from netwatch.speedtest.backends.models import SpeedtestResult

SERVERS = [{"id": str(i), "name": "Example ISP", "location": "Guangzhou"} for i in range(1, 5)]


@pytest.fixture
def selection(monkeypatch):
    out = StringIO()
    monkeypatch.setattr(ui, "console", Console(file=out, width=160, color_system=None))
    official = Mock(return_value=True)
    python = Mock(return_value=True)
    official_list = Mock(return_value=SERVERS)
    python_list = Mock(return_value=[{"id": "python-only", "location": "Guangzhou"}])
    monkeypatch.setattr(runner.ookla_cli, "is_available", official)
    monkeypatch.setattr(runner.python_speedtest, "is_available", python)
    monkeypatch.setattr(runner.ookla_cli, "list_servers", official_list)
    monkeypatch.setattr(runner.python_speedtest, "list_servers", python_list)
    monkeypatch.setattr(runner.ookla_cli, "get_install_hint", lambda: "INSTALL_OFFICIAL_OOKLA")
    execute = Mock(return_value=SpeedtestResult("official-ookla-cli", server_id="1", download_mbps=100))
    interface = Mock(return_value=None)
    probe = Mock(return_value=SimpleNamespace(org="Example ISP", city="Guangzhou", region="Guangdong"))
    printer = Mock()
    monkeypatch.setattr(ui, "run_speedtest_with_backend", execute)
    monkeypatch.setattr(ui, "get_speedtest_interface_name", interface)
    monkeypatch.setattr(ui, "probe_exit_ip", probe)
    monkeypatch.setattr(ui, "_print_speedtest_result", printer)
    monkeypatch.setattr(ui.Prompt, "ask", lambda *a, **kw: "auto")
    monkeypatch.setattr(ui.Confirm, "ask", lambda *a, **kw: False)
    return SimpleNamespace(out=out, official=official, python=python, official_list=official_list,
                           python_list=python_list, execute=execute, interface=interface, probe=probe, printer=printer)


@pytest.mark.parametrize("official,python", [(False, True), (True, False), (True, True), (False, False)])
def test_explicit_list_never_uses_python(selection, official, python):
    selection.official.return_value = official
    selection.python.return_value = python
    servers = runner.list_ookla_speedtest_servers()
    selection.official.assert_called_once_with()
    selection.python_list.assert_not_called()
    selection.python.assert_not_called()
    if official:
        assert servers is SERVERS
        selection.official_list.assert_called_once_with()
    else:
        assert "官方 Ookla CLI" in servers[0]["error"]
        assert "INSTALL_OFFICIAL_OOKLA" in servers[0]["error"]
        selection.official_list.assert_not_called()


@pytest.mark.parametrize("official,python", [(False, True), (True, False), (True, True), (False, False)])
def test_general_list_keeps_its_existing_fallback(selection, official, python):
    selection.official.return_value = official
    selection.python.return_value = python
    servers = runner.list_speedtest_servers()
    if official:
        assert servers is SERVERS
    elif python:
        assert servers[0]["id"] == "python-only"
    else:
        assert servers[0]["error"]


@pytest.mark.parametrize("flow", ["keyword", "preset"])
@pytest.mark.parametrize("official,python", [(False, True), (True, False), (True, True), (False, False)])
def test_selection_list_and_execution_have_the_same_backend(selection, flow, official, python):
    selection.official.return_value = official
    selection.python.return_value = python
    if flow == "keyword":
        ui.run_keyword_speedtest("Guangzhou")
    else:
        ui.show_isp_city_preset_speedtest()
    selection.python_list.assert_not_called()
    selection.official.assert_called_once_with()
    if not official:
        selection.official_list.assert_not_called()
        selection.execute.assert_not_called()
        selection.interface.assert_not_called()
        selection.probe.assert_not_called()
        assert "INSTALL_OFFICIAL_OOKLA" in selection.out.getvalue()
    else:
        selection.official_list.assert_called_once_with()
        assert selection.execute.call_count == 3
        assert [call.args for call in selection.execute.call_args_list] == [("official-ookla-cli",)] * 3
        assert [call.kwargs["server_id"] for call in selection.execute.call_args_list] == ["1", "2", "3"]


@pytest.mark.parametrize("servers", [[], [{"error": "synthetic list failure"}]])
@pytest.mark.parametrize("flow", ["keyword", "preset"])
def test_empty_or_failed_list_stops_both_flows(selection, servers, flow):
    selection.official_list.return_value = servers
    if flow == "keyword": ui.run_keyword_speedtest("Guangzhou")
    else: ui.show_isp_city_preset_speedtest()
    selection.execute.assert_not_called()
    selection.probe.assert_not_called()
    selection.python_list.assert_not_called()
    assert "列表" in selection.out.getvalue()


@pytest.mark.parametrize("answer", ["99", "", "bad", KeyboardInterrupt, EOFError])
def test_invalid_or_cancelled_selection_never_runs_or_selects_interface(monkeypatch, selection, answer):
    def ask(*a, **kw):
        if isinstance(answer, type): raise answer
        return answer
    monkeypatch.setattr(ui.Prompt, "ask", ask)
    ui.run_keyword_speedtest("Guangzhou")
    selection.execute.assert_not_called()
    selection.interface.assert_not_called()


def test_manual_selection_uses_id_from_official_list(monkeypatch, selection):
    monkeypatch.setattr(ui.Prompt, "ask", lambda *a, **kw: "2")
    ui.run_keyword_speedtest("Guangzhou")
    selection.execute.assert_called_once_with("official-ookla-cli", server_id="2", interface=None)


def test_auto_candidates_continue_after_failure_and_choose_best(selection):
    selection.execute.side_effect = [
        SpeedtestResult("official-ookla-cli", error="synthetic candidate failure"),
        SpeedtestResult("official-ookla-cli", server_id="2", download_mbps=100),
        SpeedtestResult("official-ookla-cli", server_id="3", download_mbps=200),
    ]
    ui.run_keyword_speedtest("Guangzhou")
    assert selection.execute.call_count == 3
    assert selection.printer.call_args.args[0].server_id == "3"


def test_all_failed_candidates_do_not_publish_a_result(selection):
    selection.execute.return_value = SpeedtestResult("official-ookla-cli", error="synthetic failure")
    ui.run_keyword_speedtest("Guangzhou")
    selection.printer.assert_not_called()
    assert "候选服务器测速均失败" in selection.out.getvalue()


def test_cancelled_candidate_stops_remaining_candidates(selection, monkeypatch):
    selection.execute.side_effect = KeyboardInterrupt
    ui.run_keyword_speedtest("Guangzhou")
    selection.execute.assert_called_once()
    selection.printer.assert_not_called()


@pytest.mark.parametrize("exc", [KeyboardInterrupt, EOFError])
def test_keyword_prompt_can_be_cancelled(selection, monkeypatch, exc):
    def ask(*a, **kw): raise exc
    monkeypatch.setattr(ui.Prompt, "ask", ask)
    ui.show_keyword_speedtest()
    selection.official.assert_not_called()
    selection.execute.assert_not_called()
