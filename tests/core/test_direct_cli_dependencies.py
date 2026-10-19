"""Migrated CLI modules consume explicit dependencies, not legacy entry overrides."""

import importlib
from unittest.mock import Mock

import pytest


@pytest.mark.parametrize("name,module", [
    ("get_display_network_interfaces", "netwatch.network.info"),
    ("get_preferred_physical_interface", "netwatch.network.info"),
    ("get_default_gateway", "netwatch.network.router"),
    ("probe_exit_ip", "netwatch.network.proxy_probe"),
    ("run_browser_geolocation", "netwatch.location.geolocation.device"),
])
def test_location_dependencies_are_direct_and_not_entry_overrides(monkeypatch, name, module):
    from netwatch import cli
    from netwatch.cli_modules import location as ui
    dependency = getattr(ui, name)
    assert dependency is getattr(importlib.import_module(module), name)
    trap = Mock(side_effect=AssertionError("legacy entry override must be ignored"))
    monkeypatch.setattr(cli, name, trap, raising=False)
    assert getattr(ui, name) is dependency
    sentinel = object()
    consumer = Mock(return_value=sentinel)
    monkeypatch.setattr(ui, name, consumer)
    assert getattr(ui, name)() is sentinel
    consumer.assert_called_once_with()
    trap.assert_not_called()


def test_lazy_precise_call_uses_domain_dependency_not_entry_override(monkeypatch):
    from netwatch import cli
    from netwatch.cli_modules import location as ui
    from netwatch.location import precise_location
    trap = Mock(side_effect=AssertionError("legacy precise override must be ignored"))
    monkeypatch.setattr(cli, "run_precise_location_report", trap, raising=False)
    sentinel = object()
    domain = Mock(return_value=sentinel)
    monkeypatch.setattr(precise_location, "run_precise_location_report", domain)
    assert ui.run_precise_location_report(timeout_seconds=17) is sentinel
    domain.assert_called_once_with(timeout_seconds=17)
    trap.assert_not_called()


@pytest.mark.parametrize("name", ["get_default_gateway", "get_default_route_gateway", "get_lan_router_gateway"])
def test_router_dependencies_are_direct_and_not_entry_overrides(monkeypatch, name):
    from netwatch import cli
    from netwatch.cli_modules import router as ui
    from netwatch.network import router
    dependency = getattr(ui, name)
    assert dependency is getattr(router, name)
    trap = Mock(side_effect=AssertionError("legacy router override must be ignored"))
    monkeypatch.setattr(cli, name, trap, raising=False)
    assert getattr(ui, name) is dependency
    trap.assert_not_called()


@pytest.mark.parametrize("name,module", [
    ("get_preferred_physical_interface", "netwatch.network.info"),
    ("probe_exit_ip", "netwatch.network.proxy_probe"),
    ("run_best_speedtest", "netwatch.speedtest.runner"),
    ("run_librespeed_custom_speedtest", "netwatch.speedtest.runner"),
    ("run_speedtest_cn_browser_automation", "netwatch.speedtest.speedtest_cn_browser"),
])
def test_speedtest_dependencies_are_direct_and_not_entry_overrides(monkeypatch, name, module):
    from netwatch import cli
    from netwatch.cli_modules import speedtest as ui
    dependency = getattr(ui, name)
    assert dependency is getattr(importlib.import_module(module), name)
    trap = Mock(side_effect=AssertionError("legacy speedtest override must be ignored"))
    monkeypatch.setattr(cli, name, trap, raising=False)
    assert getattr(ui, name) is dependency
    trap.assert_not_called()


@pytest.mark.parametrize("detailed", [True, False])
def test_speedtest_printer_uses_consumer_and_explicit_detail_contract(monkeypatch, detailed):
    from netwatch import cli
    from netwatch.cli_modules import speedtest as ui
    trap = Mock(side_effect=AssertionError("legacy printer override must be ignored"))
    printer = Mock()
    monkeypatch.setattr(cli, "print_speedtest_result", trap, raising=False)
    monkeypatch.setattr(ui, "print_speedtest_result", printer)
    sentinel = object()
    ui._print_speedtest_result(sentinel, detailed=detailed)
    printer.assert_called_once_with(sentinel, detailed=detailed)
    trap.assert_not_called()
