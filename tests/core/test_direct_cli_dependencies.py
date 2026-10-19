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
