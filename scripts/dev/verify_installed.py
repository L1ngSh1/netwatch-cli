#!/usr/bin/env python3
"""Run with a clean wheel environment's python -I; all user actions are mocked."""

from __future__ import annotations

import argparse
from contextlib import ExitStack
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


def verify(*, browser: bool, geo: bool) -> dict:
    import netwatch
    import requests
    from rich.console import Console
    from netwatch import cli
    from netwatch.cli_modules import location, speedtest
    from netwatch.speedtest.speedtest_cn import SpeedtestCnResult

    package = Path(netwatch.__file__).resolve()
    assert package.is_relative_to(Path(sys.prefix).resolve()), f"not installed from wheel: {package}"
    assert "netwatch.location.precise_location" not in sys.modules, "eager advanced orchestrator import"
    assert (importlib.util.find_spec("playwright") is not None) == browser
    assert (importlib.util.find_spec("shapely") is not None) == geo
    assert importlib.util.find_spec("reverse_geocoder") is not None
    data = package.parent / "location/data"
    assert (data / "china_district_centers.csv").is_file()
    assert (data / "boundaries/china_districts.sample.geojson").is_file()
    assert (data / "roads/roads.sample.geojson").is_file()
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
        assert "netwatch.location.precise_location" not in sys.modules
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
        assert "netwatch.location.precise_location" not in sys.modules
        from netwatch.location import precise_location
        from netwatch.location.geolocation.device import DeviceLocationResult
        stack.enter_context(patch.object(precise_location, "run_browser_geolocation", return_value=DeviceLocationResult(error="synthetic permission denied")))
        report = location.run_precise_location_report(timeout_seconds=1)
        assert "synthetic permission denied" in report.warnings
        assert not events
    return {"platform": platform.system(), "python": platform.python_version(), "prefix": sys.prefix,
            "installed_package": str(package), "version": importlib.metadata.version("netwatch-cli"),
            "browser_extra": browser, "geo_extra": geo, "advanced_import_lazy": True,
            "main_exit": "PASS", "main4_mock": "PASS", "advanced_domain_mock": "PASS",
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
