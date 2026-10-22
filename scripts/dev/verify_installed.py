#!/usr/bin/env python3
"""Run with a clean wheel environment's python -I; all user actions are mocked."""

from __future__ import annotations

import argparse
from contextlib import ExitStack
import hashlib
import importlib.metadata
import importlib.util
from io import StringIO
import json
import os
from pathlib import Path
import platform
import socket
import subprocess
import sys
import tempfile
from unittest.mock import Mock, patch
import webbrowser


# Read development-side truth without putting the checkout on sys.path under -I.
DATA_CONTRACT = json.loads(Path(__file__).with_name("location_data_contract.json").read_text(encoding="utf-8"))

ADVANCED_MODULES = {
    "netwatch.location.precise_location", "netwatch.location.admin",
    "netwatch.location.admin.coord_transform", "netwatch.location.admin.china_admin_lookup",
    "netwatch.location.roads", "netwatch.location.roads.nearby_roads",
    "netwatch.location.admin.offline_boundary",
}


def inspect_installed_data(package_root: Path) -> dict[str, str]:
    """Check installed bytes against reviewed truth, not hashes of those bytes."""
    data_sha256 = {}
    for member, expected in DATA_CONTRACT["files"].items():
        path = package_root / Path(member).relative_to("netwatch")
        assert path.is_file(), f"missing runtime location data: {member}"
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        assert actual == expected, f"runtime location data checksum mismatch: {member}"
        data_sha256[member] = actual
    return data_sha256


def verify_center_lookup(package_root: Path) -> dict:
    """Exercise the installed local CSV consumer after cold-start assertions."""
    from netwatch.location.admin import china_admin_lookup as lookup

    package_root = package_root.resolve()
    assert Path(lookup.__file__).resolve().is_relative_to(package_root), "lookup module outside installed package"
    assert lookup._DISTRICT_CSV.resolve() == package_root / "location/data/china_district_centers.csv", "lookup data outside installed package"
    probe = DATA_CONTRACT["center_probe"]
    result = lookup.lookup_nearest_district(lon=probe["longitude"], lat=probe["latitude"], max_km=probe["max_km"])
    assert result == probe["expected"], f"installed center lookup result mismatch: {result}"
    count = lookup.get_cache_info()["record_count"]
    assert count == probe["record_count"], f"installed center record count mismatch: {count}"
    return {"result": result, "record_count": count}


def verify(*, browser: bool, geo: bool) -> dict:
    import netwatch
    import requests
    from rich.console import Console
    from netwatch import cli
    from netwatch.cli_modules import location, speedtest
    from netwatch.speedtest.speedtest_cn import SpeedtestCnResult

    package = Path(netwatch.__file__).resolve()
    assert package.is_relative_to(Path(sys.prefix).resolve()), f"not installed from wheel: {package}"
    assert not ADVANCED_MODULES.intersection(sys.modules), "eager advanced module import"
    assert (importlib.util.find_spec("playwright") is not None) == browser
    assert (importlib.util.find_spec("shapely") is not None) == geo
    assert importlib.util.find_spec("reverse_geocoder") is not None
    data_sha256 = inspect_installed_data(package.parent)
    assert not (package.parent / "location/admin/boundary_tools.py").exists()
    events = []

    def denied(*args, **kwargs):
        events.append("unexpected external I/O")
        raise AssertionError(events[-1])

    with tempfile.TemporaryDirectory(prefix="netwatch-installed-") as home, ExitStack() as stack:
        stack.enter_context(patch.dict(os.environ, {"HOME": home, "USERPROFILE": home, "NETWATCH_CONFIG_PATH": str(Path(home)/"config.json")}))
        for target, name in [(requests.sessions.Session, "request"), (socket, "getaddrinfo"),
                             (socket.socket, "connect"), (subprocess, "run"), (webbrowser, "open")]:
            stack.enter_context(patch.object(target, name, denied))
        stack.enter_context(patch.object(cli, "console", Console(file=StringIO())))
        stack.enter_context(patch.object(cli.Prompt, "ask", return_value="8"))
        cli.main()
        assert not ADVANCED_MODULES.intersection(sys.modules)
        from netwatch.network.proxy_probe import ExitIPInfo
        with patch.object(location, "console", Console(file=StringIO())), \
             patch.object(location, "get_preferred_physical_interface", return_value=None), \
             patch.object(location, "get_display_network_interfaces", return_value=[]), \
             patch.object(location, "get_default_gateway", return_value=None), \
             patch.object(location, "probe_exit_ip", return_value=ExitIPInfo(ip=None, city=None, region=None, country=None, org=None, error="synthetic unavailable")), \
             patch.object(location.Prompt, "ask", side_effect=["n", "n"]):
            location.show_network_info()
        assert not ADVANCED_MODULES.intersection(sys.modules)
        with patch.object(location, "console", Console(file=StringIO())), \
             patch.object(location.Prompt, "ask", return_value="n"):
            location.show_precise_offline_location()
        assert not ADVANCED_MODULES.intersection(sys.modules)
        result = SpeedtestCnResult(download_mbps=100, upload_mbps=20, ping_ms=8)
        backend = Mock(return_value=result)
        stack.enter_context(patch.object(speedtest, "console", Console(file=StringIO())))
        stack.enter_context(patch.object(speedtest.Prompt, "ask", return_value="y"))
        stack.enter_context(patch.object(speedtest, "run_speedtest_cn_browser_automation", backend))
        stack.enter_context(patch.object(speedtest, "run_best_speedtest", denied))
        speedtest.show_speedtest_cn_main()
        backend.assert_called_once()
        options = backend.call_args.args[0]
        assert options.headless and not options.debug_screenshot
        assert not ADVANCED_MODULES.intersection(sys.modules)
        from netwatch.location import precise_location
        from netwatch.location.geolocation.device import DeviceLocationResult
        stack.enter_context(patch.object(precise_location, "run_browser_geolocation", return_value=DeviceLocationResult(error="synthetic permission denied")))
        report = location.run_precise_location_report(timeout_seconds=1)
        assert "synthetic permission denied" in report.warnings
        assert ADVANCED_MODULES <= set(sys.modules)
        center_lookup = verify_center_lookup(package.parent)
        assert not events
    return {"platform": platform.system(), "python": platform.python_version(), "prefix": sys.prefix,
            "installed_package": str(package), "version": importlib.metadata.version("netwatch-cli"),
            "browser_extra": browser, "geo_extra": geo, "advanced_import_lazy": True, "advanced_module_counts": [0, 7],
            "basic_info_mock": "PASS", "advanced_cancel": "PASS",
            "main_exit": "PASS", "main4_mock": "PASS", "advanced_domain_mock": "PASS",
            "data_sha256": data_sha256, "center_lookup": center_lookup,
            "unexpected_external_io": events}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--browser", choices=["yes", "no"], required=True)
    parser.add_argument("--geo", choices=["yes", "no"], required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = json.dumps(verify(browser=args.browser == "yes", geo=args.geo == "yes"), indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(result + "\n", encoding="utf-8")
    print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
