"""Deliberate negative fixtures keep the CLI dependency direction enforceable."""

from pathlib import Path

import pytest

from scripts.dev import check_cli_boundaries as checker


def source(root, relative, text):
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


@pytest.mark.parametrize("path,text", [
    ("netwatch/cli_modules/example.py", "from netwatch.cli import console"),
    ("netwatch/cli_modules/example.py", "import netwatch.cli as entry"),
    ("netwatch/cli_modules/example.py", "from netwatch import cli as entry"),
    ("netwatch/cli_modules/example.py", "from ..cli import console"),
    ("netwatch/cli_modules/example.py", "from .. import cli"),
    ("netwatch/cli_modules/example.py", 'import sys as s\nx = s.modules.get("netwatch.cli")'),
    ("netwatch/cli_modules/example.py", 'from sys import modules as registry\nx = registry["netwatch.cli"]'),
    ("netwatch/cli_modules/example.py", 'import importlib as il\nx = il.import_module("netwatch.cli")'),
    ("netwatch/cli_modules/example.py", 'from importlib import import_module as load\nx = load("netwatch.cli")'),
    ("netwatch/cli_modules/example.py", 'x = __import__("netwatch.cli")'),
    ("netwatch/cli_modules/example.py", 'import netwatch as nw\nx = getattr(nw, "cli")'),
    ("netwatch/cli_modules/example.py", 'import netwatch as nw\nx = nw.cli.console'),
    ("netwatch/cli_modules/example.py", "import requests"),
    ("netwatch/cli_modules/example.py", "import http.server"),
    ("netwatch/cli_modules/example.py", 'from importlib import import_module as load\nx = load(".cli", "netwatch")'),
    ("netwatch/cli_modules/common.py", "class ConsoleProxy: pass"),
    ("netwatch/cli_modules/example.py", "x = cli_override('dependency', fallback)"),
    ("netwatch/speedtest/example.py", "from netwatch.cli_modules.speedtest import show_auto_speedtest"),
    ("netwatch/speedtest/example.py", "from ..cli_modules import speedtest"),
    ("netwatch/location/example.py", "from .. import cli"),
    ("netwatch/network/example.py", "import netwatch.cli"),
    ("netwatch/network/example.py", "def broken(:"),
])
def test_invalid_fixture_returns_nonzero(tmp_path, path, text, capsys):
    source(tmp_path, path, text)
    assert checker.main(tmp_path) == 1
    assert "violation" in capsys.readouterr().out


def test_valid_dependencies_and_literal_documentation_pass(tmp_path):
    source(tmp_path, "netwatch/cli.py", "from netwatch.cli_modules.location import show_network_info")
    source(tmp_path, "netwatch/__main__.py", "from netwatch.cli import main")
    source(tmp_path, "netwatch/cli_modules/example.py", 'from netwatch.network.info import fetch\nNOTE = "netwatch.cli"')
    source(tmp_path, "netwatch/network/example.py", "import requests")
    assert checker.main(tmp_path) == 0


def test_large_file_is_observation_not_a_reason_to_split(tmp_path, capsys):
    source(tmp_path, "netwatch/cli_modules/example.py", "# observation\n" * 901)
    assert checker.main(tmp_path) == 0
    assert "large CLI module" in capsys.readouterr().out


def test_current_runtime_has_no_boundary_exceptions():
    root = Path(__file__).resolve().parents[2]
    assert checker.main(root) == 0


def test_missing_runtime_directory_is_not_a_success(tmp_path):
    assert checker.main(tmp_path) == 1
